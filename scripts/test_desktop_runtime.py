import importlib.util
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import threading
import time
import queue
import sqlite3
from urllib.request import Request, build_opener, ProxyHandler
from unittest.mock import Mock

import pytest

sys.path.insert(0, str(Path(__file__).parent))
import desktop_runtime as runtime


def test_port_conflict_does_not_close_unrelated_listener(monkeypatch):
    with socket.socket() as listener:
        listener.bind(('127.0.0.1', 0))
        listener.listen()
        monkeypatch.setattr(runtime, 'API_PORT', listener.getsockname()[1])
        with pytest.raises(runtime.LaunchError, match='다른 프로그램'):
            runtime.assert_ports_free()
        with socket.create_connection(listener.getsockname(), timeout=1):
            pass
        assert listener.fileno() >= 0


def test_missing_python_and_web_dependencies_have_recovery(tmp_path, monkeypatch):
    with pytest.raises(runtime.LaunchError, match='가상환경.*README'):
        runtime.prepare(root=tmp_path)
    python = tmp_path / 'apps/api/.venv311/Scripts/python.exe'
    python.parent.mkdir(parents=True)
    python.touch()
    monkeypatch.setattr(runtime.shutil, 'which', lambda _: None)
    with pytest.raises(runtime.LaunchError, match='Node.js.*npm ci'):
        runtime.prepare(root=tmp_path)


def prepared_root(tmp_path, monkeypatch):
    root = tmp_path / '공백 있는 설치 폴더'
    for item in ('apps/api/.venv311/Scripts/python.exe', 'apps/web/node_modules/vite/bin/vite.js'):
        path = root / item
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch()
    monkeypatch.setattr(runtime.shutil, 'which', lambda _: 'C:/Node Space/node.exe')
    return root


def test_arguments_preserve_spaces_loopback_and_strict_port(tmp_path, monkeypatch):
    root = prepared_root(tmp_path, monkeypatch)
    api, web, env, web_env = runtime.prepare(root=root)
    assert api == [str(root / 'apps/api/.venv311/Scripts/python.exe'), '-u', str(root / 'scripts/desktop_api.py')]
    assert web == ['C:/Node Space/node.exe', str(root / 'apps/web/node_modules/vite/bin/vite.js'),
                   '--host', '127.0.0.1', '--port', '5173', '--strictPort']
    source = (Path(__file__).parent / 'desktop_api.py').read_text(encoding='utf-8')
    assert "host='127.0.0.1'" in source


def test_external_env_not_copied_or_printed_and_precedence(tmp_path, monkeypatch, capsys):
    root = prepared_root(tmp_path, monkeypatch)
    external = tmp_path / '설정 공백.env'
    content = 'TAKEOFF_AI_API_KEY=private-test-key\nTAKEOFF_AI_MODEL=file-model\nTAKEOFF_UPLOADS_DIR=C:/Recovery Space/uploads\n'
    external.write_text(content, encoding='utf-8')
    monkeypatch.setenv('TAKEOFF_AI_MODEL', 'process-model')
    monkeypatch.setenv('NODE_OPTIONS', '--inspect=0.0.0.0:9229')
    _, _, env, web_env = runtime.prepare(external, root)
    assert env['TAKEOFF_AI_API_KEY'] == 'private-test-key'
    assert env['TAKEOFF_AI_MODEL'] == 'process-model'
    assert env['TAKEOFF_UPLOADS_DIR'] == 'C:/Recovery Space/uploads'
    assert 'NODE_OPTIONS' not in web_env
    assert not any(key.startswith('TAKEOFF_') for key in web_env)
    assert external.read_text(encoding='utf-8') == content
    assert not list(root.glob('*.env'))
    assert 'private-test-key' not in capsys.readouterr().out
    assert 'private-test-key' not in json.dumps(runtime.storage_summary(env, root))


def test_non_sqlite_connection_string_is_not_displayed():
    assert 'password' not in str(runtime.storage_summary({'TAKEOFF_DATABASE_URL': 'postgres://user:password@host/db'}))


def test_windows_mixed_case_env_preserves_process_precedence_and_redaction(tmp_path, monkeypatch):
    root = prepared_root(tmp_path, monkeypatch)
    external = tmp_path / 'mixed.env'
    external.write_text('takeoff_ai_model=file-model\ntakeoff_ai_api_key=private-test\nTakeOff_Uploads_Dir=C:/Recovery/uploads\n', encoding='utf-8')
    monkeypatch.setenv('TAKEOFF_AI_MODEL', 'process-model')
    _, _, env, web_env = runtime.prepare(external, root)
    assert env['TAKEOFF_AI_MODEL'] == 'process-model'
    assert env['TAKEOFF_AI_API_KEY'] == 'private-test'
    assert runtime.storage_summary(env, root)['uploads'] == 'C:/Recovery/uploads'
    assert not any(key.upper().startswith('TAKEOFF_') for key in web_env)
    assert not any(key.lower() == 'takeoff_ai_model' and key != 'TAKEOFF_AI_MODEL' for key in env)


