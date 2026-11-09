from time import perf_counter
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from typing import Literal
from sqlalchemy.orm import Session
from sqlalchemy import update
from app.core.config import settings
from app.db.session import get_db
from app.models import AssistRun, DrawingFile, DrawingSheet, Measurement, RoomFinish, ReviewStatus, EvaluationTrial
from app.services.assist_search import local_search_arguments, model_search_arguments, search_sheets
from app.services.assist_drafts import DraftRequest, dimension_evidence, fingerprint, calculate_quantity, create_measurement_draft
from app.schemas import MeasurementRead
from fastapi.responses import Response
from app.services.assist_vision import CropRegion, VisionRequest, crop_png, image_fingerprint, read_crop
from datetime import datetime, timezone
import hashlib
from pathlib import Path
from app.services.provider_errors import provider_error_metadata
from app.services.pilot_evaluation import PilotObservation, analyze_trials

router = APIRouter(tags=["assist"])


class SearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request: str = Field(min_length=1, max_length=500)
    mode: Literal["local", "ai"] = "local"


class PreviewRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    region: CropRegion


class TrialRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    task_key: str = Field(min_length=1, max_length=100)
    mode: Literal['manual','local','ai','vision']
    run_id: int | None = Field(default=None, gt=0)
    elapsed_seconds: int = Field(ge=1, le=86400)
    correction_count: int = Field(ge=0, le=10000)
    manual_interventions: int = Field(ge=0, le=10000)
    error_count: int = Field(ge=0, le=10000)
    review_result: Literal['adopted','rejected','needs_review']
    notes: str = Field(min_length=1, max_length=2000)
    pilot: PilotObservation | None = None


@router.post('/drawing-files/{file_id}/assist/trials', status_code=201)
def record_trial(file_id: int, payload: TrialRequest, db: Session = Depends(get_db)):
    drawing_file = db.get(DrawingFile,file_id)
    if drawing_file is None:
        raise HTTPException(404,'Drawing file not found.')
    if not payload.task_key.strip() or not payload.notes.strip():
        raise HTTPException(422,'과제명과 검수 메모를 입력하세요.')
    if payload.pilot and payload.pilot.sequence[payload.pilot.position - 1] != payload.mode:
        raise HTTPException(422, '실행 순서와 현재 방식이 일치해야 합니다.')
    failed_without_run = payload.pilot and payload.pilot.outcome != 'completed' and payload.run_id is None
    if payload.mode != 'manual' and not failed_without_run:
        run = db.get(AssistRun,payload.run_id) if payload.run_id else None
        if run is None or run.drawing_file_id != file_id or run.mode != payload.mode:
            raise HTTPException(400,'선택한 도면과 방식에 맞는 실행 기록이 필요합니다.')
    elif payload.mode == 'manual' and payload.run_id is not None:
        raise HTTPException(400,'수동 기준선에는 AI 실행 ID를 연결하지 않습니다.')
    if not Path(drawing_file.stored_path).is_file():
        raise HTTPException(409,'비교 기준 도면 파일을 찾을 수 없습니다.')
    with open(drawing_file.stored_path,'rb') as source:
        drawing_hash = hashlib.file_digest(source,'sha256').hexdigest()
    trial = EvaluationTrial(drawing_file_id=file_id,data={**payload.model_dump(mode="json", exclude={"pilot"} if payload.pilot is None else set()), 'drawing_fingerprint':drawing_hash,
        'recorded_at':datetime.now(timezone.utc).isoformat(), 'verification':'user_reported'})
    db.add(trial);db.commit();db.refresh(trial)
    return {'trial_id':trial.id,**trial.data}


@router.get('/drawing-files/{file_id}/assist/trials')
def trials(file_id: int, db: Session = Depends(get_db)):
    if db.get(DrawingFile,file_id) is None:
        raise HTTPException(404,'Drawing file not found.')
    rows = db.query(EvaluationTrial).filter(EvaluationTrial.drawing_file_id == file_id).order_by(EvaluationTrial.id.desc()).all()
    return [{'trial_id':r.id,**r.data} for r in rows]


