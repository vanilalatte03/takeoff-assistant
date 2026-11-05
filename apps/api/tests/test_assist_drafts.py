from decimal import Decimal
from io import BytesIO
from openpyxl import load_workbook
import pytest
from test_known_takeoff_workflow import workflow, prepare


def search(client, file_id, text='110호 ACST 천장'):
    response = client.post(f'/drawing-files/{file_id}/assist/search', json={'request': text})
    assert response.status_code == 200
    return response.json()


def ceiling_payload(rows, run):
    sheet = next(e for e in run['evidence'] if e['page_index'] == 1)
    return {
        'run_id': run['run_id'],
        'measurement_id': next(r['id'] for r in rows if r['room_no'] == '110' and r['measurement_type'] == 'CEILING_AREA'),
        'finish_code': 'ACST',
        'inputs': {name: {'value': value, 'unit': 'm', 'unit_confirmed': True, 'sheet_id': sheet['sheet_id'], 'note': 'User verified synthetic example dimension'} for name, value in [('width', '4.2'), ('height', '2.7')]},
        'deductions_reviewed': True,
    }


def test_e01_candidate_inputs_draft_export_and_e06_protection(workflow):
    client = workflow
    _, file_id, rows = prepare(client)
    run = search(client, file_id)
    body = ceiling_payload(rows, run)
    # Synthetic drawing has bare 4200/2700: explicit user unit confirmation is required.
    for field, raw in [('width', '4200'), ('height', '2700')]:
        candidate = next(c for c in run['dimensions'] if c['raw_text'] == raw and c['page_index'] == 1)
        body['inputs'][field] = {'candidate_id': candidate['candidate_id'], 'unit': 'mm', 'unit_confirmed': True,
            'sheet_id': candidate['sheet_id'], 'note': 'User confirmed drawing dimensions are mm'}
    response = client.post(f'/drawing-files/{file_id}/assist/drafts', json=body)
    assert response.status_code == 200, response.text
    saved = response.json()
    assert Decimal(saved['quantity']) == Decimal('11.34')
    assert (saved['formula'], saved['unit'], saved['status']) == ('4.2 * 2.7', 'm2', 'DRAFT')
    assert set(saved['source_sheets'].split(', ')) == {'ZX701', 'ZX201'}
    assert saved['coordinates_json']['assist']['run_id'] == run['run_id']
    assert saved['coordinates_json']['assist']['inputs']['inputs']['width']['unit'] == 'mm'
    workbook = load_workbook(BytesIO(client.get(f'/drawing-files/{file_id}/measurements/export').content))
    values = list(workbook['Details'].values)
    record = next(dict(zip(values[0], r)) for r in values[1:] if r[1] == '110' and r[4] == 'ACST')
    assert Decimal(str(record['Quantity'])) == Decimal('11.34')
    assert record['Status'] == 'DRAFT'
    assert client.patch(f"/measurements/{saved['id']}", json={'status': 'CONFIRMED'}).status_code == 200
    assert client.get(f'/drawing-files/{file_id}/assist/runs').json()[0]['review']['status'] == 'CONFIRMED'
    repeated = search(client, file_id)
    body['run_id'] = repeated['run_id']
    assert client.post(f'/drawing-files/{file_id}/assist/drafts', json=body).status_code == 409
    after = next(r for r in client.get(f'/drawing-files/{file_id}/measurements').json() if r['id'] == saved['id'])
    assert (after['quantity'], after['status'], after['coordinates_json']) == (saved['quantity'], 'CONFIRMED', saved['coordinates_json'])
    trace = client.get(f'/drawing-files/{file_id}/assist/runs').json()[1]['trace']
    assert [t['tool'] for t in trace][-2:] == ['calculate_quantity', 'create_measurement_draft']


def test_e02_partition_requires_explicit_faces(workflow):
    client = workflow
    _, file_id, rows = prepare(client)
    run = search(client, file_id, '119호 5A 파티션')
    detail = next(e for e in run['evidence'] if e['page_index'] == 2)
    body = {'run_id': run['run_id'], 'measurement_id': next(r['id'] for r in rows if r['room_no'] == '119' and r['measurement_type'] == 'PARTITION_AREA'),
        'finish_code': '5A', 'deductions_reviewed': True,
        'inputs': {field: {'value': value, 'unit': 'm', 'unit_confirmed': True, 'sheet_id': detail['sheet_id'], 'note': 'Synthetic example; user verified dimensions'} for field, value in [('wall_length', '4.2'), ('wall_height', '4.6')]}}
    assert client.post(f'/drawing-files/{file_id}/assist/drafts', json=body).status_code == 400
    body['side_multiplier'] = 1
    saved = client.post(f'/drawing-files/{file_id}/assist/drafts', json=body)
    assert saved.status_code == 200, saved.text
    assert (saved.json()['quantity'], saved.json()['finish_code'], saved.json()['status']) == ('19.32', '5A', 'DRAFT')
    assert 'ZX501' in saved.json()['source_sheets']


