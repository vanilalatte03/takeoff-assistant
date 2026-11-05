"""Evidence-bound calculation tools; automatic proposals never confirm a row."""
from decimal import Decimal
from copy import deepcopy
import hashlib
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.models import CalculationType, DrawingSheet, Measurement, MeasurementType, ReviewStatus
from app.services.calculation_engine import CalculationInput, DeductionInput, calculate
from app.services.dimension_assist import extract_dimension_candidates


def fingerprint(sheet: DrawingSheet) -> str:
    return hashlib.sha256((sheet.text_content or '').encode()).hexdigest()


def dimension_evidence(drawing_file, sheets):
    result = []
    warnings = []
    for sheet in sheets:
        candidates, messages = extract_dimension_candidates(drawing_file, sheet, None)
        warnings.extend(messages)
        for index, candidate in enumerate(candidates[:80]):
            # Existing extractor guesses units by magnitude. Keep the guess visibly
            # separate and require explicit user verification before calculation.
            result.append({
                'candidate_id': f'{sheet.id}:{index}', 'sheet_id': sheet.id,
                'page_index': sheet.page_index, 'source_sheet': sheet.sheet_no,
                'raw_text': candidate.raw_text, 'bbox': candidate.bbox,
                'suggested_value': str(candidate.normalized_value) if candidate.normalized_value is not None else None,
                'unit_guess': candidate.unit_guess, 'unit_confirmed': False,
                'status': 'NEEDS_REVIEW', 'sheet_fingerprint': fingerprint(sheet),
            })
    labels = {
        'No region was provided, so sheet-level text candidates were used.': '치수 후보는 페이지 전체에서 찾았습니다. 해당 실의 적용 구간인지 원본에서 확인하세요.',
        'No dimension-like text candidates found. Enter values manually.': '치수 텍스트 후보가 없습니다. 원본을 확인하거나 수동 측정값을 입력하세요.',
        'Stored PDF file was not found; falling back to sheet text.': '원본 PDF가 없어 저장된 페이지 텍스트에서 치수 후보를 찾았습니다.',
        'Requested page index is outside the stored PDF.': '원본 PDF에 해당 페이지가 없습니다.',
        'Could not read PDF text blocks; falling back to sheet text.': 'PDF 텍스트 블록을 읽지 못해 저장된 페이지 텍스트에서 후보를 찾았습니다.',
        'Sheet text is empty.': '페이지 텍스트가 비어 있습니다.',
    }
    return result[:240], list(dict.fromkeys(labels.get(w, w) for w in warnings))


class InputEvidence(BaseModel):
    model_config = ConfigDict(extra='forbid')
    candidate_id: str | None = Field(default=None, max_length=80)
    value: Decimal | None = Field(default=None, ge=0, le=100000, allow_inf_nan=False)
    unit: Literal['m', 'mm', 'EA', 'ft-in']
    unit_confirmed: Literal[True]
    sheet_id: int = Field(gt=0)
    note: str = Field(min_length=1, max_length=500)


class DraftDeduction(BaseModel):
    model_config = ConfigDict(extra='forbid')
    amount: Decimal = Field(gt=0, le=1000000000, allow_inf_nan=False)
    unit: Literal['m2', 'm', 'EA']
    sheet_id: int = Field(gt=0)
    note: str = Field(min_length=1, max_length=500)


class DraftRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    run_id: int = Field(gt=0)
    measurement_id: int = Field(gt=0)
    finish_code: str | None = Field(default=None, min_length=1, max_length=128)
    inputs: dict[str, InputEvidence] = Field(max_length=5)
    side_multiplier: int | None = Field(default=None, ge=1, le=10)
    deductions_reviewed: Literal[True]
    deductions: list[DraftDeduction] = Field(default_factory=list, max_length=50)


RULES = {
    MeasurementType.FLOOR_AREA: (CalculationType.AREA_RECTANGLE, ('width', 'height'), 'm2'),
    MeasurementType.CEILING_AREA: (CalculationType.AREA_RECTANGLE, ('width', 'height'), 'm2'),
    MeasurementType.PERIMETER_LENGTH: (CalculationType.PERIMETER_RECTANGLE, ('width', 'height'), 'm'),
    MeasurementType.WALL_AREA: (CalculationType.WALL_AREA, ('wall_length', 'wall_height'), 'm2'),
    MeasurementType.PARTITION_AREA: (CalculationType.PARTITION_AREA, ('wall_length', 'wall_height'), 'm2'),
    MeasurementType.COUNT: (CalculationType.COUNT, ('count',), 'EA'),
}


