from app.db.session import get_db
from app.models import DrawingSheet
from test_known_takeoff_workflow import workflow, prepare
from test_assist_drafts import search, ceiling_payload


def saved_example(client):
    _,file_id,rows=prepare(client)
    run=search(client,file_id)
    payload=ceiling_payload(rows,run)
    payload['inputs']['width']['value']='4200'
    payload['inputs']['width']['unit']='mm'
    saved=client.post(f'/drawing-files/{file_id}/assist/drafts',json=payload)
    assert saved.status_code==200,saved.text
    return file_id,saved.json(),run


def test_review_shows_saved_conversion_and_sources_without_writes(workflow):
    client=workflow
    file_id,saved,_=saved_example(client)
    before=client.get(f'/drawing-files/{file_id}/measurements').json()
    response=client.get(f"/measurements/{saved['id']}/evidence")
    assert response.status_code==200
    data=response.json()
    assert data['quantity']=='11.34'
    assert data['status']=='DRAFT'
    width=next(i for i in data['inputs'] if i['name']=='width')
    assert (width['raw_value'],width['unit'],width['normalized_value'],width['normalized_unit'])==('4200','mm','4.2','m')
    assert {s['sheet_no'] for s in data['sources']}=={'ZX701','ZX201'}
    assert all(s['drawing_file_id']==file_id for s in data['sources'])
    assert client.get(f'/drawing-files/{file_id}/measurements').json()==before
    assert client.get('/measurements/999999/evidence').status_code==404


def test_review_flags_changed_original_and_manual_quantity(workflow):
    client=workflow
    _,saved,run=saved_example(client)
    gen=client.app.dependency_overrides[get_db]()
    db=next(gen)
    try:
        sheet=db.get(DrawingSheet,run['evidence'][0]['sheet_id'])
        sheet.text_content+='\nREVISED SOURCE'
        db.commit()
    finally:
        gen.close()
    assert client.patch(f"/measurements/{saved['id']}",json={'quantity':'12.00','formula':'manual edit'}).status_code==200
    data=client.get(f"/measurements/{saved['id']}/evidence").json()
    assert any(s['changed_since_saved'] for s in data['sources'])
    assert any('수동 변경' in w for w in data['warnings'])
    assert data['quantity']=='12.00'


def test_legacy_row_does_not_invent_normalized_inputs(workflow):
    client=workflow
    _,file_id,rows=prepare(client)
    row=next(r for r in rows if r['measurement_type']=='CEILING_AREA')
    data=client.get(f"/measurements/{row['id']}/evidence").json()
    assert data['inputs']==[]
    assert data['quantity'] is None
    assert any('기록이 없습니다' in w for w in data['warnings'])
    assert all(s['drawing_file_id']==file_id for s in data['sources'])


def test_foreign_and_malformed_snapshots_are_not_rendered_as_sources(workflow):
    client=workflow
    file_id,saved,_=saved_example(client)
    _,other_id,_=prepare(client)
    foreign=search(client,other_id)['evidence'][0]['sheet_id']
    malicious={'assist':{'inputs':{'inputs':{'width':{'sheet_id':foreign,'candidate_id':[],'value':{'unexpected':'object'}}}},
        'dimension_candidates':[{'candidate_id':[]}], 'evidence':[{'sheet_id':[], 'quote':{}}]}}
    assert client.patch(f"/measurements/{saved['id']}",json={'coordinates_json':malicious}).status_code==200
    response=client.get(f"/measurements/{saved['id']}/evidence")
    assert response.status_code==200,response.text
    data=response.json()
    assert data['inputs'][0]['source_sheet_id'] is None
    assert data['inputs'][0]['raw_value'] is None
    assert all(s['drawing_file_id']==file_id for s in data['sources'])
    assert foreign not in [s['sheet_id'] for s in data['sources']]


def test_malformed_saved_crop_requires_review_instead_of_failing_page(workflow):
    client=workflow
    _,saved,run=saved_example(client)
    coordinates=saved['coordinates_json']
    coordinates['assist']['evidence'][0]['vision_crop']=['invalid legacy crop']
    assert client.patch(f"/measurements/{saved['id']}",json={'coordinates_json':coordinates}).status_code==200
    response=client.get(f"/measurements/{saved['id']}/evidence")
    assert response.status_code==200,response.text
    source=next(s for s in response.json()['sources'] if s['sheet_id']==run['evidence'][0]['sheet_id'])
    assert source['changed_since_saved'] is True
    assert any('다시 확인' in w for w in response.json()['warnings'])
