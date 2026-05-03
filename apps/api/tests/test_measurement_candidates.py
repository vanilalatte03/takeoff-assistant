from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.init_db import init_db
from app.db.session import get_db
from app.main import app
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
from app.services.measurement_candidate_generator import build_measurement_candidate_specs


@pytest.fixture()
def client_with_db(tmp_path) -> Generator[tuple[TestClient, sessionmaker[Session], int], None, None]:
    database_url = f"sqlite:///{(tmp_path / 'measurement_candidates_test.db').as_posix()}"
    engine = create_engine(
        database_url,
        connect_args={"check_same_thread": False},
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    init_db(engine)

    with TestingSessionLocal() as session:
        project = Project(name="Measurement Candidate Project")
        session.add(project)
        session.flush()
        drawing_file = DrawingFile(
            project_id=project.id,
            original_filename="sample.pdf",
            stored_path="data/uploads/sample.pdf",
            page_count=2,
        )
        session.add(drawing_file)
        session.flush()
        finish_sheet = DrawingSheet(
            drawing_file_id=drawing_file.id,
            page_index=0,
            sheet_no="AE401",
            sheet_title="INTR / EXT FINISH SCHEDULE",
            role=DrawingSheetRole.FINISH_SCHEDULE,
        )
        session.add(finish_sheet)
        session.flush()
        session.add_all(
            [
                RoomFinish(
                    project_id=project.id,
                    drawing_sheet_id=finish_sheet.id,
                    room_no="110",
                    room_name="OFFICE",
                    floor_finish="VCT",
                    base_finish="RB",
                    wall_finish="GWB",
                    ceiling_finish="ACT",
                    source_sheet_no="AE401",
                    status=ReviewStatus.NEEDS_REVIEW,
                ),
                RoomFinish(
                    project_id=project.id,
                    drawing_sheet_id=finish_sheet.id,
                    room_no="111",
                    room_name="CORRIDOR",
                    floor_finish="VCT",
                    ceiling_finish="ACT",
                    source_sheet_no="AE401",
                    status=ReviewStatus.NEEDS_REVIEW,
                ),
                RoomFinish(
                    project_id=project.id,
                    drawing_sheet_id=finish_sheet.id,
                    room_no="112",
                    room_name="EMPTY",
                    source_sheet_no="AE401",
                    status=ReviewStatus.NEEDS_REVIEW,
                ),
            ]
        )
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


def test_build_measurement_candidate_specs_from_room_finish_codes() -> None:
    room_finish = RoomFinish(
        project_id=1,
        room_no="110",
        room_name="OFFICE",
        floor_finish="VCT",
        base_finish="RB",
        wall_finish="GWB",
        ceiling_finish="ACT",
        source_sheet_no="AE401",
    )

    specs = build_measurement_candidate_specs(room_finish)

    assert [(spec.category, spec.finish_code, spec.measurement_type, spec.unit) for spec in specs] == [
        ("FLOOR", "VCT", MeasurementType.FLOOR_AREA, "m2"),
        ("CEILING", "ACT", MeasurementType.CEILING_AREA, "m2"),
        ("WALL", "GWB", MeasurementType.WALL_AREA, "m2"),
        ("BASE", "RB", MeasurementType.PERIMETER_LENGTH, "m"),
    ]


def test_generate_measurement_candidates_from_room_finishes(client_with_db) -> None:
    client, session_factory, drawing_file_id = client_with_db

    response = client.post(f"/drawing-files/{drawing_file_id}/measurements/generate")

    assert response.status_code == 200
    payload = response.json()
    assert payload["drawing_file_id"] == drawing_file_id
    assert len(payload["measurements"]) == 6
    assert [(row["room_no"], row["category"], row["finish_code"], row["measurement_type"]) for row in payload["measurements"]] == [
        ("110", "FLOOR", "VCT", "FLOOR_AREA"),
        ("110", "CEILING", "ACT", "CEILING_AREA"),
        ("110", "WALL", "GWB", "WALL_AREA"),
        ("110", "BASE", "RB", "PERIMETER_LENGTH"),
        ("111", "FLOOR", "VCT", "FLOOR_AREA"),
        ("111", "CEILING", "ACT", "CEILING_AREA"),
    ]
    assert all(row["status"] == ReviewStatus.DRAFT for row in payload["measurements"])
    assert all(row["quantity"] is None for row in payload["measurements"])
    assert all(row["formula"] is None for row in payload["measurements"])
    assert all(row["source_sheets"] == "AE401" for row in payload["measurements"])
    assert payload["measurements"][0]["unit"] == "m2"
    assert payload["measurements"][3]["unit"] == "m"

    with session_factory() as session:
        measurements = session.query(Measurement).order_by(Measurement.id).all()
        assert len(measurements) == 6
        assert measurements[0].room_no == "110"
        assert measurements[0].quantity is None
        assert measurements[0].status == ReviewStatus.DRAFT
        assert measurements[0].source_sheets == "AE401"


def test_generate_measurement_candidates_is_idempotent(client_with_db) -> None:
    client, session_factory, drawing_file_id = client_with_db

    first_response = client.post(f"/drawing-files/{drawing_file_id}/measurements/generate")
    second_response = client.post(f"/drawing-files/{drawing_file_id}/measurements/generate")

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert len(first_response.json()["measurements"]) == 6
    assert second_response.json()["measurements"] == []
    with session_factory() as session:
        assert session.query(Measurement).count() == 6


def test_list_measurements_for_drawing_file(client_with_db) -> None:
    client, _, drawing_file_id = client_with_db
    generate_response = client.post(f"/drawing-files/{drawing_file_id}/measurements/generate")
    assert generate_response.status_code == 200

    response = client.get(f"/drawing-files/{drawing_file_id}/measurements")

    assert response.status_code == 200
    assert len(response.json()) == 6
    assert response.json()[0]["room_no"] == "110"


def test_generate_measurement_candidates_returns_empty_without_room_finishes(tmp_path) -> None:
    database_url = f"sqlite:///{(tmp_path / 'empty_measurement_candidates_test.db').as_posix()}"
    engine = create_engine(
        database_url,
        connect_args={"check_same_thread": False},
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    init_db(engine)

    with TestingSessionLocal() as session:
        project = Project(name="Empty Measurement Candidate Project")
        session.add(project)
        session.flush()
        drawing_file = DrawingFile(
            project_id=project.id,
            original_filename="sample.pdf",
            stored_path="data/uploads/sample.pdf",
            page_count=1,
        )
        session.add(drawing_file)
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
        with TestClient(app) as client:
            response = client.post(f"/drawing-files/{drawing_file_id}/measurements/generate")
            assert response.status_code == 200
            assert response.json()["measurements"] == []
    finally:
        app.dependency_overrides.clear()


def test_generate_measurement_candidates_requires_existing_drawing_file(client_with_db) -> None:
    client, _, _ = client_with_db

    response = client.post("/drawing-files/999/measurements/generate")

    assert response.status_code == 404
    assert response.json()["detail"] == "Drawing file not found."