def calculate_quantity(db: Session, drawing_file, run, measurement: Measurement, payload: DraftRequest):
    if measurement.project_id != drawing_file.project_id or measurement.room_finish is None:
        raise ValueError('선택한 도면의 산출 행이 아닙니다.')
    if measurement.room_finish.drawing_sheet is None or measurement.room_finish.drawing_sheet.drawing_file_id != drawing_file.id:
        raise ValueError('산출 행의 도면 소속을 확인할 수 없습니다.')
    if measurement.status in {ReviewStatus.CONFIRMED, ReviewStatus.REJECTED}:
        raise ValueError('확정·제외 행은 확정 행은 DRAFT로 변경한 뒤 재검토하세요. 제외 행은 수정할 수 없습니다.')
    if run.status != 'NEEDS_REVIEW' or run.drawing_file_id != drawing_file.id:
        raise ValueError('이 도면의 유효한 탐색 실행이 필요합니다.')
    result = run.result
    if measurement.room_finish.status == ReviewStatus.REJECTED:
        raise ValueError('제외된 마감 행은 사용할 수 없습니다.')
    args = next((t['arguments'] for t in result.get('trace', []) if t['tool'] == 'search_sheets'), {})
    if args.get('room_no') and measurement.room_no != args['room_no']:
        raise ValueError('탐색한 실 번호와 선택한 산출 행이 다릅니다.')
    finish_code = (payload.finish_code or measurement.finish_code).strip()
    if not finish_code:
        raise ValueError('마감 코드를 확인하세요.')
    query_code = (args.get('finish_code') or '').casefold()
    if query_code and not (finish_code.casefold() == query_code or finish_code.casefold().startswith(query_code + '-')):
        raise ValueError('마감 코드를 먼저 원본과 대조해 수정하세요.')
    calculation_type, required, unit = RULES[measurement.measurement_type]
    if set(payload.inputs) != set(required):
        raise ValueError('필수 입력을 확인하세요: ' + ', '.join(required))
    if measurement.measurement_type == MeasurementType.PARTITION_AREA:
        if payload.side_multiplier is None:
            raise ValueError('파티션의 산출 면 수를 명시적으로 확인하세요.')
    elif payload.side_multiplier is not None:
        raise ValueError('산출 면 수는 파티션에만 적용할 수 있습니다.')

    evidence_by_id = {item['sheet_id']: item for item in result.get('evidence', [])}
    sheets = {}
    for sheet_id, item in evidence_by_id.items():
        sheet = db.get(DrawingSheet, sheet_id)
        if sheet is None or sheet.drawing_file_id != drawing_file.id or item.get('sheet_fingerprint') != fingerprint(sheet):
            raise ValueError('도면 내용이 변경됐습니다. 근거를 다시 검색하세요.')
        if item.get('vision_crop'):
            from app.services.assist_vision import CropRegion, crop_png, image_fingerprint
            crop = item['vision_crop']
            if image_fingerprint(crop_png(drawing_file, sheet, CropRegion.model_validate(crop['region']))) != crop['sha256']:
                raise ValueError('원본 이미지가 변경됐습니다. 선택 영역을 다시 판독하세요.')
        sheets[sheet_id] = sheet
    vision_code = any(c.get('kind') == 'finish_code' and c.get('raw_text','').casefold() == finish_code.casefold() for c in result.get('vision_candidates', []))
    if payload.finish_code and not vision_code and not any(re.search(r'(?<![A-Za-z0-9])' + re.escape(finish_code) + r'(?![A-Za-z0-9])', sheet.text_content or '', re.I) for sheet in sheets.values()):
        raise ValueError('확인한 마감 코드의 도면 근거가 없습니다.')

    candidates = {c['candidate_id']: c for c in result.get('dimensions', [])}
    values = {}
    sources = set()
    if payload.finish_code:
        code_source = next((s.id for s in sheets.values() if re.search(r'(?<![A-Za-z0-9])' + re.escape(finish_code) + r'(?![A-Za-z0-9])', s.text_content or '', re.I)), None)
        if code_source is not None:
            sources.add(code_source)
        elif vision_code:
            sources.update(e['sheet_id'] for e in result['evidence'] if e.get('method') == 'vision')
    for name, evidence in payload.inputs.items():
        if evidence.sheet_id not in sheets or not evidence.note.strip():
            raise ValueError('입력값의 도면 출처와 확인 메모가 필요합니다.')
        if name == 'count' and evidence.unit != 'EA' or name != 'count' and evidence.unit == 'EA':
            raise ValueError('계산 유형에 맞는 단위를 확인하세요.')
        value = evidence.value
        if evidence.candidate_id:
            if value is not None:
                raise ValueError('치수 후보와 수동값을 동시에 지정할 수 없습니다.')
            candidate = candidates.get(evidence.candidate_id)
            if candidate is None or candidate['sheet_id'] != evidence.sheet_id:
                raise ValueError('유효한 치수 후보를 선택하세요.')
            raw = candidate['raw_text']
            if evidence.unit == 'ft-in':
                match = re.fullmatch(r'(\d+(?:\.\d+)?)\s*\'\s*-?\s*(\d+(?:\.\d+)?)?\s*"?', raw)
                if not match:
                    raise ValueError('피트·인치 원문을 확인하세요.')
                value = Decimal(match[1])*Decimal('.3048') + Decimal(match[2] or '0')*Decimal('.0254')
            else:
                match = re.fullmatch(r'(\d+(?:\.\d+)?)\s*(mm|m)?', raw)
                if not match:
                    raise ValueError('치수 원문을 확인하세요.')
                if match[2] and match[2] != evidence.unit:
                    raise ValueError('원문에 표시된 단위와 확인 단위가 다릅니다.')
                value = Decimal(match[1])
        elif evidence.unit == 'ft-in':
            raise ValueError('수동 입력은 m 또는 mm로 입력하세요.')
        if value is None or not value.is_finite() or value < 0 or (name != 'count' and value == 0):
            raise ValueError('치수가 누락됐습니다. 원본 확인 또는 수동 측정이 필요합니다.')
        if evidence.unit == 'mm':
            value /= Decimal('1000')
        if name == 'count' and value != value.to_integral_value():
            raise ValueError('개수는 정수여야 합니다.')
        if value > Decimal('100000'):
            raise ValueError('치수가 허용 범위를 벗어났습니다.')
        values[name] = value
        sources.add(evidence.sheet_id)

    deductions = []
    for deduction in payload.deductions:
        if deduction.unit != unit or deduction.sheet_id not in sheets or not deduction.note.strip():
            raise ValueError('공제 단위·도면 출처·검수 메모를 확인하세요.')
        sources.add(deduction.sheet_id)
        deductions.append(DeductionInput(amount=deduction.amount, label=deduction.note))
    if calculation_type == CalculationType.COUNT and deductions:
        raise ValueError('개수 계산은 공제 후 최종 개수를 입력하세요.')
    # Include the finish schedule in addition to the dimensions' source sheets.
    sources.add(measurement.room_finish.drawing_sheet_id)
    source_sheets = ', '.join(dict.fromkeys(db.get(DrawingSheet, key).sheet_no or f'PDF page {db.get(DrawingSheet, key).page_index + 1}' for key in sorted(sources)))
    calculation = calculate(CalculationInput(calculation_type=calculation_type, **values,
        side_multiplier=Decimal(payload.side_multiplier) if payload.side_multiplier else None,
        source_sheets=source_sheets, deductions=tuple(deductions)))
    if calculation.quantity < 0 or calculation.quantity > Decimal('9999999999.99'):
        raise ValueError('공제 후 수량 또는 저장 가능한 수량 범위를 확인하세요.')
    return calculation, values


