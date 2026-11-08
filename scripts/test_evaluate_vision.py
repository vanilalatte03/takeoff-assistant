import json
from pathlib import Path
import sys
from unittest.mock import patch

import pytest
from pydantic import SecretStr

sys.path.insert(0, str(Path(__file__).parent))
import evaluate_vision as evaluation


def test_reproducible_gold_images_and_default_never_calls_model(tmp_path):
    with patch.object(evaluation.assist_vision, 'read_crop', side_effect=AssertionError('no paid call')):
        report = evaluation.evaluate(image_dir=tmp_path)
        assert report == evaluation.evaluate()
    assert report['model_quality'] == 'NOT_RUN'
    assert len(report['cases']) == 5
    for case in report['cases']:
        assert case['metrics'] is None and case['metadata'] is None and case['elapsed_ms'] is None
        assert evaluation.digest((tmp_path/(case['id']+'.png')).read_bytes()) == case['image_sha256']
    assert report['cases'][3]['expected'][0]['unit'] == 'unknown'
    assert report['cases'][4]['expected'] == []


def test_scoring_separates_blank_unit_omission_and_value_errors():
    token = evaluation.token
    assert evaluation.score([], [token('dimension', '123')])['blank_false_positives'] == 1
    assert evaluation.score([token('dimension', '4200')], [])['omissions'] == 1
    assert evaluation.score([token('dimension', '4200')], [token('dimension', '4200', 'mm')])['unit_errors'] == 1
    wrong = evaluation.score([token('dimension', '4200')], [token('room_no', '420')])
    assert (wrong['false_positives'], wrong['omissions'], wrong['value_or_kind_errors']) == (1, 1, 1)


def test_committed_corpus_matches_generated_truth_and_bytes():
    report = json.loads((evaluation.ROOT/'docs/evaluation/vision-manifest-v1.json').read_text(encoding='utf-8'))
    assert report['model_quality'] == 'NOT_RUN'
    generated = evaluation.corpus()
    assert report['truth_sha256'] == evaluation.digest(evaluation.json_bytes([case for case, _ in generated]))
    for case, png in generated:
        assert (evaluation.ROOT/'docs/evaluation/vision-v1'/f"{case['id']}.png").read_bytes() == png


def test_offline_cli_rejects_credential_file_before_reading(monkeypatch):
    monkeypatch.setattr(sys, 'argv', ['evaluate_vision.py', '--output', 'unused.json', '--env-file', 'never-read.env'])
    with pytest.raises(SystemExit) as exc:
        evaluation.main()
    assert exc.value.code == 2


def test_explicit_live_cli_uses_only_selected_credentials_and_model(tmp_path, monkeypatch):
    env = tmp_path/'explicit.env'
    env.write_text('TAKEOFF_AI_API_KEY=synthetic-secret\nTAKEOFF_AI_MODEL=unused-search\nTAKEOFF_AI_VISION_MODEL=unused-file-model\n', encoding='utf-8')
    report_path = tmp_path/'result.json'
    monkeypatch.setattr(evaluation.assist_vision.settings, 'ai_api_key', SecretStr(''))
    monkeypatch.setattr(evaluation.assist_vision.settings, 'ai_vision_model', '')
    seen = []
    def substitute(png):
        assert evaluation.assist_vision.settings.ai_api_key.get_secret_value() == 'synthetic-secret'
        assert evaluation.assist_vision.settings.ai_vision_model == 'chosen-model'
        seen.append(png)
        return evaluation.assist_vision.VisionOutput(items=[]), {'model':'chosen-model', 'usage':{}}
    monkeypatch.setattr(evaluation.assist_vision, 'read_crop', substitute)
    monkeypatch.setattr(sys, 'argv', ['evaluate_vision.py', '--live', '--env-file', str(env), '--model', 'chosen-model', '--output', str(report_path)])
    assert evaluation.main() == 0
    assert len(seen) == 5
    saved = report_path.read_text(encoding='utf-8')
    assert 'synthetic-secret' not in saved and str(env) not in saved and 'unused-search' not in saved
    assert 'synthetic-secret' in env.read_text(encoding='utf-8')


@pytest.mark.parametrize('failure', ['no_output', 'malformed', 'provider_failure'])
def test_live_path_reuses_reader_but_transport_contract_failure_is_not_negative_truth(monkeypatch, failure):
    """Mocked transport only; assertions here are never a live-quality result."""
    monkeypatch.setattr(evaluation.assist_vision.settings, 'ai_api_key', SecretStr('test-only'))
    monkeypatch.setattr(evaluation.assist_vision.settings, 'ai_vision_model', 'test-only')
    class Response:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def read(self, size):
            output = [] if failure == 'no_output' else [{'type':'function_call', 'name':'report_candidates', 'arguments':'{"items":invalid}'}]
            return json.dumps({'status':'completed', 'output':output}).encode()
    with patch.object(evaluation.assist_vision, 'urlopen', side_effect=TimeoutError('private fake body') if failure == 'provider_failure' else None, return_value=Response()):
        report = evaluation.evaluate(live=True)
    assert report['model_quality'] == 'INCOMPLETE'
    assert all(case['status'] == 'FAILED' and case['metrics'] is None for case in report['cases'])
    assert 'private fake body' not in json.dumps(report)


def test_substitute_response_metrics_are_only_a_scorer_contract(monkeypatch):
    seen = []
    def substitute(png):
        seen.append(evaluation.digest(png))
        return evaluation.assist_vision.VisionOutput(items=[]), {'model':'test-only', 'response_id':'fake', 'usage':{'total_tokens':1}}
    monkeypatch.setattr(evaluation.assist_vision, 'read_crop', substitute)
    report = evaluation.evaluate(live=True)
    assert seen == [case['image_sha256'] for case in report['cases']]
    assert report['cases'][0]['metrics']['omissions'] == 1
    assert report['cases'][1]['metrics'] is None
    assert report['cases'][1]['diagnostic']['abstained'] is True
    assert report['cases'][-1]['metrics']['blank_false_positives'] == 0
    assert all(case['metadata']['usage']['total_tokens'] == 1 for case in report['cases'])
