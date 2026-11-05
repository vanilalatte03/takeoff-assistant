import pytest
from test_known_takeoff_workflow import workflow, prepare


def manual():
    return {'task_key':'E-01 synthetic','mode':'manual','elapsed_seconds':120,'correction_count':2,
        'manual_interventions':3,'error_count':1,'review_result':'needs_review','notes':'Synthetic observation, not a field trial'}


def test_comparison_records_scope_version_and_user_reported_status(workflow):
    client = workflow
    _, file_id, _ = prepare(client)
    path = f'/drawing-files/{file_id}/assist/trials'
    baseline = client.post(path,json=manual())
    assert baseline.status_code == 201,baseline.text
    assert baseline.json()['verification'] == 'user_reported'
    assert len(baseline.json()['drawing_fingerprint']) == 64
    run = client.post(f'/drawing-files/{file_id}/assist/search',json={'request':'110호 ACST'}).json()
    comparison = client.post(path,json={**manual(),'mode':'local','run_id':run['run_id'],'elapsed_seconds':100})
    assert comparison.status_code == 201
    assert comparison.json()['drawing_fingerprint'] == baseline.json()['drawing_fingerprint']
    records = client.get(path).json()
    assert [r['mode'] for r in records] == ['local','manual']
    assert all(r['task_key'] == 'E-01 synthetic' for r in records)
    _, other_id, _ = prepare(client)
    assert client.get(f'/drawing-files/{other_id}/assist/trials').json() == []
    assert client.post(f'/drawing-files/{other_id}/assist/trials',json={**manual(),'mode':'local','run_id':run['run_id']}).status_code == 400
    assert client.post(path,json={**manual(),'mode':'ai','run_id':run['run_id']}).status_code == 400
    assert client.post(path,json={**manual(),'run_id':run['run_id']}).status_code == 400
    assert client.get('/drawing-files/999999/assist/trials').status_code == 404


@pytest.mark.parametrize('change',[{'elapsed_seconds':0},{'correction_count':-1},{'review_result':'CONFIRMED'},{'task_key':'  '},{'notes':''}])
def test_invalid_trial_is_not_saved(workflow,change):
    client = workflow
    _, file_id, _ = prepare(client)
    path = f'/drawing-files/{file_id}/assist/trials'
    response = client.post(path,json={**manual(),**change})
    assert response.status_code == 422,response.text
    assert client.get(path).json() == []
