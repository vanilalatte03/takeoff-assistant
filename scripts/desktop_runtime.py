"""Owned local server session. No persisted PIDs, shell commands or port-based kills."""
import ctypes
from argparse import ArgumentParser
from ctypes import wintypes
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import threading
import time
from urllib.request import build_opener, ProxyHandler

ROOT = Path(__file__).resolve().parents[1]
HOST = '127.0.0.1'
API_PORT = 8000
WEB_PORT = 5173
URL = f'http://{HOST}:{WEB_PORT}/workflow'
CREATE_NO_WINDOW = 0x08000000 if os.name == 'nt' else 0


class LaunchError(Exception):
    pass


def kernel32():
    dll = ctypes.WinDLL('kernel32', use_last_error=True)
    dll.CreateJobObjectW.restype = wintypes.HANDLE
    dll.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
    dll.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
    dll.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
    dll.GetCurrentProcess.restype = wintypes.HANDLE
    dll.CreateMutexW.restype = wintypes.HANDLE
    dll.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
    dll.CloseHandle.argtypes = [wintypes.HANDLE]
    return dll


class SingleInstance:
    """Kernel handle lifetime, never a stale PID/lock file."""
    def __init__(self, root=ROOT):
        dll = kernel32()
        name = hashlib.sha256(str(root.resolve()).casefold().encode()).hexdigest()
        self.handle = dll.CreateMutexW(None, False, 'Local\\TakeoffDesktop-' + name)
        if not self.handle:
            raise LaunchError('실행 잠금을 만들 수 없습니다. Windows 로그인 세션을 확인하세요.')
        self.duplicate = ctypes.get_last_error() == 183

    def close(self):
        if self.handle:
            kernel32().CloseHandle(self.handle)
            self.handle = None


def protect_supervisor():
    """Put this supervisor in a kill-on-close Job BEFORE creating any child.

    The handle is not inheritable. OS closes it on crash/exit, reclaiming the
    entire descendant tree (including esbuild). The GUI remains outside the Job.
    """
    class Basic(ctypes.Structure):
        _fields_ = [('process_time', ctypes.c_int64), ('job_time', ctypes.c_int64),
                    ('flags', wintypes.DWORD), ('min_ws', ctypes.c_size_t),
                    ('max_ws', ctypes.c_size_t), ('active', wintypes.DWORD),
                    ('affinity', ctypes.c_size_t), ('priority', wintypes.DWORD),
                    ('scheduling', wintypes.DWORD)]

    class IO(ctypes.Structure):
        _fields_ = [(name, ctypes.c_uint64) for name in
                    ('read_ops', 'write_ops', 'other_ops', 'read_bytes', 'write_bytes', 'other_bytes')]

    class Extended(ctypes.Structure):
        _fields_ = [('basic', Basic), ('io', IO), ('process_memory', ctypes.c_size_t),
                    ('job_memory', ctypes.c_size_t), ('peak_process', ctypes.c_size_t),
                    ('peak_job', ctypes.c_size_t)]

    dll = kernel32()
    job = dll.CreateJobObjectW(None, None)
    limits = Extended()
    limits.basic.flags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
    if not job or not dll.SetInformationJobObject(job, 9, ctypes.byref(limits), ctypes.sizeof(limits)):
        raise LaunchError('안전 종료 장치를 만들 수 없습니다. 다른 개발 서버를 종료한 뒤 다시 실행하세요.')
    if not dll.AssignProcessToJobObject(job, dll.GetCurrentProcess()):
        dll.CloseHandle(job)
        raise LaunchError('안전 종료 장치를 연결할 수 없어 서버를 시작하지 않았습니다. Windows에서 직접 다시 실행하세요.')
    return job  # Keep open for this process lifetime; never persist/reopen PIDs.


def assert_ports_free():
    for port in (API_PORT, WEB_PORT):
        with socket.socket() as sock:
            if os.name == 'nt':
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            try:
                sock.bind((HOST, port))
            except OSError:
                raise LaunchError(f'{port} 포트를 다른 프로그램이 사용 중입니다. 해당 프로그램의 창에서 정상 종료한 뒤 다시 시작하세요. 실행기는 그 프로그램을 종료하지 않습니다.') from None


