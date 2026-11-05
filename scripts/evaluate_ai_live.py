"""Opt-in paid smoke evaluation using synthetic data only. Never prints secrets."""
from argparse import ArgumentParser
from decimal import Decimal
from io import BytesIO
import json
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from time import perf_counter


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('--env-file', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    from dotenv import dotenv_values
    credentials = dotenv_values(args.env_file, interpolate=False)
    for name in ('TAKEOFF_AI_API_KEY', 'TAKEOFF_AI_MODEL', 'TAKEOFF_AI_VISION_MODEL'):
        if credentials.get(name):
            os.environ[name] = credentials[name]
    if not os.environ.get('TAKEOFF_AI_API_KEY') or not os.environ.get('TAKEOFF_AI_MODEL'):
        print('AI key and model must be configured in the supplied environment file.')
        return 2
    del credentials
    vision_fallback = not bool(os.environ.get('TAKEOFF_AI_VISION_MODEL'))
    if vision_fallback:
        os.environ['TAKEOFF_AI_VISION_MODEL'] = os.environ['TAKEOFF_AI_MODEL']
    report = {'scope':'synthetic inputs only; live model and server contracts, not field accuracy',
        'model':os.environ['TAKEOFF_AI_MODEL'], 'vision_model':os.environ['TAKEOFF_AI_VISION_MODEL'],
        'vision_uses_search_model':vision_fallback, 'cases':[], 'calls':[]}
    started = perf_counter()
    try:
        with TemporaryDirectory(prefix='takeoff-live-eval-') as temp:
            directory = Path(temp)
            os.environ.update(TAKEOFF_DATABASE_URL='sqlite:///'+(directory/'startup.db').as_posix(),
                TAKEOFF_DATA_DIR=str(directory), TAKEOFF_UPLOADS_DIR=str(directory/'uploads'),
                TAKEOFF_RENDERED_PAGES_DIR=str(directory/'rendered'), TAKEOFF_EXPORTS_DIR=str(directory/'exports'))
            root = Path(__file__).resolve().parents[1]
            sys.path[:0] = [str(root/'apps/api'),str(root/'apps/api/tests')]
            import pytest
            from openpyxl import load_workbook
            from test_known_takeoff_workflow import workflow, prepare
            from test_assist_drafts import ceiling_payload
            from test_assist_vision import prepare_scan, preview, body, REGION
            patcher = pytest.MonkeyPatch()
            fixture = workflow.__wrapped__(directory,patcher)
            client = next(fixture)
            try:
                _, file_id, rows = prepare(client)

                def record(case, checks):
                    status = 'PASS' if all(checks.values()) else 'FAILED'
                    report['cases'].append({'case':case,'status':status,'checks':checks})
                    print(case+': '+status,flush=True)
                    assert status == 'PASS', case+' contract failed'

                def search(prompt):
                    start = perf_counter()
                    response = client.post(f'/drawing-files/{file_id}/assist/search',json={'request':prompt,'mode':'ai'})
                    assert response.status_code == 200, 'Search HTTP contract failed'
                    run = response.json()
                    report['calls'].append({'kind':'search','status':run['status'], 'elapsed_ms':round((perf_counter()-start)*1000),
                        'metadata':run.get('metadata',{})})
                    assert run['status'] == 'NEEDS_REVIEW', 'Live search did not return evidence'
                    return run

                run = search('110호 ACST 천장 면적 찾아줘')
                payload = ceiling_payload(rows,run)
                draft = client.post(f'/drawing-files/{file_id}/assist/drafts',json=payload)
                assert draft.status_code == 200,'Ceiling draft rejected'
                saved = draft.json()
                book = load_workbook(BytesIO(client.get(f'/drawing-files/{file_id}/measurements/export').content))
                values = list(book['Details'].values)
                row = next(dict(zip(values[0],r)) for r in values[1:] if r[1]=='110' and r[4]=='ACST')
                record('E-01',{'quantity':Decimal(saved['quantity'])==Decimal('11.34'),'draft':saved['status']=='DRAFT',
                    'excel':Decimal(str(row['Quantity']))==Decimal('11.34'),'sources':bool(row['Source Sheets'])})
                missing = {**payload,'inputs':{'width':payload['inputs']['width']}}
                record('E-03',{'missing_input_rejected':client.post(f'/drawing-files/{file_id}/assist/drafts',json=missing).status_code==400})
                record('E-04',{'multiple_sources':len(run['evidence'])>=2,'warning':any('여러 개' in w for w in run['warnings'])})
                uncertain = {**payload,'inputs':{**payload['inputs'],'width':{**payload['inputs']['width'],'unit_confirmed':False}}}
                record('E-05',{'unknown_unit_rejected':client.post(f'/drawing-files/{file_id}/assist/drafts',json=uncertain).status_code==422})

                run2 = search('119호 5A 파티션 산출해줘')
                detail = next(e for e in run2['evidence'] if e['page_index']==2)
                partition = next(r for r in rows if r['room_no']=='119' and r['measurement_type']=='PARTITION_AREA')
                partition_payload = {'run_id':run2['run_id'],'measurement_id':partition['id'],'finish_code':'5A',
                    'deductions_reviewed':True,'side_multiplier':1,
                    'inputs':{field:{'value':value,'unit':'m','unit_confirmed':True,'sheet_id':detail['sheet_id'],
                        'note':'Synthetic acceptance inputs; no deductions, one face'} for field,value in [('wall_length','4.2'),('wall_height','4.6')]}}
                response = client.post(f'/drawing-files/{file_id}/assist/drafts',json=partition_payload)
                assert response.status_code==200,'Partition draft rejected'
                record('E-02',{'quantity':Decimal(response.json()['quantity'])==Decimal('19.32'),'draft':response.json()['status']=='DRAFT'})

                assert client.patch(f"/measurements/{saved['id']}",json={'status':'CONFIRMED'}).status_code==200
                repeated = search('110호 ACST 천장 다시 찾아줘')
                payload['run_id'] = repeated['run_id']
                protected = client.post(f'/drawing-files/{file_id}/assist/drafts',json=payload)
                current = next(r for r in client.get(f'/drawing-files/{file_id}/measurements').json() if r['id']==saved['id'])
                record('E-06',{'protected':protected.status_code==409,'quantity_preserved':current['quantity']==saved['quantity'],'confirmed':current['status']=='CONFIRMED'})

                scan_id = prepare_scan(client)
                cropped = preview(client,scan_id)
                start = perf_counter()
                response = client.post(f'/drawing-files/{scan_id}/pages/0/assist/vision',json=body(cropped.headers['X-Crop-SHA256']))
                assert response.status_code==200,'Vision HTTP contract failed'
                vision = response.json()
                report['calls'].append({'kind':'vision','status':vision['status'],'elapsed_ms':round((perf_counter()-start)*1000),
                    'metadata':vision.get('metadata',{})})
                numeric = {c['raw_text'] for c in vision.get('dimensions',[])}
                record('V-01',{'evidence':vision['status']=='NEEDS_REVIEW','dimensions':{'4200','2700'}<=numeric,
                    'unconfirmed_units':all(c['unit_confirmed'] is False for c in vision.get('dimensions',[])),
                    'no_auto_quantity':all(r['quantity'] is None for r in client.get(f'/drawing-files/{scan_id}/measurements').json())})
                record('V-02',{'no_inferred_units':bool(vision.get('dimensions')) and
                    all(c['unit_guess']=='unknown' for c in vision['dimensions'])})

                blank_region = {**REGION,'y':300}
                cropped = client.post(f'/drawing-files/{scan_id}/pages/0/assist/vision-preview',json={'region':blank_region})
                assert cropped.status_code==200,'Blank crop preview failed'
                blank_payload = {**body(cropped.headers['X-Crop-SHA256']),'region':blank_region,
                    'note':'Synthetic blank crop: no visible dimensions, codes, or room numbers'}
                before = client.get(f'/drawing-files/{scan_id}/measurements').json()
                start = perf_counter()
                response = client.post(f'/drawing-files/{scan_id}/pages/0/assist/vision',json=blank_payload)
                assert response.status_code==200,'Blank vision HTTP contract failed'
                blank = response.json()
                report['calls'].append({'kind':'vision_blank','status':blank['status'],
                    'elapsed_ms':round((perf_counter()-start)*1000),'metadata':blank.get('metadata',{})})
                record('V-03',{'not_found':blank['status']=='NOT_FOUND',
                    'no_candidates':not blank.get('vision_candidates'),
                    'measurements_unchanged':before==client.get(f'/drawing-files/{scan_id}/measurements').json()})
            finally:
                fixture.close()
                patcher.undo()
                # Lifespan init_db also opens the module-level SQLite engine.
                # Windows keeps that file locked until its pool is disposed.
                from app.db.session import engine
                engine.dispose()
        report['status']='PASS'
    except Exception as exc:
        # Never serialize provider exception text, request objects, or environment.
        report['status']='FAILED'
        report['error_type']=type(exc).__name__
        print('Evaluation stopped: '+type(exc).__name__,flush=True)
    report['elapsed_seconds']=round(perf_counter()-started,2)
    report['total_tokens']=sum(c.get('metadata',{}).get('usage',{}).get('total_tokens',0) for c in report['calls'])
    args.report.parent.mkdir(parents=True,exist_ok=True)
    args.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':report['status'],'cases':len(report['cases']),'total_tokens':report['total_tokens']},ensure_ascii=False))
    return 0 if report['status']=='PASS' else 1


if __name__=='__main__':
    raise SystemExit(main())
