"""Local, user-reported pilot observations; never an accuracy benchmark."""
from collections import Counter, defaultdict
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator
from typing_extensions import Annotated

Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1000)]


class PilotObservation(BaseModel):
    model_config = ConfigDict(extra='forbid')
    schema_version: Literal[1]
    synthetic: bool
    comparison_set: Text
    participant: Text
    observer: Text
    observed_at: datetime
    category: Literal['floor', 'ceiling', 'partition', 'other']
    task_definition: Text
    conditions: Text  # device, app revision, task rules, settings and model/vision variant
    preparation: Literal['included', 'excluded']
    preparation_seconds: int = Field(ge=0, le=86400)
    cache: Literal['cold', 'warm']
    sequence: list[Literal['manual', 'local', 'ai', 'vision']] = Field(min_length=3, max_length=3)
    position: int = Field(ge=1, le=3)
    practice: bool
    learning_effect: Text
    outcome: Literal['completed', 'failed', 'aborted']
    observation_complete: bool
    timing_scope_confirmed: bool
    wrong_evidence_count: int = Field(ge=0, le=10000)
    intervention_details: Text
    error_details: Text
    reviewer: Text
    review_evidence: Text
    adoption_reason: Text

    @model_validator(mode='after')
    def valid_sequence(self):
        if set(self.sequence) not in ({'manual', 'local', 'ai'}, {'manual', 'local', 'vision'}):
            raise ValueError('sequence must contain manual, local and exactly one AI variant')
        if self.observed_at.tzinfo is None:
            raise ValueError('observed_at requires timezone')
        return self