@router.get('/drawing-files/{file_id}/assist/trials/export')
def export_trials(file_id: int, db: Session = Depends(get_db)):
    records = trials(file_id, db)
    return {'schema_version': 1, 'drawing_file_id': file_id, 'verification': 'user_reported',
            'records': records, 'analysis': analyze_trials(records)}


@router.get('/drawing-files/{file_id}/assist/trials/analysis')
def trial_analysis(file_id: int, db: Session = Depends(get_db)):
    return analyze_trials(trials(file_id, db))


@router.get('/assist/config')
def config():
    return {"ai_available": bool(settings.ai_api_key.get_secret_value() and settings.ai_model),
        'vision_available': bool(settings.ai_api_key.get_secret_value() and settings.ai_vision_model)}


def vision_source(db, file_id, page_index):
    drawing_file = db.get(DrawingFile, file_id)
    sheet = db.query(DrawingSheet).filter(DrawingSheet.drawing_file_id == file_id, DrawingSheet.page_index == page_index).one_or_none()
    if drawing_file is None or sheet is None:
        raise HTTPException(404, '처리된 도면 페이지를 찾을 수 없습니다.')
    return drawing_file, sheet


@router.post('/drawing-files/{file_id}/pages/{page_index}/assist/vision-preview')
def vision_preview(file_id: int, page_index: int, payload: PreviewRequest, db: Session = Depends(get_db)):
    drawing_file, sheet = vision_source(db, file_id, page_index)
    try:
        png = crop_png(drawing_file, sheet, payload.region)
    except Exception as exc:
        raise HTTPException(400, '선택 영역을 읽지 못했습니다. PDF와 선택 범위를 확인하세요.') from exc
    return Response(png, media_type='image/png', headers={'Cache-Control':'no-store', 'X-Crop-SHA256':image_fingerprint(png)})


@router.post('/drawing-files/{file_id}/pages/{page_index}/assist/vision')
def vision(file_id: int, page_index: int, payload: VisionRequest, db: Session = Depends(get_db)):
    drawing_file, sheet = vision_source(db, file_id, page_index)
    if not payload.note.strip():
        raise HTTPException(422, '추출 실패 상황을 기록하세요.')
    started = perf_counter()
    result = {'evidence': [], 'dimensions': [], 'finishes': [], 'vision_candidates': [], 'warnings': [], 'trace': [], 'metadata': {}}
    try:
        png = crop_png(drawing_file, sheet, payload.region)
        crop_hash = image_fingerprint(png)
        if crop_hash != payload.preview_sha256:
            raise HTTPException(409, '선택 영역이 미리보기와 다릅니다. 다시 미리보기를 확인하세요.')
        output, result['metadata'] = read_crop(png)
        result['vision_candidates'] = [item.model_dump() for item in output.items]
        result['evidence'] = [{'sheet_id':sheet.id, 'sheet_no':sheet.sheet_no, 'sheet_title':sheet.sheet_title,
            'page_index':page_index, 'quote':'이미지 판독 후보입니다. 원본에서 확인해야 합니다.', 'method':'vision',
            'status':'NEEDS_REVIEW', 'sheet_fingerprint':fingerprint(sheet),
            'vision_crop':{'region':payload.region.model_dump(), 'sha256':crop_hash}}]
        for index, item in enumerate(output.items):
            if item.kind != 'dimension':
                continue
            bbox = None
            if item.bbox:
                bbox = {'x':payload.region.x + item.bbox.x*payload.region.width, 'y':payload.region.y + item.bbox.y*payload.region.height,
                    'width':item.bbox.width*payload.region.width, 'height':item.bbox.height*payload.region.height}
            result['dimensions'].append({'candidate_id':f'{sheet.id}:vision:{index}', 'sheet_id':sheet.id, 'page_index':page_index,
                'source_sheet':sheet.sheet_no, 'raw_text':item.raw_text, 'unit_guess':item.unit, 'unit_confirmed':False,
                'suggested_value':None, 'bbox':bbox, 'status':'NEEDS_REVIEW', 'method':'vision', 'sheet_fingerprint':fingerprint(sheet)})
        result['trace'] = [{'tool':'read_selected_region', 'arguments':{'page_index':page_index, 'region':payload.region.model_dump(),
            'failure_reason':payload.failure_reason}, 'result_count':len(output.items)}]
        status = 'NEEDS_REVIEW' if output.items else 'NOT_FOUND'
        result['warnings'] = ['모델 판독은 원문 인용과 다릅니다. 숫자·단위·코드를 원본 이미지와 대조하세요. 수량은 저장하지 않았습니다.']
        if not output.items:
            result['warnings'].append('판독 가능한 후보가 없습니다. 수동 입력 또는 측정을 사용하세요.')
    except HTTPException:
        raise
    except Exception as exc:
        status = 'FAILED'
        result['warnings'] = ['Vision 서버 설정이 필요합니다.' if str(exc) == 'VISION_NOT_CONFIGURED' else '선택 영역 판독에 실패했습니다. 원본을 확인하거나 수동 입력을 사용하세요.']
        result['metadata'] = provider_error_metadata(exc)
    result['elapsed_ms'] = round((perf_counter()-started)*1000)
    result['consent'] = {'external_crop_authorized':True, 'failure_reason':payload.failure_reason, 'note':payload.note,
        'preview_sha256':payload.preview_sha256, 'region':payload.region.model_dump()}
    run = AssistRun(drawing_file_id=file_id, request=payload.note, mode='vision', status=status, result=result)
    db.add(run); db.commit(); db.refresh(run)
    return {'run_id':run.id,'mode':'vision','status':status,**result}


