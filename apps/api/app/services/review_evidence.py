"""Read-only presentation of stored evidence, scoped to its owning drawing file."""
from app.services.assist_drafts import fingerprint
from app.services.assist_vision import CropRegion, crop_png, image_fingerprint
from decimal import Decimal, InvalidOperation


def _dict(value):
    return value if isinstance(value,dict) else {}


def _list(value):
    return value if isinstance(value,list) else []


def _display(value):
    return str(value) if isinstance(value,(str,int,float)) and not isinstance(value,bool) else None


def build_review_evidence(measurement, drawing_file, sheets):
    assist = _dict(_dict(measurement.coordinates_json).get('assist'))
    request = _dict(assist.get('inputs'))
    normalized = _dict(assist.get('normalized_inputs'))
    candidates = {c['candidate_id']:c for c in _list(assist.get('dimension_candidates')) if isinstance(c,dict) and isinstance(c.get('candidate_id'),str)}
    snapshots = {e['sheet_id']:e for e in _list(assist.get('evidence')) if isinstance(e,dict) and isinstance(e.get('sheet_id'),int)}
    by_id = {s.id:s for s in sheets}
    warnings = []
    inputs = []
    required_sources = set()
    for name, raw in _dict(request.get('inputs')).items():
        value = _dict(raw)
        candidate_key = value.get('candidate_id')
        candidate = candidates.get(candidate_key,{}) if isinstance(candidate_key,str) else {}
        source_id = value.get('sheet_id')
        if not isinstance(source_id,int) or source_id not in by_id:
            warnings.append('일부 입력의 출처를 현재 도면에서 찾을 수 없습니다.')
            source_id = None
        else:
            required_sources.add(source_id)
        inputs.append({'name':name,'raw_value':_display(candidate.get('raw_text',value.get('value'))),
            'unit':_display(value.get('unit')),'normalized_value':_display(normalized.get(name)),
            'normalized_unit':'EA' if name=='count' else 'm', 'source_sheet_id':source_id,
            'note':_display(value.get('note')),'method':_display(candidate.get('method','text')) if candidate else 'manual'})
    if not inputs:
        warnings.append('이 행에는 보조 기능의 입력별 기록이 없습니다. 저장된 계산식과 출처를 원본에서 확인하세요.')
    elif not normalized:
        warnings.append('이전 버전에서 저장한 행으로, 계산 당시의 단위 변환값 기록이 없습니다. 현재 수량을 다시 계산한 것으로 표시하지 않습니다.')
    original = _dict(assist.get('calculated_result'))
    if original:
        try:
            result_changed = (original.get('formula') != measurement.formula or original.get('unit') != measurement.unit
                or Decimal(str(original.get('quantity'))) != measurement.quantity)
        except (InvalidOperation,ValueError):
            result_changed = True
        if result_changed:
            warnings.append('입력 근거를 저장한 뒤 계산 결과가 수동 변경됐습니다. 아래 입력은 이전 계산의 기록입니다.')
    source_tokens = {t.strip() for t in (measurement.source_sheets or '').replace(';',',').split(',') if t.strip()}
    required_sources.update(s.id for s in sheets if s.sheet_no in source_tokens)
    sources = []
    for source_id in sorted(required_sources):
        sheet = by_id[source_id]
        snapshot = snapshots.get(source_id,{})
        stale = bool(snapshot.get('sheet_fingerprint') and snapshot['sheet_fingerprint'] != fingerprint(sheet))
        if snapshot.get('vision_crop'):
            try:
                crop = snapshot['vision_crop']
                stale = stale or image_fingerprint(crop_png(drawing_file,sheet,CropRegion.model_validate(crop['region']))) != crop['sha256']
            except (ValueError,KeyError,TypeError,OSError):
                stale = True
        sources.append({'sheet_id':sheet.id,'drawing_file_id':drawing_file.id,'page_index':sheet.page_index,
            'sheet_no':sheet.sheet_no,'sheet_title':sheet.sheet_title,'quote':_display(snapshot.get('quote')) or '',
            'method':_display(snapshot.get('method')) or 'manual','changed_since_saved':stale})
    if any(s['changed_since_saved'] for s in sources):
        warnings.append('저장 후 원본이 변경됐습니다. 표시된 이미지는 현재 원본이므로 근거를 다시 확인하세요.')
    deductions = _list(request.get('deductions'))
    if not deductions:
        deductions = [{'amount':_display(d.get('amount')),'unit':measurement.unit,'note':_display(d.get('label'))}
            for d in _list(_dict(measurement.deductions_json).get('items')) if isinstance(d,dict)]
    return {'measurement_id':measurement.id,'room_no':measurement.room_no,'finish_code':measurement.finish_code,
        'formula':measurement.formula,'quantity':str(measurement.quantity) if measurement.quantity is not None else None,
        'unit':measurement.unit,'status':measurement.status.value,'run_id':assist.get('run_id'),
        'inputs':inputs,'sources':sources,'side_multiplier':request.get('side_multiplier'),
        'deductions':deductions,'deductions_reviewed':request.get('deductions_reviewed'),
        'warnings':list(dict.fromkeys(warnings))}
