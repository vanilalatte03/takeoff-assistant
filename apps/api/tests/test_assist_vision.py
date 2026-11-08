import base64
import json
from pathlib import Path
from unittest.mock import patch

import fitz
import pytest
from pydantic import SecretStr, ValidationError
from app.core.config import settings
from app.db.session import get_db
from app.models import DrawingFile
from app.services.assist_vision import CropRegion, VisionOutput, read_crop
from test_known_takeoff_workflow import workflow


REGION = {'x':20,'y':40,'width':300,'height':180,'image_width':600,'image_height':800}


def prepare_scan(client):
    with fitz.open() as raster:
        page = raster.new_page(width=600,height=800)
        page.insert_text((50,100),'Room 110 ACST 4200 2700',fontsize=16)
        page.insert_text((50,700),'SYNTHETIC TITLE OUTSIDE CROP',fontsize=20)
        image = page.get_pixmap().tobytes('png')
    with fitz.open() as document:
        page = document.new_page(width=600,height=800)
        page.insert_image(page.rect,stream=image)
        assert page.get_text() == ''
        page = document.new_page()
        page.insert_text((40,60),'ZX701 FINISH SCHEDULE\nRM NOS | ROOM NAMES | FLOOR | BASE | INTERIOR WALL | CEILING | HGT\n110 | OFFICE | VCT | RB | GWB | ACST | 2.7m',fontsize=9)
        pdf = document.tobytes()
    project = client.post('/projects',json={'name':'Synthetic scanned drawing'}).json()
    uploaded = client.post('/drawing-files/upload',data={'project_id':project['id']},files={'file':('synthetic-scan.pdf',pdf,'application/pdf')})
    file_id = uploaded.json()['id']
    for step in ('pages/process','sheets/detect','sheets/classify','room-finishes/extract','measurements/generate'):
        assert client.post(f'/drawing-files/{file_id}/{step}').status_code == 200
    return file_id


def preview(client,file_id):
    response = client.post(f'/drawing-files/{file_id}/pages/0/assist/vision-preview',json={'region':REGION})
    assert response.status_code == 200,response.text
    assert response.headers['Cache-Control'] == 'no-store'
    pixmap = fitz.Pixmap(response.content)
    assert (pixmap.width,pixmap.height) == (600,360)
    return response


def body(hash):
    return {'region':REGION,'consent':True,'failure_reason':'no_text','note':'Synthetic scanned dimensions lack text layer','preview_sha256':hash}


def output():
    return VisionOutput.model_validate({'items':[
        {'kind':'dimension','raw_text':'4200','unit':'unknown','bbox':None},
        {'kind':'dimension','raw_text':'2700','unit':'unknown','bbox':None},
        {'kind':'finish_code','raw_text':'ACST','unit':'unknown','bbox':None},
        {'kind':'room_no','raw_text':'110','unit':'unknown','bbox':None},
    ]})


def test_scan_crop_only_and_reviewed_draft(workflow,monkeypatch):
    client = workflow
    file_id = prepare_scan(client)
    cropped = preview(client,file_id)
    from app.api.routes import assist
    transmitted = []
    def fake(data):
        transmitted.append(data)
        return output(),{'model':'test-only','usage':{'total_tokens':20}}
    monkeypatch.setattr(assist,'read_crop',fake)
    before = client.get(f'/drawing-files/{file_id}/measurements').json()
    result = client.post(f'/drawing-files/{file_id}/pages/0/assist/vision',json=body(cropped.headers['X-Crop-SHA256']))
    assert result.status_code == 200,result.text
    run = result.json()
    assert transmitted == [cropped.content]
    assert run['status'] == 'NEEDS_REVIEW'
    assert all(c['suggested_value'] is None and c['unit_confirmed'] is False for c in run['dimensions'])
    assert client.get(f'/drawing-files/{file_id}/measurements').json() == before
    row = next(r for r in before if r['measurement_type'] == 'CEILING_AREA')
    payload = {'run_id':run['run_id'],'measurement_id':row['id'],'finish_code':'ACST','deductions_reviewed':True,
        'inputs': {field:{'candidate_id':run['dimensions'][i]['candidate_id'],'unit':'mm','unit_confirmed':True,
            'sheet_id':run['evidence'][0]['sheet_id'],'note':'User verified scanned source dimensions and mm units'} for i,field in enumerate(('width','height'))}}
    saved = client.post(f'/drawing-files/{file_id}/assist/drafts',json=payload)
    assert saved.status_code == 200,saved.text
    assert (saved.json()['quantity'],saved.json()['status']) == ('11.34','DRAFT')
    assert saved.json()['coordinates_json']['assist']['evidence'][0]['vision_crop']['sha256'] == cropped.headers['X-Crop-SHA256']


