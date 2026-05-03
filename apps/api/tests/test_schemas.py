from decimal import Decimal

from app.models import DrawingSheetRole, MeasurementType, ReviewStatus
from app.schemas import (
    DrawingFileCreate,
    DrawingSheetCreate,
    MeasurementCreate,
    ProjectCreate,
    RoomFinishCreate,
)


def test_basic_schemas_capture_mvp_entities() -> None:
    project = ProjectCreate(name="Sample Project")
    drawing_file = DrawingFileCreate(
        project_id=1,
        original_filename="sample.pdf",
        stored_path="data/uploads/sample.pdf",
        page_count=3,
    )
    drawing_sheet = DrawingSheetCreate(
        drawing_file_id=1,
        page_index=0,
        sheet_no="AE401",
        sheet_title="INTR / EXT FINISH SCHEDULE",
        role=DrawingSheetRole.FINISH_SCHEDULE,
    )
    room_finish = RoomFinishCreate(
        project_id=1,
        drawing_sheet_id=1,
        room_no="101",
        room_name="OFFICE",
        floor_finish="F-1",
        source_sheet_no="AE401",
    )
    measurement = MeasurementCreate(
        project_id=1,
        room_finish_id=1,
        room_no="101",
        room_name="OFFICE",
        category="FLOOR",
        finish_code="F-1",
        measurement_type=MeasurementType.FLOOR_AREA,
        formula="4.2 * 2.7",
        quantity=Decimal("11.34"),
        unit="m2",
        source_sheets="AE401, AE101",
    )

    assert project.name == "Sample Project"
    assert drawing_file.page_count == 3
    assert drawing_sheet.role == DrawingSheetRole.FINISH_SCHEDULE
    assert drawing_sheet.status == ReviewStatus.DRAFT
    assert room_finish.status == ReviewStatus.NEEDS_REVIEW
    assert measurement.status == ReviewStatus.DRAFT
    assert measurement.formula == "4.2 * 2.7"
    assert measurement.quantity == Decimal("11.34")
    assert measurement.unit == "m2"
    assert measurement.source_sheets == "AE401, AE101"
