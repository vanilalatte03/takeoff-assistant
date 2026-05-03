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
from app.models import Measurement, MeasurementType, Project, ReviewStatus
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