def test_partial_web_start_failure_cleans_only_created_handles(monkeypatch):
    session = runtime.Session(threading.Event(), Mock())
    api = Mock()
    api.poll.return_value = None
    monkeypatch.setattr(runtime, 'prepare', lambda *a: (['api'], ['web'], {}, {}))
    monkeypatch.setattr(runtime, 'assert_ports_free', lambda: None)
    monkeypatch.setattr(session, 'spawn', Mock(side_effect=[api, OSError('web failed')]))
    monkeypatch.setattr(session, 'wait_ready', lambda *a: None)
    try:
        with pytest.raises(OSError):
            session.start()
    finally:
        assert session.stop() is False
    api.stdin.write.assert_called_once_with(b'stop\n')
    api.wait.assert_called_once_with(timeout=25)
    api.kill.assert_not_called()


def test_api_shutdown_timeout_uses_original_handle_only():
    session = runtime.Session(threading.Event(), Mock())
    api = session.api = Mock()
    api.poll.return_value = None
    api.wait.side_effect = [subprocess.TimeoutExpired('api', 25), 0]
    assert session.stop() is True
    api.kill.assert_called_once()
    api.stdin.write.assert_called_once_with(b'stop\n')


def test_exited_process_is_never_terminated_even_if_pid_reused():
    session = runtime.Session(threading.Event(), Mock())
    for name in ('api', 'web'):
        process = Mock(pid=99999)
        process.poll.return_value = 0
        setattr(session, name, process)
    session.stop()
    for process in (session.api, session.web):
        process.terminate.assert_not_called()
        process.kill.assert_not_called()
        process.stdin.write.assert_not_called()


def test_readiness_cancel_and_dead_child_do_not_treat_http_as_success():
    cancel = threading.Event()
    cancel.set()
    session = runtime.Session(cancel, Mock())
    process = Mock()
    with pytest.raises(runtime.LaunchError, match='취소'):
        session.wait_ready(process, 'http://127.0.0.1:1', 'API')
    cancel.clear()
    process.poll.return_value = 2
    with pytest.raises(runtime.LaunchError, match='시작에 실패'):
        session.wait_ready(process, 'http://127.0.0.1:1', 'API')


@pytest.mark.skipif(os.name != 'nt', reason='Windows Job/mutex contract')
def test_mutex_duplicate_lifetime_has_no_stale_lock(tmp_path):
    first = runtime.SingleInstance(tmp_path)
    second = runtime.SingleInstance(tmp_path)
    try:
        assert not first.duplicate
        assert second.duplicate
    finally:
        first.close()
        second.close()
    third = runtime.SingleInstance(tmp_path)
    assert not third.duplicate
    third.close()


@pytest.mark.skipif(os.name != 'nt', reason='Windows Job descendant reclamation')
@pytest.mark.parametrize('owner_exit', ['eof', 'kill'])
def test_job_reclaims_child_and_grandchild_after_owner_exit(tmp_path, owner_exit):
    # Actual Windows handles, isolated ephemeral ports, synthetic processes only.
    child_script = tmp_path / 'worker with spaces.py'
    child_script.write_text('import subprocess,sys,time\n'
                            'p=subprocess.Popen([sys.executable,"-c","import time; time.sleep(60)"])\n'
                            'print(p.pid,flush=True)\ntime.sleep(60)\n', encoding='utf-8')
    code = ('import sys,subprocess; sys.path.insert(0,sys.argv[1]); '
            'import desktop_runtime as r; job=r.protect_supervisor(); '
            'p=subprocess.Popen([sys.executable,sys.argv[2]],stdout=subprocess.PIPE); '
            'print(str(p.pid)+","+p.stdout.readline().decode().strip(),flush=True); '
            'sys.stdin.readline()')
    supervisor = subprocess.Popen([sys.executable, '-u', '-c', code, str(Path(__file__).parent), str(child_script)],
                                  stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                  creationflags=runtime.CREATE_NO_WINDOW)
    dll = runtime.kernel32()
    dll.OpenProcess.restype = runtime.wintypes.HANDLE
    dll.OpenProcess.argtypes = [runtime.wintypes.DWORD, runtime.wintypes.BOOL, runtime.wintypes.DWORD]
    dll.WaitForSingleObject.argtypes = [runtime.wintypes.HANDLE, runtime.wintypes.DWORD]
    handles = []
    try:
        line = supervisor.stdout.readline().decode().strip()
        assert line, supervisor.stderr.read().decode()
        pids = [int(value) for value in line.split(',')]
        handles = [dll.OpenProcess(0x100000, False, pid) for pid in pids]
        assert all(handles)
        assert all(dll.WaitForSingleObject(handle, 0) == 258 for handle in handles)
        if owner_exit == 'kill':
            supervisor.kill()
        else:
            supervisor.stdin.close()
        supervisor.wait(timeout=8)
        assert all(dll.WaitForSingleObject(handle, 5000) == 0 for handle in handles)
    finally:
        if supervisor.poll() is None:
            supervisor.kill()
        supervisor.wait(timeout=8)
        for handle in handles:
            if handle:
                dll.CloseHandle(handle)
        for stream in (supervisor.stdin, supervisor.stdout, supervisor.stderr):
            if stream and not stream.closed:
                stream.close()


