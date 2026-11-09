"""Synthetic observations and times only; no field data or model calls."""
from copy import deepcopy
import pytest
from app.services.pilot_evaluation import analyze_trials
from test_known_takeoff_workflow import workflow, prepare
from test_evaluation_trials import manual


def pilot(**changes):
    return dict(schema_version=1, synthetic=True, comparison_set='synthetic-set', participant='synthetic-P',
        observer='synthetic-O', observed_at='2026-11-09T10:00:00+09:00', category='ceiling',
        task_definition='Synthetic ceiling, no deduction, verify Excel', conditions='synthetic PC/revision/model/settings',
        preparation='included', preparation_seconds=5, cache='cold', sequence=['manual','local','ai'],
        position=1, practice=False, learning_effect='Synthetic: practice separated', outcome='completed',
        observation_complete=True, timing_scope_confirmed=True, wrong_evidence_count=0,
        intervention_details='none (synthetic)', error_details='none (synthetic)', reviewer='synthetic-R',
        review_evidence='Synthetic formula/unit/source/Excel reviewed', adoption_reason='synthetic accepted', **changes)


def records():
    result=[]
    for i, mode in enumerate(['manual','local','ai']):
        p=pilot();p['position']=i+1
        result.append(dict(trial_id=i+1,task_key='Synthetic task',mode=mode,elapsed_seconds=120-i*20,
            drawing_fingerprint='a'*64, review_result='adopted',pilot=p))
    return result


def test_empty_and_common_completed_group_with_explicit_order():
    assert analyze_trials([])['status']=='NOT_RUN'
    rows=records(); rows.reverse()  # storage order must not be execution order
    report=analyze_trials(rows)
    assert report['excluded_count']==0
    assert report['common_completed_task_count']==1
    paired=report['comparisons'][0]
    assert paired['manual_minus_assisted_seconds']=={'ai':40,'local':20}
    assert paired['conditions']['synthetic'] is True
    assert paired['conditions']['sequence']==['manual','local','ai']


@pytest.mark.parametrize('change,reason',[
    ({'observation_complete':False},'incomplete_observation'),
    ({'timing_scope_confirmed':False},'incomplete_timing_scope'),
    ({'practice':True},'practice'),({'conditions':'different revision'},'conditions_or_task_mismatch'),
    ({'task_definition':'different task'},'conditions_or_task_mismatch'),
    ({'category':'floor'},'conditions_or_task_mismatch'),
    ({'cache':'warm'},'conditions_or_task_mismatch'),
    ({'preparation':'excluded'},'conditions_or_task_mismatch'),
    ({'position':1},'sequence_mode_mismatch'),
])
def test_ineligible_or_mismatched_group_has_ids_and_reasons(change,reason):
    rows=records();rows[1]['pilot'].update(change)
    report=analyze_trials(rows)
    assert report['common_completed_task_count']==0
    assert report['excluded_count']==3
    assert reason in next(r['reasons'] for r in report['excluded'] if r['trial_id']==2)


def test_failures_rejections_retries_and_legacy_are_never_fastest_attempt_selection():
    rows=records()
    retry=deepcopy(rows[2]);retry['trial_id']=4
    rows[2]['pilot']['outcome']='failed';rows[2]['elapsed_seconds']=1;rows[2]['review_result']='rejected'
    rows.append(retry)
    rows.append(dict(trial_id=5,mode='manual',review_result='needs_review'))
    report=analyze_trials(rows)
    assert report['common_completed_task_count']==0
    assert report['excluded_count']==5
    ai=next(r for r in report['mode_summaries'] if r['mode']=='ai')
    assert (ai['failure_rate'],ai['failure_rate_denominator'],ai['rejected_count'])==(.5,2,1)
    assert ai['failed_or_aborted_record_ids']==[3]
    assert {r['trial_id'] for r in report['attempt_outcomes']}=={1,2,3,4,5}


def test_file_versions_missing_modes_unreviewed_and_source_strata():
    for mutate in [lambda r:r[1].update(drawing_fingerprint='b'*64),
                   lambda r:r[1].update(review_result='needs_review'),
                   lambda r:r[1].update(review_result='rejected'),
                   lambda r:r.pop()]:
        rows=records();mutate(rows)
        assert analyze_trials(rows)['common_completed_task_count']==0
    rows=records();real=deepcopy(rows[0]);real['trial_id']=4;real['pilot']['synthetic']=False;rows.append(real)
    report=analyze_trials(rows)
    assert report['common_completed_task_count']==1
    assert {s['source'] for s in report['mode_summaries']}=={'synthetic','real'}


def test_api_optional_metadata_export_all_and_failed_before_provider_run(workflow):
    client=workflow;_,file_id,_=prepare(client)
    path=f'/drawing-files/{file_id}/assist/trials'
    assert client.get(path+'/analysis').json()['status']=='NOT_RUN'
    assert client.post(path,json=manual()).status_code==201
    p=pilot();p.update(position=3,outcome='failed')
    response=client.post(path,json={**manual(),'mode':'ai','pilot':p})
    assert response.status_code==201,response.text
    assert response.json()['pilot']['synthetic'] is True
    bad=deepcopy(p);bad['sequence']=['manual','manual','ai']
    assert client.post(path,json={**manual(),'mode':'ai','pilot':bad}).status_code==422
    bad=deepcopy(p);bad['position']=1
    assert client.post(path,json={**manual(),'mode':'ai','pilot':bad}).status_code==422
    # No hidden 100-record truncation: every retry must reach export and analysis.
    for _ in range(100):
        assert client.post(path,json=manual()).status_code==201
    exported=client.get(path+'/export').json()
    assert len(exported['records'])==102
    assert exported['analysis']['record_count']==102
    assert exported['analysis']['excluded_count']==102
    assert 'pilot' not in exported['records'][-1]
    assert client.get('/drawing-files/999999/assist/trials/export').status_code==404
