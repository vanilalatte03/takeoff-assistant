from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import DrawingFile, DrawingSheet, DrawingSheetRole, Project, ReviewStatus, RoomFinish
from app.schemas import RoomFinishCreate, RoomFinishExtractionResult, RoomFinishRead, RoomFinishUpdate
from app.services import extract_room_finish_candidates


router = APIRouter(tags=["room-finishes"])


@router.post(
    "/drawing-files/{drawing_file_id}/room-finishes/extract",
    response_model=RoomFinishExtractionResult,
)
def extract_room_finishes(
    drawing_file_id: int,
    db: Session = Depends(get_db),
) -> RoomFinishExtractionResult:
    drawing_file = db.get(DrawingFile, drawing_file_id)
    if drawing_file is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Drawing file not found.",
        )

    finish_sheets = (
        db.query(DrawingSheet)
        .filter(
            DrawingSheet.drawing_file_id == drawing_file_id,
            DrawingSheet.role == DrawingSheetRole.FINISH_SCHEDULE,
        )
        .order_by(DrawingSheet.page_index)
        .all()
    )

    created_room_finishes: list[RoomFinish] = []
    for sheet in finish_sheets:
        for candidate in extract_room_finish_candidates(sheet):
            if _room_finish_exists(db, sheet.id, candidate.room_no):
                continue
            room_finish = RoomFinish(
                project_id=drawing_file.project_id,
                drawing_sheet_id=sheet.id,
                room_no=candidate.room_no,
                room_name=candidate.room_name,
                floor_finish=candidate.floor_finish,
                base_finish=candidate.base_finish,
                wall_finish=candidate.wall_finish,
                ceiling_finish=candidate.ceiling_finish,
                height=candidate.height,
                remarks=candidate.remarks,
                source_sheet_no=sheet.sheet_no,
                confidence=candidate.confidence,
                status=ReviewStatus.NEEDS_REVIEW,
            )
            db.add(room_finish)
            created_room_finishes.append(room_finish)

    db.commit()
    for room_finish in created_room_finishes:
        db.refresh(room_finish)

    return RoomFinishExtractionResult(
        drawing_file_id=drawing_file.id,
        room_finishes=created_room_finishes,
    )


@router.get(
    "/drawing-files/{drawing_file_id}/room-finishes",
    response_model=list[RoomFinishRead],
)
def list_room_finishes(
    drawing_file_id: int,
    db: Session = Depends(get_db),
) -> list[RoomFinish]:
    drawing_file = db.get(DrawingFile, drawing_file_id)
    if drawing_file is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Drawing file not found.",
        )

    return (
        db.query(RoomFinish)
        .join(DrawingSheet, RoomFinish.drawing_sheet_id == DrawingSheet.id, isouter=True)
        .filter(
            RoomFinish.project_id == drawing_file.project_id,
            (RoomFinish.drawing_sheet_id.is_(None)) | (DrawingSheet.drawing_file_id == drawing_file_id),
        )
        .order_by(RoomFinish.id)
        .all()
    )


@router.post("/room-finishes", response_model=RoomFinishRead, status_code=status.HTTP_201_CREATED)
def create_room_finish(
    payload: RoomFinishCreate,
    db: Session = Depends(get_db),
) -> RoomFinish:
    _validate_room_finish_references(db, payload.project_id, payload.drawing_sheet_id)
    room_finish = RoomFinish(**payload.model_dump(exclude={"status"}), status=ReviewStatus.NEEDS_REVIEW)
    db.add(room_finish)
    db.commit()
    db.refresh(room_finish)
    return room_finish


@router.patch("/room-finishes/{room_finish_id}", response_model=RoomFinishRead)
def update_room_finish(
    room_finish_id: int,
    payload: RoomFinishUpdate,
    db: Session = Depends(get_db),
) -> RoomFinish:
    room_finish = db.get(RoomFinish, room_finish_id)
    if room_finish is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Room finish not found.",
        )

    update_data = payload.model_dump(exclude_unset=True)
    if "drawing_sheet_id" in update_data:
        _validate_room_finish_references(db, room_finish.project_id, update_data["drawing_sheet_id"])

    for field, value in update_data.items():
        setattr(room_finish, field, value)

    db.commit()
    db.refresh(room_finish)
    return room_finish


def _room_finish_exists(db: Session, drawing_sheet_id: int, room_no: str) -> bool:
    return (
        db.query(RoomFinish)
        .filter(
            RoomFinish.drawing_sheet_id == drawing_sheet_id,
            RoomFinish.room_no == room_no,
        )
        .first()
        is not None
    )


def _validate_room_finish_references(db: Session, project_id: int, drawing_sheet_id: int | None) -> None:
    if db.get(Project, project_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found.",
        )
    if drawing_sheet_id is not None and db.get(DrawingSheet, drawing_sheet_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Drawing sheet not found.",
        )
