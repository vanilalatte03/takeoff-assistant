import importlib.util
from pathlib import Path
import sys
from unittest.mock import patch

spec=importlib.util.spec_from_file_location('run_api',Path(__file__).with_name('run_api.py'))
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_external_env_launcher_keeps_secrets_out_of_output(tmp_path,monkeypatch,capsys):
    env=tmp_path/'settings.env'
    env.write_text('TAKEOFF_AI_MODEL=test-model\nTAKEOFF_AI_API_KEY=not-a-real-key\n',encoding='utf-8')
    for key in ('TAKEOFF_AI_MODEL','TAKEOFF_AI_API_KEY','TAKEOFF_AI_VISION_MODEL'):
        monkeypatch.delenv(key,raising=False)
    monkeypatch.setattr(sys,'argv',['run_api.py','--env-file',str(env),'--vision-use-search-model','--port','8123'])
    monkeypatch.setattr(sys,'path',list(sys.path))
    with patch.dict('os.environ',{},clear=False), patch('uvicorn.run') as run:
        module.main()
        run.assert_called_once_with('app.main:app',host='127.0.0.1',port=8123,reload=False)
        import os
        assert os.environ['TAKEOFF_AI_VISION_MODEL']=='test-model'
    assert 'not-a-real-key' not in capsys.readouterr().out
    assert env.read_text(encoding='utf-8').count('TAKEOFF_AI_VISION_MODEL')==0


def test_vision_is_not_enabled_without_explicit_flag(tmp_path,monkeypatch):
    env=tmp_path/'settings.env'
    env.write_text('TAKEOFF_AI_MODEL=test-model\n',encoding='utf-8')
    monkeypatch.delenv('TAKEOFF_AI_VISION_MODEL',raising=False)
    monkeypatch.setattr(sys,'argv',['run_api.py','--env-file',str(env)])
    monkeypatch.setattr(sys,'path',list(sys.path))
    with patch.dict('os.environ',{},clear=False), patch('uvicorn.run'):
        module.main()
        import os
        assert not os.environ.get('TAKEOFF_AI_VISION_MODEL')