@pytest.mark.parametrize('mutation,code', [
    ('missing_dimension', 400), ('unknown_unit', 422), ('unconfirmed_unit', 422),
    ('unreviewed_deductions', 422), ('unknown_candidate', 400), ('wrong_sheet', 400),
    ('infinite', 422), ('negative', 422), ('too_large_deduction', 400),
    ('wrong_deduction_unit', 400), ('confirmed_status', 422), ('guessed_code', 400),
])
def test_e03_e05_invalid_inputs_do_not_write(workflow, mutation, code):
    client = workflow
    _, file_id, rows = prepare(client)
    run = search(client, file_id)
    body = ceiling_payload(rows, run)
    if mutation == 'missing_dimension': del body['inputs']['height']
    if mutation == 'unknown_unit': body['inputs']['width']['unit'] = 'unknown'
    if mutation == 'unconfirmed_unit': body['inputs']['width']['unit_confirmed'] = False
    if mutation == 'unreviewed_deductions': body['deductions_reviewed'] = False
    if mutation == 'unknown_candidate':
        body['inputs']['width'].pop('value')
        body['inputs']['width']['candidate_id'] = '99999:0'
    if mutation == 'wrong_sheet': body['inputs']['width']['sheet_id'] = 99999
    if mutation == 'infinite': body['inputs']['width']['value'] = 'NaN'
    if mutation == 'negative': body['inputs']['width']['value'] = '-1'
    if mutation == 'too_large_deduction': body['deductions'] = [{'amount': '1000', 'unit': 'm2', 'sheet_id': body['inputs']['width']['sheet_id'], 'note': 'Invalid deduction'}]
    if mutation == 'wrong_deduction_unit': body['deductions'] = [{'amount': '1', 'unit': 'm', 'sheet_id': body['inputs']['width']['sheet_id'], 'note': 'Wrong unit'}]
    if mutation == 'confirmed_status': body['status'] = 'CONFIRMED'
    if mutation == 'guessed_code': body['finish_code'] = 'INVENTED'
    before = client.get(f'/drawing-files/{file_id}/measurements').json()
    response = client.post(f'/drawing-files/{file_id}/assist/drafts', json=body)
    assert response.status_code == code, response.text
    assert client.get(f'/drawing-files/{file_id}/measurements').json() == before


def test_e04_multiple_sheets_stale_and_foreign_run(workflow):
    client = workflow
    _, file_id, rows = prepare(client)
    run = search(client, file_id)
    assert len(run['evidence']) >= 2
    assert any('여러 개' in w for w in run['warnings'])
    body = ceiling_payload(rows, run)
    _, other_id, _ = prepare(client)
    assert client.post(f'/drawing-files/{other_id}/assist/drafts', json=body).status_code == 400
    # Reprocessing/altering page text invalidates prior search evidence.
    from app.db.session import get_db
    from app.models import DrawingSheet
    # Use an explicit session lifetime through the override generator.
    gen = client.app.dependency_overrides[get_db]()
    db = next(gen)
    try:
        sheet = db.get(DrawingSheet, run['evidence'][0]['sheet_id'])
        sheet.text_content += '\nREVISED DRAWING TEXT'
        db.commit()
    finally:
        gen.close()
    assert client.post(f'/drawing-files/{file_id}/assist/drafts', json=body).status_code == 400


def test_deductions_and_manual_correction_are_preserved(workflow):
    client = workflow
    _, file_id, rows = prepare(client)
    run = search(client, file_id)
    body = ceiling_payload(rows, run)
    body['deductions'] = [{'amount': '1.34', 'unit': 'm2', 'sheet_id': body['inputs']['width']['sheet_id'], 'note': 'Synthetic opening; user verified 1.34m2'}]
    response = client.post(f'/drawing-files/{file_id}/assist/drafts', json=body)
    assert response.status_code == 200, response.text
    assert response.json()['quantity'] == '10.00'
    assert response.json()['formula'] == '4.2 * 2.7 - 1.34'
    assert response.json()['deductions_json']['items'][0]['amount'] == '1.34'
    restored=response.json()['coordinates_json']['calculation_inputs']
    assert (restored['width'],restored['height'],restored['calculation_type'])==('4.2','2.7','AREA_RECTANGLE')
    assert restored['deductions']==[{'amount':'1.34','label':'Synthetic opening; user verified 1.34m2'}]
    assert client.post(f'/drawing-files/{file_id}/assist/drafts', json=body).status_code == 200
    assert len(client.get(f'/drawing-files/{file_id}/measurements').json()) == len(rows)


