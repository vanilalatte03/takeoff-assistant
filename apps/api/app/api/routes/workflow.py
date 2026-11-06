from pathlib import Path
from threading import Lock

import fitz
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.routes.drawing_files import _extract_page_text, _render_page_png, _rendered_page_path
from app.api.routes.measurements import generate_measurement_candidates, list_measurements
from app.api.routes.room_finishes import extract_room_finishes, list_room_finishes
from app.db.session import get_db
from app.models import DrawingFile, DrawingSheet, DrawingSheetRole, ReviewStatus
from app.models.drawing_preparation import DrawingPreparation
from app.services import classify_and_apply_sheet_roles, detect_and_apply_sheet_metadata

router = APIRouter(tags=["workflow"])
STAGES = ["페이지 처리", "도면 감지", "도면 분류", "마감 후보 추출", "산출 후보 생성"]
# One local API process is the supported runtime. Striped locks bound memory and
# reject duplicate requests rather than letting two tabs create duplicate rows.
_locks = [Lock() for _ in range(64)]


def _file(db, file_id):
    drawing = db.get(DrawingFile, file_id)
    if drawing is None:
        raise HTTPException(404, "도면 PDF를 찾을 수 없습니다. 다시 선택하세요.")
    return drawing


def _sheets(db, file_id):
    return db.query(DrawingSheet).filter_by(drawing_file_id=file_id).order_by(DrawingSheet.page_index).all()


def _state(db, drawing):
    checkpoint = db.get(DrawingPreparation, drawing.id)
    completed = checkpoint.completed if checkpoint else 0
    warnings = list(checkpoint.warnings) if checkpoint else []
    finishes = list_room_finishes(drawing.id, room_no=None, room_name=None, finish_code=None, status_filter=None, db=db)
    measurements = list_measurements(drawing.id, room_no=None, category=None, code=None, measurement_type=None, status_filter=None, db=db)
    return {
        "completed": completed,
        "stages": STAGES,
        "warnings": warnings,
        "ready": completed == len(STAGES) and bool(finishes) and bool(measurements),
        "finish_count": len(finishes),
        "measurement_count": len(measurements),
    }


@router.get("/drawing-files/{file_id}/workflow")
def workflow_status(file_id: int, db: Session = Depends(get_db)):
    return _state(db, _file(db, file_id))


@router.post("/drawing-files/{file_id}/workflow/prepare")
def prepare_next_stage(file_id: int, db: Session = Depends(get_db)):
    drawing = _file(db, file_id)
    lock = _locks[file_id % len(_locks)]
    if not lock.acquire(blocking=False):
        raise HTTPException(409, "도면 준비가 이미 실행 중입니다. 잠시 후 상태를 다시 불러오세요.")
    try:
        checkpoint = db.get(DrawingPreparation, file_id)
        if checkpoint is None:
            checkpoint = DrawingPreparation(drawing_file_id=file_id, completed=0, owned_sheet_ids=[], warnings=[])
            db.add(checkpoint)
            if _sheets(db, file_id):
                # Legacy sheets may contain deliberate user corrections, including
                # UNKNOWN roles and blank metadata. Do not infer permission to reset.
                checkpoint.completed = 3
                checkpoint.warnings = ["기존 도면의 원문·번호·분류·검수 상태를 보존했습니다. 분류가 잘못되었으면 도면 목록에서 수정하세요."]
            db.commit()
        stage = checkpoint.completed
        if stage == 0:
            if not Path(drawing.stored_path).is_file():
                raise HTTPException(404, "저장된 PDF가 없습니다. 원본 파일 위치를 확인하거나 다시 업로드하세요.")
            created = []
            with fitz.open(drawing.stored_path) as document:
                for index in range(document.page_count):
                    page = document.load_page(index)
                    text, text_status = _extract_page_text(page)
                    if _render_page_png(page, _rendered_page_path(file_id, index)) is not None:
                        raise HTTPException(500, f"PDF {index + 1}쪽 이미지 처리 실패. 저장 공간을 확인하고 재시도하세요.")
                    sheet = DrawingSheet(drawing_file_id=file_id, page_index=index, text_content=text, status=text_status)
                    db.add(sheet)
                    created.append(sheet)
                drawing.page_count = document.page_count
            db.flush()
            checkpoint.owned_sheet_ids = [sheet.id for sheet in created]
            if any(not sheet.text_content.strip() for sheet in created):
                checkpoint.warnings = [*checkpoint.warnings, "텍스트가 없는 페이지가 있습니다. 원본을 열어 수동 측정·마감 입력이 필요할 수 있습니다."]
        elif stage in (1, 2):
            owned = [s for s in _sheets(db, file_id) if s.id in checkpoint.owned_sheet_ids
                     and s.status not in (ReviewStatus.CONFIRMED, ReviewStatus.REJECTED)]
            if stage == 1:
                # Never overwrite a manual metadata edit made between checkpoints.
                detect_and_apply_sheet_metadata([s for s in owned if s.sheet_no is None and s.sheet_title is None
                                                 and s.sheet_detection_confidence is None and s.role == DrawingSheetRole.UNKNOWN])
            else:
                classify_and_apply_sheet_roles([s for s in owned if s.role == DrawingSheetRole.UNKNOWN])
        elif stage == 3:
            result = extract_room_finishes(file_id, db=db)
            if result.warnings:
                checkpoint.warnings = [*checkpoint.warnings, "마감표 또는 마감 후보를 자동으로 찾지 못했습니다. 도면 분류를 확인하거나 마감 후보를 직접 입력하세요."]
        elif stage == 4:
            generate_measurement_candidates(file_id, db=db)
        if stage < len(STAGES):
            checkpoint.completed = stage + 1
            db.commit()
        return _state(db, drawing)
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(500, "도면 준비에 실패했습니다. 원본·저장 공간을 확인하고 실패 단계부터 재시도하세요.") from exc
    finally:
        lock.release()
