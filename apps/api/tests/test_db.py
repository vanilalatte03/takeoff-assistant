from decimal import Decimal

from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import Session

from app.db.init_db import init_db
from app.models import (
    DrawingFile,
    DrawingSheet,
    DrawingSheetRole,
    Measurement,
    MeasurementType,
    Project,
    ReviewStatus,
    RoomFinish,
)


def test_init_db_creates_expected_tables(tmp_path) -> None:
    database_url = f"sqlite:///{(tmp_path / 'takeoff_test.db').as_posix()}"
    engine = create_engine(database_url)

    init_db(engine)

    table_names = set(inspect(engine).get_table_names())
    assert {
        "projects",
        "drawing_files",
        "drawing_sheets",
        "room_finishes",
        "measurements",
    }.issubset(table_names)


def test_basic_model_creation_uses_editable_candidate_statuses(tmp_path) -> None:
    database_url = f"sqlite:///{(tmp_path / 'takeoff_test.db').as_posix()}"
    engine = create_engine(database_url)
    init_db(engine)

    with Session(engine) as session:
        project = Project(name="Sample Project")
        session.add(project)
        session.flush()

        drawing_file = DrawingFile(
            project_id=project.id,
            original_filename="sample.pdf",
            stored_path="data/uploads/sample.pdf",
            page_count=12,
        )
        session.add(drawing_file)
        session.flush()

        sheet = DrawingSheet(
            drawing_file_id=drawing_file.id,
            page_index=0,
            sheet_no="AE401",
            sheet_title="INTR / EXT FINISH SCHEDULE",
            role=DrawingSheetRole.FINISH_SCHEDULE,
            text_content="RM NOS ROOM NAMES FLOOR BASE INTERIOR WALL CEILING",
            sheet_detection_confidence=0.8,
        )
        session.add(sheet)
        session.flush()

        room_finish = RoomFinish(
            project_id=project.id,
            drawing_sheet_id=sheet.id,
            room_no="101",
            room_name="OFFICE",
            floor_finish="F-1",
            wall_finish="W-1",
            ceiling_finish="C-1",
            source_sheet_no="AE401",
            confidence=0.55,
        )
        session.add(room_finish)
        session.flush()

        measurement = Measurement(
            project_id=project.id,
            room_finish_id=room_finish.id,
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
        session.add(measurement)
        session.commit()

        assert room_finish.status == ReviewStatus.NEEDS_REVIEW
        assert measurement.status == ReviewStatus.DRAFT
        assert measurement.formula == "4.2 * 2.7"
        assert measurement.quantity == Decimal("11.34")
        assert measurement.unit == "m2"
        assert measurement.source_sheets == "AE401, AE101"
