from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.init_db import init_db
from app.db.session import get_db
from app.main import app
from app.models import DrawingFile, DrawingSheet, DrawingSheetRole, Project, ReviewStatus, RoomFinish


@pytest.fixture()
def client_with_db(tmp_path) -> Generator[tuple[TestClient, sessionmaker[Session], int, int], None, None]:
    database_url = f"sqlite:///{(tmp_path / 'room_finishes_test.db').as_posix()}"
    engine = create_engine(
        database_url,
        connect_args={"check_same_thread": False},
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    init_db(engine)

    with TestingSessionLocal() as session:
        project = Project(name="Room Finish Project")
        session.add(project)
        session.flush()
        drawing_file = DrawingFile(
            project_id=project.id,
            original_filename="sample.pdf",
            stored_path="data/uploads/sample.pdf",
            page_count=3,
        )
        session.add(drawing_file)
        session.flush()
        finish_sheet = DrawingSheet(
            drawing_file_id=drawing_file.id,
            page_index=0,
            sheet_no="AE401",
            sheet_title="INTR / EXT FINISH SCHEDULE",
            role=DrawingSheetRole.FINISH_SCHEDULE,
            text_content="""
            RM NOS | ROOM NAMES | FLOOR | BASE | INTERIOR WALL | CEILING | HGT
            110 | OFFICE | VCT | RB | GWB | ACT | 9'-0"
            111 | CORRIDOR | LVT | RB | PT | ACT | 8'-6"
            """,
        )
        plan_sheet = DrawingSheet(
            drawing_file_id=drawing_file.id,
            page_index=1,
            sheet_no="AE101",
            sheet_title="NEW FLOOR PLAN",
            role=DrawingSheetRole.FLOOR_PLAN,
            text_content="110 OFFICE",
        )
        session.add_all([finish_sheet, plan_sheet])
        session.commit()
        drawing_file_id = drawing_file.id
        project_id = project.id

    def override_get_db() -> Generator[Session, None, None]:
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(app), TestingSessionLocal, drawing_file_id, project_id
    finally:
        app.dependency_overrides.clear()


def test_extract_room_finishes_from_finish_schedule_sheets(client_with_db) -> None:
    client, session_factory, drawing_file_id, _ = client_with_db

    response = client.post(f"/drawing-files/{drawing_file_id}/room-finishes/extract")

    assert response.status_code == 200
    payload = response.json()
    assert payload["drawing_file_id"] == drawing_file_id
    assert len(payload["room_finishes"]) == 2
    first = payload["room_finishes"][0]
    assert first["room_no"] == "110"
    assert first["room_name"] == "OFFICE"
    assert first["floor_finish"] == "VCT"
    assert first["base_finish"] == "RB"
    assert first["wall_finish"] == "GWB"
    assert first["ceiling_finish"] == "ACT"
    assert first["height"] == "9'-0\""
    assert first["source_sheet_no"] == "AE401"
    assert first["status"] == ReviewStatus.NEEDS_REVIEW

    with session_factory() as session:
        rows = session.query(RoomFinish).order_by(RoomFinish.room_no).all()
        assert len(rows) == 2
        assert all(row.status == ReviewStatus.NEEDS_REVIEW for row in rows)
        assert {row.room_no for row in rows} == {"110", "111"}


def test_extract_room_finishes_is_idempotent(client_with_db) -> None:
    client, session_factory, drawing_file_id, _ = client_with_db

    first_response = client.post(f"/drawing-files/{drawing_file_id}/room-finishes/extract")
    second_response = client.post(f"/drawing-files/{drawing_file_id}/room-finishes/extract")

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert len(second_response.json()["room_finishes"]) == 0
    with session_factory() as session:
        assert session.query(RoomFinish).count() == 2


def test_extract_room_finishes_returns_empty_when_auto_extraction_fails(client_with_db) -> None:
    client, session_factory, drawing_file_id, _ = client_with_db
    with session_factory() as session:
        finish_sheet = (
            session.query(DrawingSheet)
            .filter(
                DrawingSheet.drawing_file_id == drawing_file_id,
                DrawingSheet.role == DrawingSheetRole.FINISH_SCHEDULE,
            )
            .one()
        )
        finish_sheet.text_content = "Unparseable finish schedule text"
        session.commit()

    response = client.post(f"/drawing-files/{drawing_file_id}/room-finishes/extract")

    assert response.status_code == 200
    assert response.json()["room_finishes"] == []


def test_create_room_finish_allows_manual_input_after_failed_extraction(client_with_db) -> None:
    client, _, _, project_id = client_with_db

    response = client.post(
        "/room-finishes",
        json={
            "project_id": project_id,
            "room_no": "210",
            "room_name": "MANUAL ROOM",
            "floor_finish": "VCT",
            "base_finish": "RB",
            "wall_finish": "GWB",
            "ceiling_finish": "ACT",
            "height": "9'-0\"",
            "source_sheet_no": "AE401",
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["room_no"] == "210"
    assert payload["room_name"] == "MANUAL ROOM"
    assert payload["status"] == ReviewStatus.NEEDS_REVIEW


def test_create_room_finish_for_drawing_file_derives_project_and_forces_review_status(client_with_db) -> None:
    client, _, drawing_file_id, _ = client_with_db

    response = client.post(
        f"/drawing-files/{drawing_file_id}/room-finishes",
        json={
            "room_no": "101~106",
            "room_name": "MULTI ROOM",
            "floor_finish": "VCT-1",
            "wall_finish": "GWB",
            "ceiling_finish": "ACST-1",
            "height": "2700",
            "source_sheet_no": "AE601",
            "status": "CONFIRMED",
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["room_no"] == "101~106"
    assert payload["status"] == ReviewStatus.NEEDS_REVIEW
    assert payload["confidence"] is None


def test_update_room_finish_allows_user_corrections(client_with_db) -> None:
    client, _, drawing_file_id, _ = client_with_db
    extract_response = client.post(f"/drawing-files/{drawing_file_id}/room-finishes/extract")
    room_finish_id = extract_response.json()["room_finishes"][0]["id"]

    response = client.patch(
        f"/room-finishes/{room_finish_id}",
        json={
            "room_name": "PRIVATE OFFICE",
            "floor_finish": "LVT",
            "height": "8'-6\"",
            "status": "DRAFT",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["room_name"] == "PRIVATE OFFICE"
    assert payload["floor_finish"] == "LVT"
    assert payload["height"] == "8'-6\""
    assert payload["status"] == ReviewStatus.DRAFT


def test_list_room_finishes_for_drawing_file(client_with_db) -> None:
    client, _, drawing_file_id, _ = client_with_db
    extract_response = client.post(f"/drawing-files/{drawing_file_id}/room-finishes/extract")
    assert extract_response.status_code == 200

    response = client.get(f"/drawing-files/{drawing_file_id}/room-finishes")

    assert response.status_code == 200
    assert [row["room_no"] for row in response.json()] == ["110", "111"]


def test_extract_room_finishes_requires_existing_drawing_file(client_with_db) -> None:
    client, _, _, _ = client_with_db

    response = client.post("/drawing-files/999/room-finishes/extract")

    assert response.status_code == 404
    assert response.json()["detail"] == "Drawing file not found."
