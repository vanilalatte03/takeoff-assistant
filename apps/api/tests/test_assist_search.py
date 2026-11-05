import json
from unittest.mock import patch

import pytest
from pydantic import SecretStr, ValidationError
from app.core.config import settings
from app.services.assist_search import SearchArguments, model_search_arguments
from app.services.assist_search import local_search_arguments
from app.services.assist_search import search_sheets
from app.models import DrawingSheet, DrawingSheetRole
from test_known_takeoff_workflow import workflow, prepare


def test_local_query_preserves_finish_suffix_and_partition_code():
    assert local_search_arguments('110호 ACST-1 천장').finish_code == 'ACST-1'
    assert local_search_arguments('119호 5A 파티션').finish_code == '5A'
    assert local_search_arguments('5A 파티션').room_no is None


def test_architectural_evidence_is_not_crowded_out_by_repeated_numbers():
    sheets = [DrawingSheet(id=i+1,page_index=i,text_content='110 '*50,role=DrawingSheetRole.UNKNOWN,sheet_title='GENERAL NOTES') for i in range(20)]
    for i,role in enumerate([DrawingSheetRole.FINISH_SCHEDULE,DrawingSheetRole.FLOOR_PLAN,DrawingSheetRole.CEILING_PLAN,DrawingSheetRole.PARTITION_DETAIL]):
        sheets.append(DrawingSheet(id=30+i,page_index=30+i,text_content='Room 110 ACST',role=role,sheet_title=role.value))
    sheets.append(DrawingSheet(id=40,page_index=40,text_content='Room 110',role=DrawingSheetRole.UNKNOWN,sheet_title='CROSS SECTIONS'))
    args = SearchArguments(room_no='110',finish_code='ACST',keyword=None)
    evidence = search_sheets(sheets,args,'110호 ACST 천장')
    assert {e['role'] for e in evidence[:4]} == {'FINISH_SCHEDULE','FLOOR_PLAN','CEILING_PLAN','PARTITION_DETAIL'}
    assert search_sheets(sheets,args,'110호 파티션')[0]['role'] == 'PARTITION_DETAIL'
    assert any(e['sheet_id']==40 for e in evidence)


def test_local_evidence_scoped_and_no_measurement_writes(workflow):
    client = workflow
    _, file_id, rows = prepare(client)
    _, other_id, _ = prepare(client)
    root = f'/drawing-files/{file_id}'
    before = client.get(root + '/measurements').json()
    response = client.post(root + '/assist/search', json={'request': '110호 ACST 천장 면적 찾아줘'})
    assert response.status_code == 200
    result = response.json()
    assert result['status'] == 'NEEDS_REVIEW'
    assert len(result['evidence']) >= 2
    assert all('110' in e['quote'] or 'ACST' in e['quote'] for e in result['evidence'])
    assert {e['page_index'] for e in result['evidence']} >= {0, 1}
    assert all('quantity' not in e for e in result['evidence'])
    assert client.get(root + '/measurements').json() == before
    history = client.get(root + '/assist/runs').json()
    assert history[0]['run_id'] == result['run_id']
    assert client.get(f'/drawing-files/{other_id}/assist/runs').json() == []
    assert client.post('/drawing-files/9999/assist/search', json={'request': '110'}).status_code == 404


def test_no_match_and_empty_request(workflow):
    client = workflow
    _, file_id, _ = prepare(client)
    root = f'/drawing-files/{file_id}'
    result = client.post(root + '/assist/search', json={'request': '999호'}).json()
    assert result['status'] == 'NOT_FOUND'
    assert result['evidence'] == []
    assert client.post(root + '/assist/search', json={'request': '  '}).status_code == 422
    assert client.post(root + '/assist/search', json={'request': 'x'*501}).status_code == 422


def test_model_tool_is_executed_on_server_only(workflow, monkeypatch):
    client = workflow
    _, file_id, _ = prepare(client)
    from app.api.routes import assist
    calls = []
    def fake(prompt):
        calls.append(prompt)
        return SearchArguments(room_no='110', finish_code='ACST', keyword=None), {'model': 'test-only', 'usage': {'total_tokens': 10}}
    monkeypatch.setattr(assist, 'model_search_arguments', fake)
    result = client.post(f'/drawing-files/{file_id}/assist/search', json={'request': '110호 ACST', 'mode': 'ai'}).json()
    assert result['status'] == 'NEEDS_REVIEW'
    assert calls == ['110호 ACST']
    assert result['trace'][0]['tool'] == 'search_sheets'
    assert result['metadata']['usage']['total_tokens'] == 10
    before = client.get(f'/drawing-files/{file_id}/measurements').json()
    def failed(prompt):
        raise RuntimeError('sensitive provider response MUST NOT appear')
    monkeypatch.setattr(assist, 'model_search_arguments', failed)
    failed_result = client.post(f'/drawing-files/{file_id}/assist/search', json={'request': '110', 'mode': 'ai'}).json()
    assert failed_result['status'] == 'FAILED'
    assert 'sensitive' not in json.dumps(failed_result)
    assert client.get(f'/drawing-files/{file_id}/measurements').json() == before


def test_ai_not_configured_keeps_local_available(workflow, monkeypatch):
    monkeypatch.setattr(settings, 'ai_api_key', SecretStr(''))
    monkeypatch.setattr(settings, 'ai_model', '')
    client = workflow
    _, file_id, _ = prepare(client)
    assert client.get('/assist/config').json()['ai_available'] is False
    assert client.post(f'/drawing-files/{file_id}/assist/search', json={'request': '110', 'mode': 'ai'}).json()['status'] == 'FAILED'
    assert client.post(f'/drawing-files/{file_id}/assist/search', json={'request': '110'}).json()['status'] == 'NEEDS_REVIEW'


@pytest.mark.parametrize('extra', [{'project_id': 999}, {'drawing_file_id': 999}, {'status': 'CONFIRMED'}, {'room_no': 110}])
def test_untrusted_arguments_reject_scope_and_status(extra):
    with pytest.raises(ValidationError):
        SearchArguments.model_validate({'room_no': '110', 'finish_code': None, 'keyword': None, **extra})


def test_provider_contract_and_unrecognized_calls(monkeypatch):
    monkeypatch.setattr(settings, 'ai_api_key', SecretStr('test-key'))
    monkeypatch.setattr(settings, 'ai_model', 'configured-test-model')
    output = {'status': 'completed', 'id': 'fake', 'usage': {'total_tokens': 10}, 'output': [{'type': 'function_call', 'name': 'search_sheets', 'arguments': json.dumps({'room_no': '110', 'finish_code': 'ACST', 'keyword': None})}]}
    class Response:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def read(self, size): return json.dumps(output).encode()
    with patch('app.services.assist_search.urlopen', return_value=Response()) as transport:
        args, metadata = model_search_arguments('110호 ACST')
        payload = json.loads(transport.call_args.args[0].data)
        assert payload['store'] is False
        assert payload['input'] == '110호 ACST'
        assert payload['max_output_tokens'] == 500
        assert payload['parallel_tool_calls'] is False
        assert len(payload['tools']) == 1
        assert args.room_no == '110'
        output['output'][0]['name'] = 'create_measurement_draft'
        with pytest.raises(ValueError, match='INVALID_TOOL_CALL'):
            model_search_arguments('110')
