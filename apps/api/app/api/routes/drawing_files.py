from pathlib import Path
from shutil import copyfileobj
from uuid import uuid4

import fitz
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.models import DrawingFile, DrawingSheet, DrawingSheetRole, Measurement, Project, ReviewStatus, RoomFinish
from app.schemas import (
    DimensionCandidate,
    DimensionCandidateRequest,
    DimensionCandidateResponse,
    DrawingFilePageProcessResult,
    DrawingFileRead,
    DrawingFileSheetClassificationResult,
    DrawingFileSheetDetectionResult,
    DrawingSheetSearchResponse,
    DrawingSheetSearchResult,
    RoomPageCandidate,
    RoomPageCandidateResponse,
)
from app.services import (
    build_room_page_candidates,
    classify_and_apply_sheet_roles,
    detect_and_apply_sheet_metadata,
    dimension_region_from_mapping,
    extract_dimension_candidates,
    filter_sheets_by_keyword,
    filter_sheets_by_sheet_no,
)


router = APIRouter(prefix="/drawing-files", tags=["drawing-files"])


def _safe_pdf_filename(filename: str | None) -> str:
    original_name = Path(filename or "").name
    if not original_name or Path(original_name).suffix.lower() != ".pdf":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are supported.",
        )
    return original_name


def _count_pdf_pages(path: Path) -> int:
    try:
        with fitz.open(path) as document:
            return document.page_count
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is not a valid PDF.",
        ) from exc


def _rendered_page_path(drawing_file_id: int, page_index: int) -> Path:
    return settings.rendered_pages_dir / str(drawing_file_id) / f"page_{page_index}.png"


def _extract_page_text(page: fitz.Page) -> tuple[str, ReviewStatus]:
    try:
        text = page.get_text("text")
    except Exception:
        return "", ReviewStatus.NEEDS_REVIEW
    if not text.strip():
        return "", ReviewStatus.NEEDS_REVIEW
    return text, ReviewStatus.DRAFT


def _render_page_png(page: fitz.Page, output_path: Path) -> ReviewStatus | None:
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
        pixmap.save(output_path)
    except Exception:
        return ReviewStatus.NEEDS_REVIEW
    return None


def _get_or_create_sheet(db: Session, drawing_file_id: int, page_index: int) -> DrawingSheet:
    sheet = (
        db.query(DrawingSheet)
        .filter(
            DrawingSheet.drawing_file_id == drawing_file_id,
            DrawingSheet.page_index == page_index,
        )
        .one_or_none()
    )
    if sheet is not None:
        return sheet
    sheet = DrawingSheet(drawing_file_id=drawing_file_id, page_index=page_index)
    db.add(sheet)
    return sheet


@router.post("/upload", response_model=DrawingFileRead, status_code=status.HTTP_201_CREATED)
def upload_drawing_file(
    project_id: int = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> DrawingFile:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found.",
        )

    original_filename = _safe_pdf_filename(file.filename)
    upload_dir = settings.uploads_dir / str(project_id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    stored_path = upload_dir / f"{uuid4().hex}_{original_filename}"

    try:
        with stored_path.open("wb") as target:
            copyfileobj(file.file, target)
        page_count = _count_pdf_pages(stored_path)
    except HTTPException:
        if stored_path.exists():
            stored_path.unlink()
        raise
    finally:
        file.file.close()

    drawing_file = DrawingFile(
        project_id=project_id,
        original_filename=original_filename,
        stored_path=str(stored_path),
        page_count=page_count,
    )
    db.add(drawing_file)
    db.commit()
    db.refresh(drawing_file)
    return drawing_file


@router.post(
    "/{drawing_file_id}/pages/process",
    response_model=DrawingFilePageProcessResult,
)
def process_drawing_file_pages(
    drawing_file_id: int,
    db: Session = Depends(get_db),
) -> DrawingFilePageProcessResult:
    drawing_file = db.get(DrawingFile, drawing_file_id)
    if drawing_file is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Drawing file not found.",
        )

    pdf_path = Path(drawing_file.stored_path)
    if not pdf_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stored PDF file not found.",
        )

    try:
        document = fitz.open(pdf_path)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Stored file is not a valid PDF.",
        ) from exc

    processed_sheets: list[DrawingSheet] = []
    with document:
        drawing_file.page_count = document.page_count
        for page_index in range(document.page_count):
            sheet = _get_or_create_sheet(db, drawing_file_id, page_index)
            try:
                page = document.load_page(page_index)
                text, text_status = _extract_page_text(page)
                render_status = _render_page_png(page, _rendered_page_path(drawing_file_id, page_index))
                sheet.text_content = text
                sheet.status = render_status or text_status
            except Exception:
                sheet.text_content = ""
                sheet.status = ReviewStatus.NEEDS_REVIEW
            processed_sheets.append(sheet)

    db.commit()
    for sheet in processed_sheets:
        db.refresh(sheet)
    db.refresh(drawing_file)

    return DrawingFilePageProcessResult(
        drawing_file_id=drawing_file.id,
        page_count=drawing_file.page_count,
        sheets=processed_sheets,
    )


