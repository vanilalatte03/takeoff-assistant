"""Windows click launcher. GUI owns a disposable, Job-protected supervisor."""
import json
import os
from pathlib import Path
import queue
import subprocess
import threading
import ctypes
from desktop_win32 import NativeWindow
import webbrowser

from desktop_runtime import CREATE_NO_WINDOW, ROOT, URL, LaunchError, SingleInstance


class Launcher:
    def __init__(self):
        self.process = None
        self.events = queue.Queue()
        self.result = None
        self.closing = False
        self.env_file = None
        self.opened = False
        self.reader_done = False
        self.ui = NativeWindow(self)
        self.set_storage({'database': str(ROOT / 'data/takeoff_assistant.db'),
                          'uploads': str(ROOT / 'data/uploads'),
                          'rendered': str(ROOT / 'data/rendered'), 'exports': str(ROOT / 'exports')})

    def set_storage(self, paths):
        lines = ['실제 저장 위치 (외부 설정·환경변수가 우선)']
        for key, label in [('database', 'DB'), ('uploads', '원본 PDF'), ('rendered', '페이지 이미지'), ('exports', 'Excel')]:
            lines.append(f'{label}: {paths[key]}')
        self.ui.text('storage', '\r\n'.join(lines))

    def open_docs(self):
        guide = ROOT / 'docs/WINDOWS_LAUNCH.md'
        try:
            os.startfile(guide)
        except OSError:
            try:
                # .md file associations are optional on a prepared Windows PC.
                # An argument vector keeps spaces literal and invokes no shell.
                subprocess.Popen([str(Path(os.environ.get('SystemRoot', 'C:/Windows')) / 'System32/notepad.exe'),
                                  str(guide)], creationflags=CREATE_NO_WINDOW)
            except OSError:
                self.ui.message('백업·복구 안내',
                                '도움말을 열 수 없습니다. 탐색기에서 다음 파일을 텍스트 편집기로 여세요:\n'
                                f'{guide}\n\n'
                                '브라우저의 저장 완료와 실행기의 안전 종료 완료를 확인한 후, DB와 남은 journal/WAL 파일·'
                                '원본 PDF·페이지 이미지·Excel 폴더 전체를 새 빈 백업 폴더에 복사하세요. '
                                '실행 중 DB를 단순 복사하지 마세요. 복구는 새 폴더의 복사본으로 확인하며 기존 자료를 덮어쓰지 마세요.')

    def choose_env(self):
        filename = self.ui.choose_file()
        if filename:
            self.env_file = filename
            self.ui.text('env_status', '선택한 외부 설정을 시작 시 읽습니다 (내용·키는 표시하거나 복사하지 않습니다).')

    def clear_env(self):
        self.env_file = None
        self.ui.text('env_status', '설정 파일 없음 · 기존 환경변수는 유지하며, 키가 없으면 로컬 기능을 사용합니다.')

    def start(self):
        if self.process is not None:
            return
        self.ui.text('status', '시작 중 · 의존성과 포트를 확인합니다. 취소하려면 안전 종료를 누르세요.')
        self.ui.enable('start', False)
        self.ui.enable('env', False)
        self.ui.enable('clear_env', False)
        self.ui.enable('stop', True)
        self.result = None
        self.opened = False
        self.reader_done = False
        env = os.environ.copy()
        env['PYTHONUTF8'] = '1'
        command = [str(ROOT / 'apps/api/.venv311/Scripts/python.exe'), '-u', str(ROOT / 'scripts/desktop_runtime.py')]
        if self.env_file:
            command.append(self.env_file)
        try:
            self.process = subprocess.Popen(command, cwd=ROOT, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                            stderr=subprocess.DEVNULL, env=env, creationflags=CREATE_NO_WINDOW)
        except OSError:
            self.ui.text('status', '실행할 수 없습니다. README의 Python 가상환경 준비와 폴더 읽기 권한을 확인하세요.')
            self.reset_buttons()
            return
        process = self.process

        def read_events():
            try:
                for line in process.stdout:
                    try:
                        self.events.put((process, json.loads(line)))
                    except (ValueError, UnicodeError):
                        continue
            finally:
                self.events.put((process, {'kind': 'eof', 'value': None}))
        threading.Thread(target=read_events, daemon=True).start()

    def reset_buttons(self):
        self.ui.enable('start', True)
        self.ui.enable('env', True)
        self.ui.enable('clear_env', True)
        self.ui.enable('stop', False)
        self.ui.enable('browser', False)

    def open_browser(self):
        if not webbrowser.open(URL):
            self.ui.message('브라우저 열기', f'브라우저를 열 수 없습니다. 주소창에 {URL} 을 입력하세요.')

    def stop(self):
        if self.process is None:
            return
        self.ui.text('status', '안전 종료 중 · 진행 중인 API 저장 요청이 끝나기를 기다립니다 (최대 25초).')
        self.ui.enable('stop', False)
        self.ui.enable('browser', False)
        try:
            self.process.stdin.close()  # EOF is also used after abrupt GUI termination.
        except OSError:
            pass

    def close(self):
        self.closing = True
        if self.process is None:
            self.ui.destroy()
        else:
            self.stop()

    def poll(self):
        while True:
            try:
                process, event = self.events.get_nowait()
            except queue.Empty:
                break
            if process is not self.process:
                continue
            kind, value = event['kind'], event['value']
            if kind == 'storage':
                self.set_storage(value)
            elif kind == 'ready' and not self.closing and not process.stdin.closed:
                self.ui.text('status', '실행 중 · 브라우저에서 저장 완료를 확인한 뒤 안전 종료하세요.')
                self.ui.enable('browser', True)
                if not self.opened:
                    self.opened = True
                    self.open_browser()
            elif kind == 'stopped':
                self.result = value
            elif kind == 'eof':
                self.reader_done = True
        if self.process is not None and self.process.poll() is not None:
            process = self.process
            # Drain the reader before interpreting its final result.
            if not self.reader_done:
                return
            result = self.result or {'forced': True, 'error': '실행 제어가 종료되었습니다. 소유한 서버는 Windows 안전 장치로 정리됩니다. 의존성·저장 경로를 확인한 뒤 다시 시작하세요.'}
            if result.get('error'):
                self.ui.text('status', result['error'])
            elif result['forced']:
                self.ui.text('status', '종료 대기 시간이 지나 소유 서버만 강제 종료했습니다. 다시 시작한 뒤 마지막 저장 내용을 확인하세요.')
            else:
                self.ui.text('status', '안전 종료 완료 · 서버가 모두 종료되었습니다. 이제 저장 폴더를 백업할 수 있습니다.')
            process.stdout.close()
            if not process.stdin.closed:
                process.stdin.close()
            self.process = None
            self.reset_buttons()
            if self.closing:
                if result['forced'] or result.get('error'):
                    self.closing = False
                    self.ui.message('종료 확인', '종료 중 문제가 있었습니다. 실행기의 안내와 마지막 저장 내용을 확인하세요.')
                else:
                    self.ui.destroy()
                return


def main():
    try:
        instance = SingleInstance()
    except LaunchError as exc:
        ctypes.windll.user32.MessageBoxW(None, str(exc), '실행 오류', 0x10)
        return
    try:
        if instance.duplicate:
            ctypes.windll.user32.MessageBoxW(None, '이 폴더의 실행기가 이미 열려 있습니다. 기존 실행기 창에서 시작·안전 종료를 사용하세요. 기존 서버는 종료하지 않았습니다.', '이미 실행 중', 0x40)
            return
        launcher = Launcher()
        launcher.ui.run()
    finally:
        instance.close()


if __name__ == '__main__':
    main()