def test_cmd_entry_resolves_its_own_directory_and_uses_pythonw():
    entry = (Path(__file__).resolve().parents[1] / 'Start Takeoff.cmd').read_text(encoding='ascii')
    assert '%~dp0apps\\api\\.venv311\\Scripts\\pythonw.exe' in entry
    assert '"%~dp0scripts\\desktop_launcher.py"' in entry
    assert '-EncodedCommand' in entry  # UTF-16 Korean missing-dependency message; no console encoding mutation.


def test_foreign_http_200_without_owned_child_signal_is_not_ready(monkeypatch):
    session = runtime.Session(threading.Event(), Mock())
    process = Mock()
    process.poll.return_value = None
    process.desktop_ready = threading.Event()
    opener = Mock()
    monkeypatch.setattr(runtime, 'build_opener', lambda *_: opener)
    with pytest.raises(runtime.LaunchError, match='시간이 초과'):
        session.wait_ready(process, 'http://127.0.0.1:1', 'API', timeout=0.01)
    opener.open.assert_not_called()


@pytest.mark.skipif(os.name != 'nt', reason='Windows prepared runtime integration')
def test_real_supervisor_graceful_stop_preserves_temporary_sqlite(tmp_path):
    try:
        runtime.assert_ports_free()
    except runtime.LaunchError:
        pytest.skip('A default port is already in use; never stop its owner for a test')
    root = runtime.ROOT
    if not (root / 'apps/api/.venv311/Scripts/python.exe').is_file() or not (root / 'apps/web/node_modules/vite/bin/vite.js').is_file():
        pytest.skip('Prepared API/web runtime unavailable')
    data = tmp_path / '공백 있는 합성 데이터'
    data.mkdir()
    env = os.environ.copy()
    env.update({'PYTHONUTF8': '1', 'TAKEOFF_DATABASE_URL': f'sqlite:///{(data / "qa.db").as_posix()}',
                'TAKEOFF_DATA_DIR': str(data), 'TAKEOFF_UPLOADS_DIR': str(data / 'uploads'),
                'TAKEOFF_RENDERED_PAGES_DIR': str(data / 'rendered'), 'TAKEOFF_EXPORTS_DIR': str(data / 'exports'),
                'TAKEOFF_AI_API_KEY': '', 'TAKEOFF_AI_MODEL': '', 'TAKEOFF_AI_VISION_MODEL': ''})
    process = subprocess.Popen([str(root / 'apps/api/.venv311/Scripts/python.exe'), '-u', str(root / 'scripts/desktop_runtime.py')],
                               cwd=root, env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, creationflags=runtime.CREATE_NO_WINDOW)
    events = queue.Queue()
    def read():
        for line in process.stdout:
            events.put(json.loads(line))
    threading.Thread(target=read, daemon=True).start()
    stopped = None
    try:
        deadline = time.monotonic() + 50
        while time.monotonic() < deadline:
            event = events.get(timeout=45)
            assert event['kind'] != 'stopped', event
            if event['kind'] == 'ready':
                break
        else:
            pytest.fail('Owned servers never signaled ready')
        opener = build_opener(ProxyHandler({}))
        with opener.open('http://127.0.0.1:8000/assist/config', timeout=5) as response:
            assert json.load(response)['ai_available'] is False
        request = Request('http://127.0.0.1:8000/projects', data=b'{"name":"synthetic-launcher-save"}',
                          headers={'Content-Type': 'application/json'}, method='POST')
        with opener.open(request, timeout=5) as response:
            assert json.load(response)['name'] == 'synthetic-launcher-save'
        process.stdin.close()
        deadline = time.monotonic() + 35
        while time.monotonic() < deadline:
            event = events.get(timeout=30)
            if event['kind'] == 'stopped':
                stopped = event['value']
                break
        process.wait(timeout=8)
        assert stopped == {'forced': False, 'error': None}
        runtime.assert_ports_free()
        with sqlite3.connect(data / 'qa.db') as db:
            assert db.execute("select name from projects where name='synthetic-launcher-save'").fetchone()
    finally:
        if not process.stdin.closed:
            process.stdin.close()
        try:
            process.wait(timeout=35)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=8)
        for stream in (process.stdout, process.stderr):
            stream.close()