def test_model_assisted_search_can_feed_the_same_verified_draft_tools(workflow, monkeypatch):
    from app.api.routes import assist
    from app.services.assist_search import SearchArguments
    monkeypatch.setattr(assist, 'model_search_arguments', lambda prompt: (SearchArguments(room_no='110', finish_code='ACST', keyword=None), {'model':'test-only'}))
    client = workflow
    _, file_id, rows = prepare(client)
    response = client.post(f'/drawing-files/{file_id}/assist/search', json={'request':'110호 ACST', 'mode':'ai'})
    assert response.json()['mode'] == 'ai'
    payload = ceiling_payload(rows, response.json())
    saved = client.post(f'/drawing-files/{file_id}/assist/drafts', json=payload)
    assert saved.status_code == 200, saved.text
    assert (saved.json()['quantity'], saved.json()['status']) == ('11.34','DRAFT')
    assert client.patch(f"/measurements/{saved.json()['id']}", json={'status':'CONFIRMED'}).status_code == 200
    rerun = client.post(f'/drawing-files/{file_id}/assist/search', json={'request':'110호 ACST','mode':'ai'}).json()
    payload['run_id'] = rerun['run_id']
    assert client.post(f'/drawing-files/{file_id}/assist/drafts', json=payload).status_code == 409


def test_review_trace_follows_reopen_recalculate_and_reject(workflow):
    client=workflow
    _,file_id,rows=prepare(client)
    run=search(client,file_id)
    saved=client.post(f'/drawing-files/{file_id}/assist/drafts',json=ceiling_payload(rows,run)).json()
    row_id=saved['id']
    def review():
        return next(r for r in client.get(f'/drawing-files/{file_id}/assist/runs').json() if r['run_id']==run['run_id'])['review']
    assert client.patch(f'/measurements/{row_id}',json={'status':'CONFIRMED'}).status_code==200
    assert review()['status']=='CONFIRMED'
    assert client.patch(f'/measurements/{row_id}',json={'status':'DRAFT'}).status_code==200
    assert review()['status']=='DRAFT'
    response=client.post(f'/measurements/{row_id}/calculate',json={'calculation_type':'AREA_RECTANGLE','width':'5','height':'2','source_sheets':saved['source_sheets']})
    assert response.status_code==200,response.text
    assert review()['quantity']=='10.00'
    assert client.delete(f'/measurements/{row_id}').status_code==200
    assert review()['status']=='REJECTED'


def test_assist_replaces_old_calculation_and_archives_merged_evidence(workflow):
    from app.db.session import get_db
    from app.models import Measurement
    client=workflow
    _,file_id,rows=prepare(client)
    run=search(client,file_id)
    payload=ceiling_payload(rows,run)
    gen=client.app.dependency_overrides[get_db]()
    db=next(gen)
    try:
        row=db.get(Measurement,payload['measurement_id'])
        row.coordinates_json={'calculation_inputs':{'width':'99'},'merge_provenance':{'rows':[{'measurement_id':999}]}}
        db.commit()
    finally:
        gen.close()
    result=client.post(f'/drawing-files/{file_id}/assist/drafts',json=payload)
    assert result.status_code==200,result.text
    coordinates=result.json()['coordinates_json']
    assert coordinates['calculation_inputs']['width']=='4.2'
    assert 'merge_provenance' not in coordinates
    assert coordinates['history'][0]['merge_provenance']['rows'][0]['measurement_id']==999


def test_merged_assist_target_keeps_review_tracking_after_rejection(workflow):
    client=workflow
    _,file_id,rows=prepare(client)
    run=search(client,file_id)
    payload=ceiling_payload(rows,run)
    target=client.post(f'/drawing-files/{file_id}/assist/drafts',json=payload).json()
    # Two compatible synthetic rows; use an explicit fixture copy as the second source.
    from app.db.session import get_db
    from app.models import Measurement
    gen=client.app.dependency_overrides[get_db]()
    db=next(gen)
    try:
        row=db.get(Measurement,target['id'])
        source=Measurement(project_id=row.project_id,room_finish_id=row.room_finish_id,room_no=row.room_no,
            category=row.category,finish_code=row.finish_code,measurement_type=row.measurement_type,
            quantity=row.quantity,formula=row.formula,unit=row.unit,source_sheets=row.source_sheets,status=row.status)
        db.add(source);db.commit();source_id=source.id
    finally:
        gen.close()
    merged=client.post('/measurements/merge',json={'target_id':target['id'],'source_ids':[source_id]})
    assert merged.status_code==200,merged.text
    assert merged.json()['quantity']=='22.68'
    assert client.delete(f"/measurements/{target['id']}").status_code==200
    review=next(r for r in client.get(f'/drawing-files/{file_id}/assist/runs').json() if r['run_id']==run['run_id'])['review']
    assert (review['status'],review['quantity'])==('REJECTED','22.68')