def create_measurement_draft(measurement, run, payload, calculation, normalized_inputs):
    coordinates = deepcopy(measurement.coordinates_json or {})
    provenance = coordinates.pop('merge_provenance', None)
    if provenance is not None:
        history = coordinates.get('history', [])
        history = history if isinstance(history, list) else [{'legacy_history':history}]
        coordinates['history'] = [*history, {'merge_provenance':provenance}]
    # Keep the existing calculation form's re-entry contract current as well.
    coordinates['calculation_inputs'] = {
        'calculation_type': RULES[measurement.measurement_type][0].value,
        **{name:str(value) for name,value in normalized_inputs.items()},
        'side_multiplier': str(payload.side_multiplier) if payload.side_multiplier is not None else None,
        'source_sheets': calculation.source_sheets,
        'deductions': [{'amount':str(d.amount),'label':d.note} for d in payload.deductions],
    }
    return dict(formula=calculation.formula, quantity=calculation.quantity,
        finish_code=(payload.finish_code or measurement.finish_code).strip(),
        unit=calculation.unit, source_sheets=calculation.source_sheets,
        deductions_json=calculation.deductions_json, status=ReviewStatus.DRAFT,
        coordinates_json={**coordinates, 'assist': {
        'run_id': run.id, 'inputs': payload.model_dump(mode='json'),
        'normalized_inputs': {name:str(value) for name,value in normalized_inputs.items()},
        'calculated_result': {'formula':calculation.formula,'quantity':str(calculation.quantity),'unit':calculation.unit},
        'dimension_candidates': run.result.get('dimensions', []),
        'evidence': run.result.get('evidence', []),
    }})
