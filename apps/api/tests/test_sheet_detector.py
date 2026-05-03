from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.init_db import init_db
from app.db.session import get_db
from app.main import app
from app.models import DrawingFile, DrawingSheet, Project, ReviewStatus
from app.services.sheet_detector import detect_and_apply_sheet_metadata, detect_sheet_metadata


@pytest.fixture()
def client_with_db(tmp_path) -> Generator[tuple[TestClient, sessionmaker[Session]], None, None]:
    database_url = f"sqlite:///{(tmp_path / 'sheet_detector_test.db').as_posix()}"
    engine = create_engine(
        database_url,
        connect_args={"check_same_thread": False},
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    init_db(engine)

    def override_get_db() -> Generator[Session, None, None]:
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(app), TestingSessionLocal
    finally:
        app.dependency_overrides.clear()


def test_detect_sheet_metadata_from_direct_title_block_line() -> None:
    detection = detect_sheet_metadata("AE101 NEW FLOOR PLAN")

    assert detection.sheet_no == "AE101"
    assert detection.sheet_title == "NEW FLOOR PLAN"
    assert detection.confidence == 0.8


@pytest.mark.parametrize("text", ["FY24", "D13", "HD19", "ON12", "THAN10", "ACI-318"])
def test_detect_sheet_metadata_rejects_common_non_sheet_number_text(text) -> None:
    detection = detect_sheet_metadata(f"{text} GENERAL PROJECT NOTE")

    assert detection.sheet_no is None
    assert detection.sheet_title is None
    assert detection.confidence == 0


@pytest.mark.parametrize("sheet_no", ["AE101", "AE401", "AE402", "AE606", "A-001", "S-001"])
def test_detect_sheet_metadata_accepts_common_architectural_sheet_numbers(sheet_no) -> None:
    detection = detect_sheet_metadata(f"{sheet_no} DRAWING TITLE")

    assert detection.sheet_no == sheet_no
    assert detection.sheet_title == "DRAWING TITLE"
    assert detection.confidence == 0.8


def test_standalone_sheet_number_without_index_or_title_has_low_confidence() -> None:
    detection = detect_sheet_metadata("AE101")

    assert detection.sheet_no == "AE101"
    assert detection.sheet_title is None
    assert detection.confidence == 0.3


def test_detect_sheet_metadata_from_standalone_sheet_no_and_nearby_title() -> None:
    detection = detect_sheet_metadata(
        """
        PROJECT TITLE
        AE405
        FLOOR PARTITION TYPE KEY PLAN
        """
    )

    assert detection.sheet_no == "AE405"
    assert detection.sheet_title == "FLOOR PARTITION TYPE KEY PLAN"
    assert detection.confidence == 0.65


def test_index_sequence_maps_low_confidence_pages_without_title() -> None:
    sheets = [
        DrawingSheet(
            drawing_file_id=1,
            page_index=0,
            text_content="""
            INDEX OF DRAWINGS
            AE101 NEW FLOOR PLAN
            AE401 INTR / EXT FINISH SCHEDULE
            """,
        ),
        DrawingSheet(drawing_file_id=1, page_index=1, text_content="GENERAL NOTES WITHOUT TITLE BLOCK"),
        DrawingSheet(drawing_file_id=1, page_index=2, text_content="ANOTHER PAGE WITHOUT TITLE BLOCK"),
    ]

    detected = detect_and_apply_sheet_metadata(sheets)

    assert detected[1].sheet_no == "AE101"
    assert detected[1].sheet_title == "NEW FLOOR PLAN"
    assert detected[1].sheet_detection_confidence == 0.45
    assert detected[2].sheet_no == "AE401"
    assert detected[2].sheet_title == "INTR / EXT FINISH SCHEDULE"
    assert detected[2].sheet_detection_confidence == 0.45


def test_index_titles_override_page_title_block_titles() -> None:
    index_map = {
        "AE401": "INTR / EXT FINISH SCHEDULE",
        "AE402": "INTR / EXT FINISH SCHEDULE",
        "AE601": "EXTERIOR & INTERIOR FINISH SCHEDULE",
    }

    detection = detect_sheet_metadata("AE401 OUTDATED TITLE BLOCK TEXT", index_map)

    assert detection.sheet_no == "AE401"
    assert detection.sheet_title == "INTR / EXT FINISH SCHEDULE"
    assert detection.confidence == 0.95


def test_detector_does_not_treat_ae601_as_the_only_finish_schedule() -> None:
    index_page = DrawingSheet(
        drawing_file_id=1,
        page_index=0,
        text_content="""
        INDEX OF DRAWINGS
        AE401 INTR / EXT FINISH SCHEDULE
        AE402 INTR / EXT FINISH SCHEDULE
        AE601 EXTERIOR & INTERIOR FINISH SCHEDULE
        AE405 FLOOR PARTITION TYPE KEY PLAN
        """,
    )
    sheets = [
        index_page,
        DrawingSheet(drawing_file_id=1, page_index=1, text_content="AE401 TITLE BLOCK"),
        DrawingSheet(drawing_file_id=1, page_index=2, text_content="AE402 TITLE BLOCK"),
        DrawingSheet(drawing_file_id=1, page_index=3, text_content="AE601 TITLE BLOCK"),
        DrawingSheet(drawing_file_id=1, page_index=4, text_content="AE405 TITLE BLOCK"),
    ]

    detected = detect_and_apply_sheet_metadata(sheets)

    assert detected[0].sheet_no is None
    assert detected[0].status == ReviewStatus.NEEDS_REVIEW
    assert detected[1].sheet_no == "AE401"
    assert detected[1].sheet_title == "INTR / EXT FINISH SCHEDULE"
    assert detected[2].sheet_no == "AE402"
    assert detected[2].sheet_title == "INTR / EXT FINISH SCHEDULE"
    assert detected[3].sheet_no == "AE601"
    assert detected[3].sheet_title == "EXTERIOR & INTERIOR FINISH SCHEDULE"
    assert detected[4].sheet_no == "AE405"
    assert detected[4].sheet_title == "FLOOR PARTITION TYPE KEY PLAN"
    assert all(sheet.sheet_detection_confidence == 0.95 for sheet in detected[1:])


def test_detect_endpoint_updates_drawing_sheets_from_index_first(client_with_db) -> None:
    client, session_factory = client_with_db
    with session_factory() as session:
        project = Project(name="Sheet Detector Project")
        session.add(project)
        session.flush()
        drawing_file = DrawingFile(
            project_id=project.id,
            original_filename="sample.pdf",
            stored_path="data/uploads/sample.pdf",
            page_count=4,
        )
        session.add(drawing_file)
        session.flush()
        session.add_all(
            [
                DrawingSheet(
                    drawing_file_id=drawing_file.id,
                    page_index=0,
                    text_content="""
                    SCHEDULE OF DRAWINGS
                    AE101 NEW FLOOR PLAN
                    AE401 INTR / EXT FINISH SCHEDULE
                    AE601 EXTERIOR & INTERIOR FINISH SCHEDULE
                    """,
                ),
                DrawingSheet(
                    drawing_file_id=drawing_file.id,
                    page_index=1,
                    text_content="AE101 FLOOR PLAN TITLE BLOCK",
                ),
                DrawingSheet(
                    drawing_file_id=drawing_file.id,
                    page_index=2,
                    text_content="AE401 FINISH SCHEDULE TITLE BLOCK",
                ),
                DrawingSheet(
                    drawing_file_id=drawing_file.id,
                    page_index=3,
                    text_content="AE601 FINISH SCHEDULE TITLE BLOCK",
                ),
            ]
        )
        session.commit()
        drawing_file_id = drawing_file.id

    response = client.post(f"/drawing-files/{drawing_file_id}/sheets/detect")

    assert response.status_code == 200
    payload = response.json()
    assert payload["drawing_file_id"] == drawing_file_id
    assert payload["sheets"][1]["sheet_no"] == "AE101"
    assert payload["sheets"][1]["sheet_title"] == "NEW FLOOR PLAN"
    assert payload["sheets"][1]["sheet_detection_confidence"] == 0.95
    assert payload["sheets"][2]["sheet_no"] == "AE401"
    assert payload["sheets"][2]["sheet_title"] == "INTR / EXT FINISH SCHEDULE"
    assert payload["sheets"][3]["sheet_no"] == "AE601"
    assert payload["sheets"][3]["sheet_title"] == "EXTERIOR & INTERIOR FINISH SCHEDULE"

    with session_factory() as session:
        detected_sheets = (
            session.query(DrawingSheet)
            .filter(DrawingSheet.drawing_file_id == drawing_file_id)
            .order_by(DrawingSheet.page_index)
            .all()
        )
        assert detected_sheets[1].sheet_no == "AE101"
        assert detected_sheets[2].sheet_title == "INTR / EXT FINISH SCHEDULE"
        assert detected_sheets[3].sheet_title == "EXTERIOR & INTERIOR FINISH SCHEDULE"


def test_detect_endpoint_requires_existing_drawing_file(client_with_db) -> None:
    client, _ = client_with_db

    response = client.post("/drawing-files/999/sheets/detect")

    assert response.status_code == 404
    assert response.json()["detail"] == "Drawing file not found."
