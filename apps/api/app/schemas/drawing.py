from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import DrawingSheetRole, ReviewStatus


class DrawingFileBase(BaseModel):
    project_id: int
    original_filename: str
    stored_path: str
    page_count: int = 0


class DrawingFileCreate(DrawingFileBase):
    pass


class DrawingFileRead(DrawingFileBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DrawingSheetBase(BaseModel):
    drawing_file_id: int
    page_index: int
    sheet_no: str | None = None
    sheet_title: str | None = None
    role: DrawingSheetRole = DrawingSheetRole.UNKNOWN
    text_content: str = ""
    sheet_detection_confidence: float | None = None
    status: ReviewStatus = ReviewStatus.DRAFT


class DrawingSheetCreate(DrawingSheetBase):
    pass


class DrawingSheetRead(DrawingSheetBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class DrawingFilePageProcessResult(BaseModel):
    drawing_file_id: int
    page_count: int
    sheets: list[DrawingSheetRead]


class DrawingFileSheetDetectionResult(BaseModel):
    drawing_file_id: int
    sheets: list[DrawingSheetRead]


class DrawingFileSheetClassificationResult(BaseModel):
    drawing_file_id: int
    sheets: list[DrawingSheetRead]


class DrawingSheetSearchResult(BaseModel):
    page_index: int
    sheet_no: str | None = None
    sheet_title: str | None = None
    sheet_role: DrawingSheetRole
    confidence: float | None = None


class DrawingSheetSearchResponse(BaseModel):
    drawing_file_id: int
    results: list[DrawingSheetSearchResult]


class RoomPageCandidate(BaseModel):
    page_index: int
    sheet_no: str | None = None
    sheet_title: str | None = None
    sheet_role: DrawingSheetRole
    room_no: str | None = None
    room_name: str | None = None
    evidence: list[str] = Field(default_factory=list)
    confidence: float


class RoomPageCandidateResponse(BaseModel):
    drawing_file_id: int
    room_query: str
    candidates: list[RoomPageCandidate]
    warnings: list[str] = Field(default_factory=list)


class DimensionRegion(BaseModel):
    x: float
    y: float
    width: float
    height: float
    image_width: float | None = None
    image_height: float | None = None
    zoom: float | None = None
    pan_x: float | None = None
    pan_y: float | None = None


class DimensionCandidateRequest(BaseModel):
    region: DimensionRegion | None = None


class DimensionCandidate(BaseModel):
    raw_text: str
    normalized_value: Decimal | None = None
    normalized_unit: str | None = None
    unit_guess: str | None = None
    source_sheet: str | None = None
    page_index: int
    bbox: dict[str, float] | None = None
    confidence: float
    status: ReviewStatus = ReviewStatus.NEEDS_REVIEW
    warning: str | None = None


class DimensionCandidateResponse(BaseModel):
    drawing_file_id: int
    page_index: int
    candidates: list[DimensionCandidate]
    warnings: list[str] = Field(default_factory=list)