@router.get('/drawing-files/{file_id}/assist/runs')
def history(file_id: int, db: Session = Depends(get_db)):
    if db.get(DrawingFile, file_id) is None:
        raise HTTPException(404, "Drawing file not found.")
    rows = db.query(AssistRun).filter(AssistRun.drawing_file_id == file_id).order_by(AssistRun.id.desc()).limit(20).all()
    return [{"run_id": r.id, "request": r.request, "mode": r.mode, "status": r.status, **r.result} for r in rows]


@router.post('/drawing-files/{file_id}/assist/search')
def search(file_id: int, payload: SearchRequest, db: Session = Depends(get_db)):
    if db.get(DrawingFile, file_id) is None:
        raise HTTPException(404, "Drawing file not found.")
    if not payload.request.strip():
        raise HTTPException(422, "검색 요청을 입력하세요.")
    started = perf_counter()
    result = {"evidence": [], "warnings": [], "trace": [], "metadata": {}}
    try:
        if payload.mode == 'ai':
            args, result['metadata'] = model_search_arguments(payload.request)
        else:
            args = local_search_arguments(payload.request)
        sheets = db.query(DrawingSheet).filter(DrawingSheet.drawing_file_id == file_id).order_by(DrawingSheet.page_index).all()
        result['evidence'] = search_sheets(sheets, args, payload.request)
        result['trace'] = [{"tool": "search_sheets", "arguments": args.model_dump(), "result_count": len(result['evidence'])}]
        by_id = {sheet.id: sheet for sheet in sheets}
        selected_sheets = [by_id[item['sheet_id']] for item in result['evidence']]
        for item in result['evidence']:
            item['sheet_fingerprint'] = fingerprint(by_id[item['sheet_id']])
        finishes = db.query(RoomFinish).filter(RoomFinish.drawing_sheet_id.in_([s.id for s in selected_sheets]), RoomFinish.status != ReviewStatus.REJECTED).all()
        result['finishes'] = [{'room_finish_id': f.id, 'room_no': f.room_no, 'ceiling_finish': f.ceiling_finish, 'wall_finish': f.wall_finish,
            'floor_finish': f.floor_finish, 'source_sheet_no': f.source_sheet_no, 'status': f.status.value}
            for f in finishes if not args.room_no or f.room_no == args.room_no]
        dimension_sheets = sorted(selected_sheets, key=lambda s: s.role not in {
            'FLOOR_PLAN', 'CEILING_PLAN', 'PARTITION_PLAN', 'PARTITION_DETAIL', 'ENLARGED_FLOOR_PLAN'})
        result['dimensions'], dimension_warnings = dimension_evidence(db.get(DrawingFile, file_id), dimension_sheets)
        result['trace'].extend([
            {'tool': 'get_room_finishes', 'arguments': {'room_no': args.room_no}, 'result_count': len(result['finishes'])},
            {'tool': 'find_dimension_candidates', 'arguments': {'sheet_ids': [s.id for s in selected_sheets]}, 'result_count': len(result['dimensions'])},
        ])
        status = 'NEEDS_REVIEW' if result['evidence'] else 'NOT_FOUND'
        result['warnings'] = ['검색 후보입니다. 마감·치수·공제 적용 여부를 원본에서 확인하세요. 수량은 생성하지 않았습니다.']
        if len(result['evidence']) > 1:
            result['warnings'].append('관련 시트가 여러 개입니다. 같은 실 번호라도 층·구역·도면 종류가 다를 수 있으므로 적용 출처를 선택하세요.')
        result['warnings'].extend(dimension_warnings)
        if not result['evidence']:
            result['warnings'].append('일치하는 텍스트 근거가 없습니다. 도면 또는 검색어를 확인하거나 수동 측정을 사용하세요.')
    except Exception as exc:
        status = 'FAILED'
        # Provider responses/exceptions can include sensitive input or credentials.
        result['warnings'] = ['AI 설정이 필요합니다. 로컬 검색은 계속 사용할 수 있습니다.' if str(exc) == 'AI_NOT_CONFIGURED' else '검색 실행에 실패했습니다. 설정·네트워크를 확인하거나 로컬 검색을 사용하세요.']
        result['metadata'] = provider_error_metadata(exc)
    result['elapsed_ms'] = round((perf_counter() - started) * 1000)
    run = AssistRun(drawing_file_id=file_id, request=payload.request, mode=payload.mode, status=status, result=result)
    db.add(run)
    db.commit()
    db.refresh(run)
    return {"run_id": run.id, "status": status, "mode": payload.mode, **result}