def prepare(env_file=None, root=ROOT, vision_use_search_model=False):
    python = root / 'apps/api/.venv311/Scripts/python.exe'
    vite = root / 'apps/web/node_modules/vite/bin/vite.js'
    node = shutil.which('node')
    if not python.is_file():
        raise LaunchError('Python 가상환경이 없습니다. README의 최초 준비 1~3번(Python 3.11 설치·가상환경·API 의존성)을 완료하세요.')
    if not node or not vite.is_file():
        raise LaunchError('Node.js 또는 웹 의존성이 없습니다. Node.js 24 설치 후 README의 npm ci 준비를 완료하세요.')
    try:
        import importlib.util
        if any(importlib.util.find_spec(name) is None for name in ('uvicorn', 'fastapi', 'sqlalchemy', 'fitz', 'openpyxl', 'dotenv')):
            raise ImportError
    except (ImportError, ValueError):
        raise LaunchError('API 의존성이 없습니다. README의 해시 lock 설치와 API 설치를 완료하세요.') from None
    # Windows environment names are case-insensitive. A plain dict is not;
    # normalize before merging so lowercase dotenv keys cannot bypass precedence.
    env = {key.upper(): value for key, value in os.environ.items()}
    if env_file:
        if not Path(env_file).is_file():
            raise LaunchError('선택한 외부 설정 파일이 없습니다. 파일을 다시 선택하거나 설정 없이 시작하세요.')
        from dotenv import dotenv_values
        try:
            values = dotenv_values(env_file, interpolate=False, encoding='utf-8')
        except (OSError, UnicodeError):
            raise LaunchError('외부 설정 파일을 읽을 수 없습니다. UTF-8 파일과 읽기 권한을 확인하세요.') from None
        for key, value in values.items():
            if value is not None:
                env.setdefault(key.upper(), value)  # Same precedence as run_api.py.
    if vision_use_search_model and not env.get('TAKEOFF_AI_VISION_MODEL'):
        # Explicit opt-in for this child process only; never rewrite the file or
        # global environment, and never replace a separately configured model.
        env['TAKEOFF_AI_VISION_MODEL'] = env.get('TAKEOFF_AI_MODEL', '')
    env['PYTHONUTF8'] = '1'
    # Do not pass NODE_OPTIONS or npm shell wrappers to the owned web process.
    web_env = env.copy()
    web_env.pop('NODE_OPTIONS', None)
    web_env['NO_COLOR'] = '1'
    web_env['FORCE_COLOR'] = '0'
    for key in list(web_env):
        if key.startswith('TAKEOFF_'):
            web_env.pop(key)
    return ([str(python), '-u', str(root / 'scripts/desktop_api.py')],
            [node, str(vite), '--host', HOST, '--port', str(WEB_PORT), '--strictPort'], env, web_env)


def storage_summary(env, root=ROOT):
    return {
        'database': (env.get('TAKEOFF_DATABASE_URL', f'sqlite:///{(root / "data/takeoff_assistant.db").as_posix()}')
                     if env.get('TAKEOFF_DATABASE_URL', 'sqlite:///').startswith('sqlite:///')
                     else '외부 설정 DB (연결 문자열은 표시하지 않음)'),
        'uploads': env.get('TAKEOFF_UPLOADS_DIR', str(root / 'data/uploads')),
        'rendered': env.get('TAKEOFF_RENDERED_PAGES_DIR', str(root / 'data/rendered')),
        'exports': env.get('TAKEOFF_EXPORTS_DIR', str(root / 'exports')),
    }