@router.get("/{drawing_file_id}/pages/{page_index}/image")
def get_page_image(drawing_file_id: int, page_index: int, db: Session = Depends(get_db)) -> FileResponse:
    drawing_file = db.get(DrawingFile, drawing_file_id)
    if drawing_file is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Drawing file not found.",
        )

    image_path = _rendered_page_path(drawing_file_id, page_index)
    if not image_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rendered page image not found.",
        )

    return FileResponse(image_path, media_type="image/png")


@router.get(
    "/{drawing_file_id}/sheets/search",
    response_model=DrawingSheetSearchResponse,
)
def search_drawing_file_sheets(
    drawing_file_id: int,
    query: str | None = Query(default=None),
    sheet_no: str | None = Query(default=None),
    keyword: str | None = Query(default=None),
    sheet_role: DrawingSheetRole | None = Query(default=None),
    db: Session = Depends(get_db),
) -> DrawingSheetSearchResponse:
    drawing_file = db.get(DrawingFile, drawing_file_id)
    if drawing_file is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Drawing file not found.",
        )

    sheet_query = db.query(DrawingSheet).filter(DrawingSheet.drawing_file_id == drawing_file_id)
    if sheet_role is not None:
        sheet_query = sheet_query.filter(DrawingSheet.role == sheet_role)

    sheets = sheet_query.order_by(DrawingSheet.page_index).all()
    matching_sheets = filter_sheets_by_sheet_no(sheets, sheet_no)
    matching_sheets = filter_sheets_by_keyword(matching_sheets, keyword if keyword is not None else query)

    return DrawingSheetSearchResponse(
        drawing_file_id=drawing_file.id,
        results=[
            DrawingSheetSearchResult(
                page_index=sheet.page_index,
                sheet_no=sheet.sheet_no,
                sheet_title=sheet.sheet_title,
                sheet_role=sheet.role,
                confidence=sheet.sheet_detection_confidence,
            )
            for sheet in matching_sheets
        ],
    )


@router.get(
    "/{drawing_file_id}/room-page-candidates",
    response_model=RoomPageCandidateResponse,
)
def find_room_page_candidates(
    drawing_file_id: int,
    room_query: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
) -> RoomPageCandidateResponse:
    drawing_file = db.get(DrawingFile, drawing_file_id)
    if drawing_file is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Drawing file not found.",
        )

    sheets = _sheets_for_drawing_file(db, drawing_file_id)
    room_finishes = (
        db.query(RoomFinish)
        .filter(RoomFinish.project_id == drawing_file.project_id)
        .order_by(RoomFinish.id)
        .all()
    )
    measurements = (
        db.query(Measurement)
        .filter(Measurement.project_id == drawing_file.project_id)
        .order_by(Measurement.id)
        .all()
    )
    candidates, warnings = build_room_page_candidates(sheets, room_finishes, measurements, room_query)
    return RoomPageCandidateResponse(
        drawing_file_id=drawing_file.id,
        room_query=room_query,
        candidates=[
            RoomPageCandidate(
                page_index=candidate.page_index,
                sheet_no=candidate.sheet_no,
                sheet_title=candidate.sheet_title,
                sheet_role=candidate.sheet_role,
                room_no=candidate.room_no,
                room_name=candidate.room_name,
                evidence=candidate.evidence,
                confidence=candidate.confidence,
            )
            for candidate in candidates
        ],
        warnings=warnings,
    )


