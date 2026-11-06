"""Synthetic preparation, retry and review-data preservation contracts."""
from unittest.mock import patch

from app.api.routes import workflow as routes
from app.main import app
from app.models import DrawingSheet, DrawingSheetRole, ReviewStatus
from test_known_takeoff_workflow import workflow, synthetic_pdf, prepare  # noqa: F401


def upload(client):
    project = client.post('/projects', json={'name': 'Guided synthetic'}).json()
    return client.post('/drawing-files/upload', data={'project_id': project['id']},
                       files={'file': ('guided.pdf', synthetic_pdf(), 'application/pdf')}).json()['id']


def finish(client, file_id):
    url = f'/drawing-files/{file_id}/workflow'
    for _ in range(5):
        response = client.post(url + '/prepare')
        assert response.status_code == 200, response.text
    return client.get(url).json()


def test_preparation_checkpoints_retry_and_duplicate_protection(workflow):
    client = workflow
    file_id = upload(client)
    url = f'/drawing-files/{file_id}/workflow'
    assert client.get(url).json()['completed'] == 0
    with patch.object(routes, '_render_page_png', return_value='failed'):
        assert client.post(url + '/prepare').status_code == 500
    assert client.get(url).json()['completed'] == 0
    assert client.post(url + '/prepare').json()['completed'] == 1
    with patch.object(routes, 'detect_and_apply_sheet_metadata', side_effect=RuntimeError('synthetic failure')):
        assert client.post(url + '/prepare').status_code == 500
    assert client.get(url).json()['completed'] == 1
    with patch.object(routes, '_render_page_png', side_effect=AssertionError('must skip completed processing')):
        result = finish(client, file_id)
    assert result['completed'] == 5 and result['ready']
    assert result['finish_count'] == 2 and result['measurement_count'] == 10
    before = client.get(f'/drawing-files/{file_id}/measurements').json()
    assert client.post(url + '/prepare').json() == result
    assert client.get(f'/drawing-files/{file_id}/measurements').json() == before
    lock = routes._locks[file_id % len(routes._locks)]
    with lock:
        assert client.post(url + '/prepare').status_code == 409


def test_legacy_resume_keeps_corrected_metadata_and_all_review_evidence(workflow):
    client = workflow
    _, file_id, rows = prepare(client)
    selected = rows[:3]
    for index, row in enumerate(selected):
        response = client.post(f"/measurements/{row['id']}/calculate", json={
            'calculation_type': 'AREA_RECTANGLE', 'width': '4.2', 'height': '2.7',
            'source_sheets': 'ZX701, ZX201',
            'deductions': [{'label': 'Synthetic opening', 'amount': '1', 'formula': '1 * 1'}],
        }) if row['measurement_type'] in ('FLOOR_AREA', 'CEILING_AREA') else client.patch(
            f"/measurements/{row['id']}", json={'memo': 'User edit preserved'})
        assert response.status_code == 200, response.text
        if index == 0:
            assert client.patch(f"/measurements/{row['id']}", json={'status': 'CONFIRMED'}).status_code == 200
        elif index == 1:
            assert client.delete(f"/measurements/{row['id']}").status_code == 200
    before_rows = client.get(f'/drawing-files/{file_id}/measurements').json()
    before_finishes = client.get(f'/drawing-files/{file_id}/room-finishes').json()
    # Direct DB edits represent deliberate manual classification, even UNKNOWN.
    sessions = app.dependency_overrides[routes.get_db]()
    db = next(sessions)
    sheets = db.query(DrawingSheet).filter_by(drawing_file_id=file_id).all()
    sheets[0].sheet_no = 'USER-CORRECTED'
    sheets[0].role = DrawingSheetRole.UNKNOWN
    sheets[0].status = ReviewStatus.CONFIRMED
    sheets[1].text_content = 'User preserved text'
    db.commit()
    snapshots = [(s.id, s.sheet_no, s.role, s.text_content, s.status) for s in sheets]
    with patch.object(routes, 'detect_and_apply_sheet_metadata', side_effect=AssertionError('legacy metadata reset')):
        result = finish(client, file_id)
    db.expire_all()
    assert [(s.id, s.sheet_no, s.role, s.text_content, s.status) for s in sheets] == snapshots
    sessions.close()
    assert result['ready'] and result['warnings']
    assert client.get(f'/drawing-files/{file_id}/measurements').json() == before_rows
    assert client.get(f'/drawing-files/{file_id}/room-finishes').json() == before_finishes


def test_zero_candidates_are_visible_not_ready(workflow):
    client = workflow
    file_id = upload(client)
    with patch.object(routes, 'classify_and_apply_sheet_roles', return_value=[]):
        state = finish(client, file_id)
    assert state['completed'] == 5
    assert not state['ready']
    assert state['finish_count'] == state['measurement_count'] == 0
    assert state['warnings']
