from collections.abc import Generator
from decimal import Decimal
from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from openpyxl import load_workbook
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.init_db import init_db
from app.db.session import get_db
from app.main import app
from app.models import DrawingFile, DrawingSheet, Measurement, MeasurementType, Project, ReviewStatus, RoomFinish
from app.services.measurement_excel_exporter import build_measurements_workbook


@pytest.fixture()
def client_with_measurement(tmp_path) -> Generator[tuple[TestClient, sessionmaker[Session], int], None, None]:
    database_url = f"sqlite:///{(tmp_path / 'measurement_update_test.db').as_posix()}"
    engine = create_engine(
        database_url,
        connect_args={"check_same_thread": False},
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    init_db(engine)

    with TestingSessionLocal() as session:
        project = Project(name="Measurement Update Project")
        session.add(project)
        session.flush()
        measurement = Measurement(
            project_id=project.id,
            room_no="110",
            room_name="OFFICE",
            category="FLOOR",
            finish_code="VCT",
            measurement_type=MeasurementType.FLOOR_AREA,
            source_sheets="AE401",
            status=ReviewStatus.NEEDS_REVIEW,
        )
        session.add(measurement)
        session.commit()
        measurement_id = measurement.id

    def override_get_db() -> Generator[Session, None, None]:
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(app), TestingSessionLocal, measurement_id
    finally:
        app.dependency_overrides.clear()


def test_update_measurement_api_saves_manual_coordinates_and_quantity(client_with_measurement) -> None:
    client, session_factory, measurement_id = client_with_measurement

    response = client.patch(
        f"/measurements/{measurement_id}",
        json={
            "formula": "manual polygon area from 4 points",
            "quantity": "18.25",
            "unit": "m2",
            "source_sheets": "AE101",
            "status": "DRAFT",
            "memo": "manual user measurement",
            "coordinates_json": {
                "measurement_mode": "POLYGON_AREA",
                "scale": {
                    "pixels_per_meter": 120.5,
                    "reference_length": 4.2,
                },
                "points": [
                    {"x": 10, "y": 10},
                    {"x": 110, "y": 10},
                    {"x": 110, "y": 90},
                    {"x": 10, "y": 90},
                ],
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["formula"] == "manual polygon area from 4 points"
    assert Decimal(str(payload["quantity"])) == Decimal("18.25")
    assert payload["unit"] == "m2"
    assert payload["source_sheets"] == "AE101"
    assert payload["status"] == ReviewStatus.DRAFT
    assert payload["coordinates_json"]["measurement_mode"] == "POLYGON_AREA"
    assert payload["coordinates_json"]["points"][0] == {"x": 10, "y": 10}

    with session_factory() as session:
        measurement = session.get(Measurement, measurement_id)
        assert measurement is not None
        assert measurement.coordinates_json is not None
        assert measurement.coordinates_json["scale"]["reference_length"] == 4.2
        assert measurement.quantity == Decimal("18.25")


def test_update_measurement_metadata_preserves_calculation_and_exports_updated_code(client_with_measurement) -> None:
    client, session_factory, measurement_id = client_with_measurement

    setup_response = client.patch(
        f"/measurements/{measurement_id}",
        json={
            "category": "PARTITION",
            "finish_code": "GWB",
            "measurement_type": "PARTITION_AREA",
            "formula": "4.2 * 4.6",
            "quantity": "19.32",
            "unit": "m2",
            "coordinates_json": {"points": [{"x": 1, "y": 2}]},
            "memo": "Verify actual partition type such as 5A, 3B, etc.",
        },
    )
    assert setup_response.status_code == 200

    response = client.patch(
        f"/measurements/{measurement_id}",
        json={
            "finish_code": "5A",
            "unit": "m2",
            "memo": "verified partition type",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["category"] == "PARTITION"
    assert payload["finish_code"] == "5A"
    assert payload["measurement_type"] == "PARTITION_AREA"
    assert payload["formula"] == "4.2 * 4.6"
    assert Decimal(str(payload["quantity"])) == Decimal("19.32")
    assert payload["coordinates_json"] == {"points": [{"x": 1, "y": 2}]}

    with session_factory() as session:
        measurement = session.get(Measurement, measurement_id)
        assert measurement is not None
        workbook = load_workbook(BytesIO(build_measurements_workbook([measurement]).getvalue()), data_only=True)

    assert workbook["Summary"]["A2"].value == "PARTITION"
    assert workbook["Summary"]["B2"].value == "5A"
    assert Decimal(str(workbook["Summary"]["D2"].value)) == Decimal("19.32")
    assert workbook["Details"]["E2"].value == "5A"


def test_update_measurement_api_requires_existing_measurement(client_with_measurement) -> None:
    client, _, _ = client_with_measurement

    response = client.patch(
        "/measurements/999",
        json={
            "quantity": "1.00",
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Measurement not found."


def test_reject_measurement_marks_unconfirmed_row_rejected(client_with_measurement) -> None:
    client, session_factory, measurement_id = client_with_measurement

    response = client.delete(f"/measurements/{measurement_id}")

    assert response.status_code == 200
    assert response.json()["status"] == ReviewStatus.REJECTED
    with session_factory() as session:
        measurement = session.get(Measurement, measurement_id)
        assert measurement is not None
        assert measurement.status == ReviewStatus.REJECTED


def test_reject_measurement_blocks_confirmed_row(client_with_measurement) -> None:
    client, session_factory, measurement_id = client_with_measurement
    with session_factory() as session:
        measurement = session.get(Measurement, measurement_id)
        assert measurement is not None
        measurement.status = ReviewStatus.CONFIRMED
        session.commit()

    response = client.delete(f"/measurements/{measurement_id}")

    assert response.status_code == 409
    assert response.json()["detail"] == "Confirmed measurements cannot be rejected."


def test_merge_measurements_sums_quantity_and_rejects_sources(client_with_measurement) -> None:
    client, session_factory, measurement_id = client_with_measurement
    with session_factory() as session:
        target = session.get(Measurement, measurement_id)
        assert target is not None
        target.quantity = Decimal("10.25")
        target.formula = "5 * 2.05"
        target.unit = "m2"
        target.source_sheets = "AE101"
        target.memo = "target memo"
        source = Measurement(
            project_id=target.project_id,
            room_no=target.room_no,
            room_name=target.room_name,
            category=target.category,
            finish_code=target.finish_code,
            measurement_type=target.measurement_type,
            formula="2 * 3",
            quantity=Decimal("6.00"),
            unit="m2",
            source_sheets="AE102",
            status=ReviewStatus.NEEDS_REVIEW,
            memo="source memo",
        )
        session.add(source)
        session.commit()
        source_id = source.id

    response = client.post("/measurements/merge", json={"target_id": measurement_id, "source_ids": [source_id]})

    assert response.status_code == 200
    payload = response.json()
    assert Decimal(str(payload["quantity"])) == Decimal("16.25")
    assert payload["source_sheets"] == "AE101, AE102"
    assert "#%s: 5 * 2.05" % measurement_id in payload["formula"]
    with session_factory() as session:
        source = session.get(Measurement, source_id)
        assert source is not None
        assert source.status == ReviewStatus.REJECTED


def test_merge_measurements_requires_matching_contract(client_with_measurement) -> None:
    client, session_factory, measurement_id = client_with_measurement
    with session_factory() as session:
        target = session.get(Measurement, measurement_id)
        assert target is not None
        source = Measurement(
            project_id=target.project_id,
            room_no="999",
            room_name=target.room_name,
            category=target.category,
            finish_code=target.finish_code,
            measurement_type=target.measurement_type,
            unit=target.unit,
            status=ReviewStatus.NEEDS_REVIEW,
        )
        session.add(source)
        session.commit()
        source_id = source.id

    response = client.post("/measurements/merge", json={"target_id": measurement_id, "source_ids": [source_id]})

    assert response.status_code == 400
    assert "room, category, code, type, and unit match" in response.json()["detail"]["message"]


def test_merge_measurements_blocks_rejected_rows(client_with_measurement) -> None:
    client, session_factory, measurement_id = client_with_measurement
    with session_factory() as session:
        target = session.get(Measurement, measurement_id)
        assert target is not None
        target.unit = "m2"
        source = Measurement(
            project_id=target.project_id,
            room_no=target.room_no,
            room_name=target.room_name,
            category=target.category,
            finish_code=target.finish_code,
            measurement_type=target.measurement_type,
            unit=target.unit,
            status=ReviewStatus.REJECTED,
        )
        session.add(source)
        session.commit()
        source_id = source.id

    response = client.post("/measurements/merge", json={"target_id": measurement_id, "source_ids": [source_id]})

    assert response.status_code == 400
    assert response.json()["detail"]["message"] == "Rejected measurements cannot be merged."
    assert response.json()["detail"]["measurement_ids"] == [source_id]


def test_drawing_file_room_status_summarizes_active_measurements(tmp_path) -> None:
    database_url = f"sqlite:///{(tmp_path / 'room_status_test.db').as_posix()}"
    engine = create_engine(database_url, connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    init_db(engine)
    with TestingSessionLocal() as session:
        project = Project(name="Room Status Project")
        session.add(project)
        session.flush()
        drawing_file = DrawingFile(
            project_id=project.id,
            original_filename="sample.pdf",
            stored_path="data/uploads/sample.pdf",
            page_count=1,
        )
        session.add(drawing_file)
        session.flush()
        sheet = DrawingSheet(drawing_file_id=drawing_file.id, page_index=0, sheet_no="AE401")
        session.add(sheet)
        session.flush()
        room_finish = RoomFinish(
            project_id=project.id,
            drawing_sheet_id=sheet.id,
            room_no="110",
            room_name="OFFICE",
        )
        session.add(room_finish)
        session.flush()
        session.add_all(
            [
                Measurement(
                    project_id=project.id,
                    room_finish_id=room_finish.id,
                    room_no="110",
                    room_name="OFFICE",
                    category="FLOOR",
                    finish_code="VCT",
                    measurement_type=MeasurementType.FLOOR_AREA,
                    quantity=Decimal("10.00"),
                    unit="m2",
                    status=ReviewStatus.CONFIRMED,
                ),
                Measurement(
                    project_id=project.id,
                    room_finish_id=room_finish.id,
                    room_no="110",
                    room_name="OFFICE",
                    category="WALL",
                    finish_code="GWB",
                    measurement_type=MeasurementType.WALL_AREA,
                    unit="m2",
                    status=ReviewStatus.NEEDS_REVIEW,
                ),
                Measurement(
                    project_id=project.id,
                    room_finish_id=room_finish.id,
                    room_no="110",
                    room_name="OFFICE",
                    category="BASE",
                    finish_code="RB",
                    measurement_type=MeasurementType.PERIMETER_LENGTH,
                    unit="m",
                    status=ReviewStatus.REJECTED,
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
        with TestClient(app) as client:
            response = client.get(f"/drawing-files/{drawing_file_id}/room-status")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    room = response.json()["rooms"][0]
    assert room["room_no"] == "110"
    assert room["total_count"] == 2
    assert room["quantity_count"] == 1
    assert room["confirmed_count"] == 1
    assert room["needs_review_count"] == 1
    assert room["missing_quantity_count"] == 1