@pytest.mark.parametrize('mutation,status',[('no_consent',422),('no_preview',409),('outside',422),('whole_page',422),('arbitrary_path',422)])
def test_invalid_or_unreviewed_region_never_calls_model(workflow,monkeypatch,mutation,status):
    client = workflow
    file_id = prepare_scan(client)
    cropped = preview(client,file_id)
    payload = body(cropped.headers['X-Crop-SHA256'])
    if mutation == 'no_consent': payload['consent'] = False
    if mutation == 'no_preview': payload['preview_sha256'] = '0'*64
    if mutation == 'outside': payload['region'] = {**REGION,'x':99999}
    if mutation == 'whole_page': payload['region'] = {**REGION,'x':0,'y':0,'width':600,'height':800}
    if mutation == 'arbitrary_path': payload['path'] = 'outside.pdf'
    with patch('app.api.routes.assist.read_crop') as model:
        response = client.post(f'/drawing-files/{file_id}/pages/0/assist/vision',json=payload)
        assert response.status_code == status,response.text
        model.assert_not_called()


def test_vision_failure_and_unreadable_result_remain_explicit(workflow,monkeypatch):
    client = workflow
    file_id = prepare_scan(client)
    cropped = preview(client,file_id)
    monkeypatch.setattr(settings,'ai_api_key',SecretStr(''))
    monkeypatch.setattr(settings,'ai_vision_model','')
    result = client.post(f'/drawing-files/{file_id}/pages/0/assist/vision',json=body(cropped.headers['X-Crop-SHA256'])).json()
    assert result['status'] == 'FAILED'
    assert result['evidence'] == []
    from app.api.routes import assist
    monkeypatch.setattr(assist,'read_crop',lambda data:(VisionOutput(items=[]),{'model':'test-only'}))
    result = client.post(f'/drawing-files/{file_id}/pages/0/assist/vision',json=body(cropped.headers['X-Crop-SHA256'])).json()
    assert result['status'] == 'NOT_FOUND'
    assert result['dimensions'] == []
    assert client.get('/drawing-files/99999/pages/0/assist/vision-preview').status_code == 405
    assert client.post('/drawing-files/99999/pages/0/assist/vision-preview',json={'region':REGION}).status_code == 404


def test_provider_image_contract_and_untrusted_response(monkeypatch):
    monkeypatch.setattr(settings,'ai_api_key',SecretStr('fake-key'))
    monkeypatch.setattr(settings,'ai_vision_model','test-vision-model')
    response = {'status':'completed','id':'fake','output':[{'type':'function_call','name':'report_candidates','arguments':output().model_dump_json()}]}
    class FakeResponse:
        def __enter__(self): return self
        def __exit__(self,*args): pass
        def read(self,size): return json.dumps(response).encode()
    with patch('app.services.assist_vision.urlopen',return_value=FakeResponse()) as transport:
        result,_ = read_crop(b'synthetic-crop-only')
        assert len(result.items) == 4
        payload = json.loads(transport.call_args.args[0].data)
        data_url = payload['input'][0]['content'][1]['image_url']
        assert base64.b64decode(data_url.split(',')[1]) == b'synthetic-crop-only'
        assert payload['store'] is False
        assert payload['max_output_tokens'] == 1500
        assert len(payload['tools']) == 1
        response['output'][0]['name'] = 'create_measurement_draft'
        with pytest.raises(ValueError,match='INVALID_VISION_RESPONSE'): read_crop(b'image')
    with pytest.raises(ValidationError):
        VisionOutput.model_validate({'items':[{'kind':'dimension','raw_text':'4.2','unit':'m','bbox':None,'status':'CONFIRMED'}]})


