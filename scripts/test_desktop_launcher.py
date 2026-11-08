"""GUI controller transitions without injecting native window messages."""
import importlib
import os
import queue
from unittest.mock import Mock

import pytest

pytestmark = pytest.mark.skipif(os.name != 'nt', reason='Windows native GUI controller')


def launcher(monkeypatch):
    module = importlib.import_module('desktop_launcher')
    ui = Mock()
    monkeypatch.setattr(module, 'NativeWindow', lambda owner: ui)
    return module.Launcher(), ui


def process():
    owned = Mock()
    owned.poll.return_value = None
    owned.stdin.closed = False
    return owned


def test_stop_closes_only_owned_supervisor_stdin_and_disables_actions(monkeypatch):
    app, ui = launcher(monkeypatch)
    app.process = owned = process()
    app.stop()
    owned.stdin.close.assert_called_once()
    owned.kill.assert_not_called()
    ui.enable.assert_any_call('stop', False)
    ui.enable.assert_any_call('browser', False)


def test_close_waits_for_process_exit_and_reader_eof(monkeypatch):
    app, ui = launcher(monkeypatch)
    app.process = owned = process()
    app.close()
    ui.destroy.assert_not_called()
    app.events.put((owned, {'kind': 'stopped', 'value': {'forced': False, 'error': None}}))
    app.poll()
    ui.destroy.assert_not_called()
    owned.poll.return_value = 0
    app.poll()
    ui.destroy.assert_not_called()
    app.events.put((owned, {'kind': 'eof', 'value': None}))
    app.poll()
    ui.destroy.assert_called_once()
    assert app.process is None


def test_failed_start_restores_retry_and_keeps_forced_close_warning_visible(monkeypatch):
    app, ui = launcher(monkeypatch)
    app.process = owned = process()
    app.closing = True
    owned.poll.return_value = 1
    app.events.put((owned, {'kind': 'stopped', 'value': {'forced': True, 'error': '합성 시작 실패'}}))
    app.events.put((owned, {'kind': 'eof', 'value': None}))
    app.poll()
    ui.text.assert_any_call('status', '합성 시작 실패')
    ui.enable.assert_any_call('start', True)
    ui.destroy.assert_not_called()
    ui.message.assert_called_once()
    assert not app.closing


def test_stale_events_cannot_open_browser_or_change_new_session(monkeypatch):
    app, ui = launcher(monkeypatch)
    app.process = process()
    app.open_browser = Mock()
    app.events.put((process(), {'kind': 'ready', 'value': {}}))
    app.poll()
    app.open_browser.assert_not_called()


def test_cancel_during_start_never_opens_browser(monkeypatch):
    app, ui = launcher(monkeypatch)
    app.process = owned = process()
    owned.stdin.closed = True
    app.open_browser = Mock()
    app.events.put((owned, {'kind': 'ready', 'value': {}}))
    app.poll()
    app.open_browser.assert_not_called()


def test_help_without_md_association_uses_quoted_argument_vector(monkeypatch):
    app, ui = launcher(monkeypatch)
    module = importlib.import_module('desktop_launcher')
    monkeypatch.setattr(module.os, 'startfile', Mock(side_effect=OSError('no association')))
    popen = Mock()
    monkeypatch.setattr(module.subprocess, 'Popen', popen)
    app.open_docs()
    command = popen.call_args.args[0]
    assert command[0].endswith('System32\\notepad.exe')
    assert command[1] == str(module.ROOT / 'docs/WINDOWS_LAUNCH.md')
    assert not popen.call_args.kwargs.get('shell')
    ui.message.assert_not_called()


def test_help_without_editor_still_shows_stop_and_backup_instructions(monkeypatch):
    app, ui = launcher(monkeypatch)
    module = importlib.import_module('desktop_launcher')
    monkeypatch.setattr(module.os, 'startfile', Mock(side_effect=OSError('no association')))
    monkeypatch.setattr(module.subprocess, 'Popen', Mock(side_effect=OSError('no editor')))
    app.open_docs()
    text = ui.message.call_args.args[1]
    assert '안전 종료 완료' in text and '실행 중 DB를 단순 복사하지' in text
    assert '원본 PDF' in text and 'Excel' in text and '덮어쓰지' in text
    assert all(scope in text for scope in ('DB', 'journal/WAL', '페이지 이미지'))