@router.post('/drawing-files/{file_id}/assist/drafts', response_model=MeasurementRead)
def draft(file_id: int, payload: DraftRequest, db: Session = Depends(get_db)):
    started = perf_counter()
    drawing_file = db.get(DrawingFile, file_id)
    run = db.get(AssistRun, payload.run_id)
    measurement = db.get(Measurement, payload.measurement_id)
    if drawing_file is None or run is None or measurement is None:
        raise HTTPException(404, '도면·탐색 실행·산출 행을 찾을 수 없습니다.')
    if measurement.status in {ReviewStatus.CONFIRMED, ReviewStatus.REJECTED}:
        raise HTTPException(409, '확정 행은 DRAFT로 변경한 뒤 재검토하세요. 제외 행은 수정할 수 없습니다.')
    try:
        calculation, normalized_inputs = calculate_quantity(db, drawing_file, run, measurement, payload)
        changes = create_measurement_draft(measurement, run, payload, calculation, normalized_inputs)
    except ValueError as exc:
        if run.drawing_file_id == file_id:
            run.result = {**run.result, 'validation_failures': [*run.result.get('validation_failures', [])[-19:],
                {'measurement_id': measurement.id, 'message': str(exc), 'elapsed_ms': round((perf_counter() - started) * 1000)}]}
            db.commit()
        raise HTTPException(400, str(exc)) from exc
    # A concurrent user confirmation must win over an assistant draft write.
    saved = db.execute(update(Measurement).where(Measurement.id == measurement.id,
        Measurement.status.in_([ReviewStatus.DRAFT, ReviewStatus.NEEDS_REVIEW])).values(**changes),
        execution_options={'synchronize_session': False})
    if saved.rowcount != 1:
        db.rollback()
        raise HTTPException(409, '행 상태가 변경됐습니다. 다시 불러와 검토하세요.')
    run.result = {**run.result, 'review': {'measurement_id': measurement.id, 'status': 'DRAFT',
        'inputs': payload.model_dump(mode='json'), 'elapsed_ms': round((perf_counter() - started) * 1000)}, 'trace': [*run.result.get('trace', [])[-58:],
        {'tool': 'calculate_quantity', 'arguments': payload.model_dump(mode='json'), 'result': {'formula': calculation.formula, 'quantity': str(calculation.quantity), 'unit': calculation.unit}},
        {'tool': 'create_measurement_draft', 'measurement_id': measurement.id, 'status': 'DRAFT'}]}
    db.commit()
    db.refresh(measurement)
    return measurement