@router.post(
    "/{drawing_file_id}/pages/{page_index}/dimension-candidates",
    response_model=DimensionCandidateResponse,
)
def get_dimension_candidates(
    drawing_file_id: int,
    page_index: int,
    payload: DimensionCandidateRequest,
    db: Session = Depends(get_db),
) -> DimensionCandidateResponse:
    drawing_file = db.get(DrawingFile, drawing_file_id)
    if drawing_file is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Drawing file not found.",
        )

    sheet = (
        db.query(DrawingSheet)
        .filter(
            DrawingSheet.drawing_file_id == drawing_file_id,
            DrawingSheet.page_index == page_index,
        )
        .one_or_none()
    )
    if sheet is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Drawing sheet not found.",
        )

    candidates, warnings = extract_dimension_candidates(
        drawing_file,
        sheet,
        dimension_region_from_mapping(payload.region),
    )
    return DimensionCandidateResponse(
        drawing_file_id=drawing_file.id,
        page_index=page_index,
        candidates=[
            DimensionCandidate(
                raw_text=candidate.raw_text,
                normalized_value=candidate.normalized_value,
                normalized_unit=candidate.normalized_unit,
                unit_guess=candidate.unit_guess,
                source_sheet=candidate.source_sheet,
                page_index=candidate.page_index,
                bbox=candidate.bbox,
                confidence=candidate.confidence,
                status=candidate.status,
                warning=candidate.warning,
            )
            for candidate in candidates
        ],
        warnings=warnings,
    )


@router.post(
    "/{drawing_file_id}/sheets/detect",
    response_model=DrawingFileSheetDetectionResult,
)
def detect_drawing_file_sheets(
    drawing_file_id: int,
    db: Session = Depends(get_db),
) -> DrawingFileSheetDetectionResult:
    drawing_file = db.get(DrawingFile, drawing_file_id)
    if drawing_file is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Drawing file not found.",
        )

    sheets = (
        db.query(DrawingSheet)
        .filter(DrawingSheet.drawing_file_id == drawing_file_id)
        .order_by(DrawingSheet.page_index)
        .all()
    )
    detected_sheets = detect_and_apply_sheet_metadata(sheets)
    db.commit()
    for sheet in detected_sheets:
        db.refresh(sheet)

    return DrawingFileSheetDetectionResult(
        drawing_file_id=drawing_file.id,
        sheets=detected_sheets,
    )


@router.post(
    "/{drawing_file_id}/sheets/classify",
    response_model=DrawingFileSheetClassificationResult,
)
def classify_drawing_file_sheets(
    drawing_file_id: int,
    db: Session = Depends(get_db),
) -> DrawingFileSheetClassificationResult:
    drawing_file = db.get(DrawingFile, drawing_file_id)
    if drawing_file is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Drawing file not found.",
        )

    sheets = (
        db.query(DrawingSheet)
        .filter(DrawingSheet.drawing_file_id == drawing_file_id)
        .order_by(DrawingSheet.page_index)
        .all()
    )
    classified_sheets = classify_and_apply_sheet_roles(sheets)
    db.commit()
    for sheet in classified_sheets:
        db.refresh(sheet)

    return DrawingFileSheetClassificationResult(
        drawing_file_id=drawing_file.id,
        sheets=classified_sheets,
    )


def _sheets_for_drawing_file(db: Session, drawing_file_id: int) -> list[DrawingSheet]:
    return (
        db.query(DrawingSheet)
        .filter(DrawingSheet.drawing_file_id == drawing_file_id)
        .order_by(DrawingSheet.page_index)
        .all()
    )
