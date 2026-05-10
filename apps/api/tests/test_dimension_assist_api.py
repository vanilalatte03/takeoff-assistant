from collections.abc import Generator
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.init_db import init_db
from app.db.session import get_db
from app.main import app
from app.models import DrawingFile, DrawingSheet, DrawingSheetRole, Measurement, MeasurementType, Project, ReviewStatus, RoomFinish


@pytest.fixture()
def client_with_dimension_assist_db(tmp_path) -> Generator[tuple[TestClient, sessionmaker[Session], int], None, None]:
    database_url = f"sqlite:///{(tmp_path / 'dimension_assist_test.db').as_posix()}"
    engine = create_engine(
        database_url,
        connect_args={"check_same_thread": False},
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    init_db(engine)

    with TestingSessionLocal() as session:
        project = Project(name="Dimension Assist Project")
        session.add(project)
        session.flush()
        drawing_file = DrawingFile(
            project_id=project.id,
            original_filename="sample.pdf",
            stored_path=str(tmp_path / "missing.pdf"),
            page_count=3,
        )
        session.add(drawing_file)
        session.flush()
        floor_plan = DrawingSheet(
            drawing_file_id=drawing_file.id,
            page_index=0,
            sheet_no="AE101",
            sheet_title="NEW FLOOR PLAN",
            role=DrawingSheetRole.FLOOR_PLAN,
            text_content='Room 119 OFFICE dimensions 4200 2700 9\'-0"',
            sheet_detection_confidence=0.93,
        )
        schedule = DrawingSheet(
            drawing_file_id=drawing_file.id,
            page_index=1,
            sheet_no="AE401",
            sheet_title="FINISH SCHEDULE",
            role=DrawingSheetRole.FINISH_SCHEDULE,
            text_content="RM 119 OFFICE VCT GWB ACT",
            sheet_detection_confidence=0.95,
        )
        partition_plan = DrawingSheet(
            drawing_file_id=drawing_file.id,
            page_index=2,
            sheet_no="AE103",
            sheet_title="PARTITION PLAN",
            role=DrawingSheetRole.PARTITION_PLAN,
            text_content="partition layout only",
            sheet_detection_confidence=0.88,
        )
        session.add_all([floor_plan, schedule, partition_plan])
        session.flush()
        room_finish = RoomFinish(
            project_id=project.id,
            drawing_sheet_id=schedule.id,
            room_no="119",
            room_name="OFFICE",
            floor_finish="VCT",
            wall_finish="GWB",
            source_sheet_no="AE401",
            confidence=0.86,
        )
        measurement = Measurement(
            project_id=project.id,
            room_no="119",
            room_name="OFFICE",
            category="WALL",
            finish_code="GWB",
            measurement_type=MeasurementType.WALL_AREA,
            source_sheets="AE101, AE103",
            status=ReviewStatus.NEEDS_REVIEW,
        )
        session.add_all([room_finish, measurement])
        session.commit()
        drawing_file_id = drawing_file.id

    def override_get_db() -> Generator[Session, None, None]:
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(app), TestingSessionLocal, drawing_file_id
    finally:
        app.dependency_overrides.clear()


def test_room_page_candidates_prefers_plan_sheets_and_includes_evidence(client_with_dimension_assist_db) -> None:
    client, _, drawing_file_id = client_with_dimension_assist_db

    response = client.get(
        f"/drawing-files/{drawing_file_id}/room-page-candidates",
        params={"room_query": "119"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["drawing_file_id"] == drawing_file_id
    assert payload["room_query"] == "119"
    assert [candidate["sheet_no"] for candidate in payload["candidates"]][:2] == ["AE101", "AE103"]
    assert payload["candidates"][0]["sheet_role"] == "FLOOR_PLAN"
    assert payload["candidates"][0]["room_no"] == "119"
    assert any("sheet text" in item for item in payload["candidates"][0]["evidence"])


def test_room_page_candidates_returns_warning_for_no_match(client_with_dimension_assist_db) -> None:
    client, _, drawing_file_id = client_with_dimension_assist_db

    response = client.get(
        f"/drawing-files/{drawing_file_id}/room-page-candidates",
        params={"room_query": "999"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["candidates"] == []
    assert payload["warnings"]


def test_dimension_candidates_extracts_sheet_text_fallback_values(client_with_dimension_assist_db) -> None:
    client, _, drawing_file_id = client_with_dimension_assist_db

    response = client.post(
        f"/drawing-files/{drawing_file_id}/pages/0/dimension-candidates",
        json={
            "region": {
                "x": 10,
                "y": 20,
                "width": 200,
                "height": 100,
                "image_width": 1800,
                "image_height": 1200,
                "zoom": 1.5,
                "pan_x": 16,
                "pan_y": 16,
            }
        },
    )

    assert response.status_code == 200
    payload = response.json()
    values_by_raw_text = {candidate["raw_text"]: Decimal(str(candidate["normalized_value"])) for candidate in payload["candidates"]}
    assert values_by_raw_text["4200"] == Decimal("4.200")
    assert values_by_raw_text["2700"] == Decimal("2.700")
    assert values_by_raw_text["9'-0\""] == Decimal("2.743")
    assert all(candidate["status"] == "NEEDS_REVIEW" for candidate in payload["candidates"])
    assert any("falling back to sheet text" in warning for warning in payload["warnings"])


def test_dimension_candidates_requires_existing_sheet(client_with_dimension_assist_db) -> None:
    client, _, drawing_file_id = client_with_dimension_assist_db

    response = client.post(
        f"/drawing-files/{drawing_file_id}/pages/99/dimension-candidates",
        json={"region": None},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Drawing sheet not found."