def test_replaced_pdf_invalidates_preview_and_vision_draft(workflow,monkeypatch):
    client = workflow
    file_id = prepare_scan(client)
    cropped = preview(client,file_id)
    from app.api.routes import assist
    monkeypatch.setattr(assist,'read_crop',lambda data:(output(),{'model':'test-only'}))
    run = client.post(f'/drawing-files/{file_id}/pages/0/assist/vision',json=body(cropped.headers['X-Crop-SHA256'])).json()
    row = next(r for r in client.get(f'/drawing-files/{file_id}/measurements').json() if r['measurement_type']=='CEILING_AREA')
    gen = client.app.dependency_overrides[get_db]()
    db = next(gen)
    try:
        path = Path(db.get(DrawingFile,file_id).stored_path)
        with fitz.open(path) as doc:
            doc[0].insert_text((30,80),'REVISED DIMENSION',fontsize=12)
            updated = doc.tobytes()
        path.write_bytes(updated)
    finally:
        gen.close()
    with patch('app.api.routes.assist.read_crop') as model:
        assert client.post(f'/drawing-files/{file_id}/pages/0/assist/vision',json=body(cropped.headers['X-Crop-SHA256'])).status_code == 409
        model.assert_not_called()
    payload = {'run_id':run['run_id'],'measurement_id':row['id'],'finish_code':'ACST','deductions_reviewed':True,
        'inputs':{field:{'candidate_id':run['dimensions'][i]['candidate_id'],'unit':'mm','unit_confirmed':True,
            'sheet_id':run['evidence'][0]['sheet_id'],'note':'Original scan reviewed'} for i,field in enumerate(('width','height'))}}
    response = client.post(f'/drawing-files/{file_id}/assist/drafts',json=payload)
    assert response.status_code == 400,response.text
    assert '이미지가 변경' in response.json()['detail']
    assert next(r for r in client.get(f'/drawing-files/{file_id}/measurements').json() if r['id']==row['id'])['quantity'] is None


@pytest.mark.parametrize('scenario', ['wrong_value', 'inferred_unit', 'mixed_room', 'blank_false_positive', 'no_output', 'malformed', 'provider_failure'])
def test_bad_vision_candidates_cannot_bypass_review_or_mutate_measurements(workflow, monkeypatch, scenario):
    """Substitute responses verify storage contracts, never model accuracy."""
    client = workflow
    file_id = prepare_scan(client)
    region = {**REGION, 'y':300} if scenario == 'blank_false_positive' else REGION
    cropped = client.post(f'/drawing-files/{file_id}/pages/0/assist/vision-preview', json={'region':region})
    assert cropped.status_code == 200
    before = client.get(f'/drawing-files/{file_id}/measurements').json()
    row = next(r for r in before if r['measurement_type'] == 'CEILING_AREA')
    from app.api.routes import assist
    def substitute(data):
        if scenario in {'no_output', 'malformed', 'provider_failure'}:
            raise ValueError('INVALID_VISION_RESPONSE') if scenario != 'provider_failure' else TimeoutError('private provider body')
        items = output().model_dump()['items']
        if scenario == 'wrong_value': items[0]['raw_text'] = '420'
        if scenario == 'inferred_unit': items[0]['unit'] = 'm'
        if scenario == 'mixed_room': items[0] = {'kind':'room_no','raw_text':'110','unit':'unknown','bbox':None}
        if scenario == 'blank_false_positive': items = items[:1]
        return VisionOutput.model_validate({'items':items}), {'model':'substitute-only'}
    monkeypatch.setattr(assist, 'read_crop', substitute)
    request = {**body(cropped.headers['X-Crop-SHA256']), 'region':region}
    run = client.post(f'/drawing-files/{file_id}/pages/0/assist/vision', json=request).json()
    assert client.get(f'/drawing-files/{file_id}/measurements').json() == before
    assert run['status'] == ('FAILED' if scenario in {'no_output','malformed','provider_failure'} else 'NEEDS_REVIEW')
    assert 'private provider body' not in json.dumps(run)
    assert all(c['suggested_value'] is None and not c['unit_confirmed'] for c in run['dimensions'])
    assert run['consent']['external_crop_authorized'] is True
    assert run['consent']['preview_sha256'] == cropped.headers['X-Crop-SHA256']
    if run['evidence']:
        assert run['evidence'][0]['vision_crop']['sha256'] == cropped.headers['X-Crop-SHA256']
        assert run['evidence'][0]['status'] == 'NEEDS_REVIEW'
    payload = {'run_id':run['run_id'], 'measurement_id':row['id'], 'deductions_reviewed':True,
               'inputs': {field:{'candidate_id':run['dimensions'][0]['candidate_id'] if run['dimensions'] else 'forged',
                                'unit':'mm', 'unit_confirmed':False,
                                'sheet_id':run['evidence'][0]['sheet_id'] if run['evidence'] else 1,
                                'note':'Unreviewed test candidate'} for field in ('width','height')}}
    assert client.post(f'/drawing-files/{file_id}/assist/drafts', json=payload).status_code == 422
    for field in payload['inputs'].values():
        field['unit_confirmed'] = True
        field['note'] = ' '
    assert client.post(f'/drawing-files/{file_id}/assist/drafts', json=payload).status_code == 400
    payload['status'] = 'CONFIRMED'
    payload['quantity'] = '99'
    assert client.post(f'/drawing-files/{file_id}/assist/drafts', json=payload).status_code == 422
    assert client.get(f'/drawing-files/{file_id}/measurements').json() == before