def analyze_trials(records: list[dict]) -> dict:
    """No imputation, best-attempt selection, truncation, or cross-condition pooling."""
    excluded = {}
    groups = defaultdict(list)
    outcomes = Counter()
    for record in records:
        rid = record['trial_id']
        outcomes[f"{record.get('mode')}:{record.get('review_result')}"] += 1
        reasons = []
        try:
            pilot = PilotObservation.model_validate(record.get('pilot'))
        except (ValueError, TypeError):
            excluded[rid] = ['missing_or_invalid_pilot_observation']
            continue
        p = pilot.model_dump(mode='json')
        if p['practice']:
            reasons.append('practice')
        if not p['observation_complete']:
            reasons.append('incomplete_observation')
        if not p['timing_scope_confirmed']:
            reasons.append('incomplete_timing_scope')
        if p['outcome'] != 'completed':
            reasons.append(p['outcome'])
        if record.get('review_result') != 'adopted':
            reasons.append('not_reviewed_and_adopted')
        if p['sequence'][p['position'] - 1] != record.get('mode'):
            reasons.append('sequence_mode_mismatch')
        if not isinstance(record.get('elapsed_seconds'), int) or record['elapsed_seconds'] <= 0:
            reasons.append('invalid_elapsed_seconds')
        elif p['preparation'] == 'included' and p['preparation_seconds'] > record['elapsed_seconds']:
            reasons.append('included_preparation_exceeds_elapsed')
        if not record.get('drawing_fingerprint'):
            reasons.append('missing_fingerprint')
        if reasons:
            excluded[rid] = reasons
        # Include excluded attempts in the group: a failed/retried attempt must not disappear.
        key = (p['synthetic'], p['comparison_set'], p['participant'], record.get('task_key'))
        groups[key].append((record, p))
    comparisons = []
    for group in groups.values():
        reasons = []
        first, p = group[0]
        ids = [r['trial_id'] for r, _ in group]
        expected = set(p['sequence'])
        if len(group) != 3 or {r.get('mode') for r, _ in group} != expected:
            reasons.append('missing_or_duplicate_mode')
        fields = ['category', 'task_definition', 'conditions', 'preparation', 'cache', 'sequence']
        if any(any(other[f] != p[f] for f in fields) for _, other in group):
            reasons.append('conditions_or_task_mismatch')
        if len({r.get('drawing_fingerprint') for r, _ in group}) != 1:
            reasons.append('file_version_mismatch')
        if any(rid in excluded for rid in ids):
            reasons.append('ineligible_attempt_in_group')
        if reasons:
            for rid in ids:
                excluded.setdefault(rid, []).extend(reasons)
            continue
        by_mode = {r['mode']: r for r, _ in group}
        task_seconds = {r['mode']: r['elapsed_seconds'] - (observation['preparation_seconds']
            if observation['preparation'] == 'included' else 0) for r, observation in group}
        total_seconds = {r['mode']: r['elapsed_seconds'] + (observation['preparation_seconds']
            if observation['preparation'] == 'excluded' else 0) for r, observation in group}
        comparisons.append({
            'record_ids': ids, 'task_key': first['task_key'], 'drawing_fingerprint': first['drawing_fingerprint'],
            'conditions': {k: p[k] for k in ['synthetic', 'comparison_set', 'participant', *fields]},
            'recorded_elapsed_seconds': {mode: r['elapsed_seconds'] for mode, r in by_mode.items()},
            'task_seconds_excluding_preparation': task_seconds,
            'total_seconds_including_preparation': total_seconds,
            'observed_counts': {r['mode']: {**{key: r.get(key) for key in
                ['correction_count', 'manual_interventions', 'error_count']},
                'wrong_evidence_count': observation['wrong_evidence_count'],
                'preparation_seconds': observation['preparation_seconds']} for r, observation in group},
            'manual_minus_assisted_task_seconds': {mode: task_seconds['manual'] - seconds
                for mode, seconds in task_seconds.items() if mode != 'manual'},
            'manual_minus_assisted_total_seconds': {mode: total_seconds['manual'] - seconds
                for mode, seconds in total_seconds.items() if mode != 'manual'},
        })
    mode_summaries = []
    strata = defaultdict(list)
    for r in records:
        try:
            observed = PilotObservation.model_validate(r.get('pilot'))
        except (ValueError, TypeError):
            observed = None
        strata[(r.get('mode', 'unknown'), 'unknown' if observed is None else ('synthetic' if observed.synthetic else 'real'))].append((r, observed))
    for (mode, source), rows in sorted(strata.items()):
        observed = [(r, p) for r, p in rows if p is not None]
        failures = [r['trial_id'] for r, p in observed if p.outcome in ('failed', 'aborted')]
        mode_summaries.append({'mode': mode, 'source': source, 'record_count': len(rows),
            'valid_observation_count': len(observed), 'missing_or_invalid_count': len(rows) - len(observed),
            'failed_or_aborted_count': len(failures), 'failed_or_aborted_record_ids': failures,
            'failure_rate_denominator': len(observed),
            'failure_rate': len(failures) / len(observed) if observed else None,
            'adopted_count': sum(r.get('review_result') == 'adopted' for r, _ in rows),
            'rejected_count': sum(r.get('review_result') == 'rejected' for r, _ in rows),
            'needs_review_count': sum(r.get('review_result') == 'needs_review' for r, _ in rows)})
    return {
        'schema_version': 1, 'verification': 'user_reported',
        'status': 'NOT_RUN' if not records else 'OBSERVATIONS_ONLY',
        'mode_summaries': mode_summaries,
        'record_count': len(records), 'record_ids': [r['trial_id'] for r in records],
        'outcomes': [{'label': key, 'count': value, 'record_ids': [r['trial_id'] for r in records if f"{r.get('mode')}:{r.get('review_result')}" == key]} for key, value in sorted(outcomes.items())],
        'attempt_outcomes': [{'trial_id': r['trial_id'], 'outcome': (r['pilot'].get('outcome', 'unknown') if isinstance(r.get('pilot'), dict) else 'unknown'), 'review_result': r.get('review_result')} for r in records],
        'excluded_count': len(excluded), 'excluded': [{'trial_id': rid, 'reasons': sorted(set(reasons))} for rid, reasons in sorted(excluded.items())],
        'common_completed_task_count': len(comparisons), 'comparisons': comparisons,
        'limitations': 'Descriptive paired times for common completed, reviewed/adopted tasks only. Failures and rejected attempts remain listed. No significance, causality, guaranteed time saving or program-verified accuracy. Synthetic and real observations are separate.',
    }
