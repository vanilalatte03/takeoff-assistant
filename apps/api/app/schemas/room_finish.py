from pydantic import BaseModel, ConfigDict

from app.models.enums import ReviewStatus


class RoomFinishBase(BaseModel):
    project_id: int
    drawing_sheet_id: int | None = None
    room_no: str | None = None
    room_name: str | None = None
    floor_material: str | None = None
    floor_finish: str | None = None
    base_material: str | None = None
    base_finish: str | None = None
    wall_material: str | None = None
    wall_finish: str | None = None
    ceiling_material: str | None = None
    ceiling_finish: str | None = None
    height: str | None = None
    remarks: str | None = None
    source_sheet_no: str | None = None
    confidence: float | None = None
    status: ReviewStatus = ReviewStatus.NEEDS_REVIEW


class RoomFinishCreate(RoomFinishBase):
    pass


class RoomFinishUpdate(BaseModel):
    drawing_sheet_id: int | None = None
    room_no: str | None = None
    room_name: str | None = None
    floor_material: str | None = None
    floor_finish: str | None = None
    base_material: str | None = None
    base_finish: str | None = None
    wall_material: str | None = None
    wall_finish: str | None = None
    ceiling_material: str | None = None
    ceiling_finish: str | None = None
    height: str | None = None
    remarks: str | None = None
    source_sheet_no: str | None = None
    confidence: float | None = None
    status: ReviewStatus | None = None


class RoomFinishRead(RoomFinishBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class RoomFinishExtractionResult(BaseModel):
    drawing_file_id: int
    room_finishes: list[RoomFinishRead]
