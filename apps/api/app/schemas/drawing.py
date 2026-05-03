from datetime import datetime

from pydantic import BaseModel, ConfigDict

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