class Session:
    def __init__(self, cancel, emit, root=ROOT):
        self.cancel, self.emit, self.root = cancel, emit, root
        self.api = self.web = None
        self.forced = False

    def spawn(self, command, env, cwd):
        process = subprocess.Popen(command, cwd=cwd, env=env, stdin=subprocess.PIPE,
                                   stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                   creationflags=CREATE_NO_WINDOW)
        process.desktop_ready = threading.Event()
        marker = b'TAKEOFF_DESKTOP_READY' if command[-1].endswith('desktop_api.py') else b'http://127.0.0.1:5173/'

        def drain():
            # Discard raw logs, retain only our own child startup signal. A foreign
            # listener racing the bind probe cannot make its HTTP 200 count as ready.
            for line in process.stdout:
                if marker in line:
                    process.desktop_ready.set()
        threading.Thread(target=drain, daemon=True).start()
        return process

    def wait_ready(self, process, url, label, timeout=35):
        opener = build_opener(ProxyHandler({}))  # localhost must never use an external proxy.
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self.cancel.is_set():
                raise LaunchError('시작을 취소했습니다. 시작한 서버를 정리합니다.')
            if process.poll() is not None:
                raise LaunchError(f'{label} 시작에 실패했습니다. README의 의존성 설치를 확인하고 포트 충돌을 해소한 뒤 다시 시작하세요. 개발자 진단은 docs/WINDOWS_LAUNCH.md를 참고하세요.')
            try:
                if process.desktop_ready.is_set():
                    with opener.open(url, timeout=0.5) as response:
                        if response.status == 200 and process.poll() is None:
                            return
            except OSError:
                pass
            self.cancel.wait(0.15)
        raise LaunchError(f'{label} 응답 시간이 초과되었습니다. 시작한 서버를 정리합니다. 저장 폴더의 쓰기 권한·디스크 여유를 확인하고 다시 시작하세요.')

    def start(self, env_file=None, vision_use_search_model=False):
        api, web, env, web_env = prepare(env_file, self.root, vision_use_search_model)
        assert_ports_free()
        # Settings paths only. Never emit env contents, model/key or raw child logs.
        self.emit('storage', storage_summary(env, self.root))
        self.api = self.spawn(api, env, self.root)
        self.wait_ready(self.api, f'http://{HOST}:{API_PORT}/health', 'API')
        self.web = self.spawn(web, web_env, self.root / 'apps/web')
        self.wait_ready(self.web, URL, '웹')
        if self.api.poll() is not None:
            raise LaunchError('API가 종료되었습니다. 저장 폴더와 의존성을 확인한 뒤 다시 시작하세요.')
        self.emit('ready', {'api_pid': self.api.pid, 'web_pid': self.web.pid})

    def stop(self):
        # These Popen objects retain original process handles. No PID lookup/kill.
        if self.web and self.web.poll() is None:
            self.web.terminate()
        if self.api and self.api.poll() is None:
            try:
                self.api.stdin.write(b'stop\n')
                self.api.stdin.flush()
            except (OSError, ValueError):
                pass
            try:
                self.api.wait(timeout=25)
            except subprocess.TimeoutExpired:
                self.forced = True
                self.api.kill()
                self.api.wait(timeout=5)
        if self.web:
            self.web.wait(timeout=5)
        for process in (self.api, self.web):
            if process and process.stdin:
                process.stdin.close()
        return self.forced


def supervise(env_file=None, vision_use_search_model=False):
    # This process and all children die together if GUI/supervisor fails.
    job = protect_supervisor()
    cancel = threading.Event()
    threading.Thread(target=lambda: (sys.stdin.readline(), cancel.set()), daemon=True).start()

    def emit(kind, value):
        try:
            print(json.dumps({'kind': kind, 'value': value}, ensure_ascii=True), flush=True)
        except OSError:
            cancel.set()

    session = Session(cancel, emit)
    error = None
    try:
        session.start(env_file, vision_use_search_model)
        while not cancel.wait(0.2):
            if any(p.poll() is not None for p in (session.api, session.web)):
                raise LaunchError('서버가 예기치 않게 종료되었습니다. 나머지 서버를 정리합니다. 마지막 저장 내용과 저장 폴더·의존성을 확인한 뒤 다시 시작하세요.')
    except LaunchError as exc:
        error = str(exc)
    except Exception:
        error = '서버 실행 중 오류가 발생했습니다. 저장 폴더의 권한·디스크 여유와 의존성을 확인한 뒤 다시 시작하세요.'
    finally:
        try:
            forced = session.stop()
            emit('stopped', {'forced': forced, 'error': error})
        except Exception:
            emit('stopped', {'forced': True, 'error': '정상 종료를 완료하지 못해 소유한 서버만 강제 정리했습니다. 다시 시작한 뒤 마지막 저장 내용을 확인하세요.'})
        # Job handle deliberately stays open until process exit. Its closure kills
        # remaining descendants before the GUI observes supervisor termination.
        assert job


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('env_file', nargs='?')
    parser.add_argument('--vision-use-search-model', action='store_true')
    args = parser.parse_args()
    supervise(args.env_file, args.vision_use_search_model)


if __name__ == '__main__':
    main()
