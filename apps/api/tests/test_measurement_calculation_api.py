from collections.abc import Generator
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.init_db import init_db
from app.db.session import get_db
from app.main import app
from app.models import DrawingFile, Measurement, MeasurementType, Project, ReviewStatus


@pytest.fixture()
def client_with_measurement(tmp_path) -> Generator[tuple[TestClient, sessionmaker[Session], int], None, None]:
    database_url = f"sqlite:///{(tmp_path / 'measurement_calculation_test.db').as_posix()}"
    engine = create_engine(
        database_url,
        connect_args={"check_same_thread": False},
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    init_db(engine)

    with TestingSessionLocal() as session:
        project = Project(name="Measurement Calculation Project")
        session.add(project)
        session.flush()
        drawing_file = DrawingFile(
            project_id=project.id,
            original_filename="sample.pdf",
            stored_path="data/uploads/sample.pdf",
            page_count=1,
        )
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
        session.add_all([drawing_file, measurement])
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


def test_calculate_measurement_api_saves_formula_quantity_unit_and_sources(client_with_measurement) -> None:
    client, session_factory, measurement_id = client_with_measurement

    response = client.post(
        f"/measurements/{measurement_id}/calculate",
        json={
            "calculation_type": "AREA_RECTANGLE",
            "width": "5",
            "height": "4",
            "source_sheets": "AE401, AE101",
            "deductions": [
                {
                    "label": "equipment",
                    "amount": "1.89",
                }
            ],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["formula"] == "5 * 4 - 1.89"
    assert Decimal(str(payload["quantity"])) == Decimal("18.11")
    assert payload["unit"] == "m2"
    assert payload["source_sheets"] == "AE401, AE101"
    assert payload["status"] == ReviewStatus.DRAFT
    assert payload["deductions_json"] == {
        "items": [
            {
                "label": "equipment",
                "formula": None,
                "amount": "1.89",
            }
        ]
    }

    with session_factory() as session:
        measurement = session.get(Measurement, measurement_id)
        assert measurement is not None
        assert measurement.formula == "5 * 4 - 1.89"
        assert measurement.quantity == Decimal("18.11")
        assert measurement.unit == "m2"
        assert measurement.source_sheets == "AE401, AE101"
        assert measurement.status == ReviewStatus.DRAFT


def test_calculate_measurement_api_reuses_existing_source_sheets_when_omitted(client_with_measurement) -> None:
    client, _, measurement_id = client_with_measurement

    response = client.post(
        f"/measurements/{measurement_id}/calculate",
        json={
            "calculation_type": "AREA_RECTANGLE",
            "width": "3",
            "height": "2",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["formula"] == "3 * 2"
    assert Decimal(str(payload["quantity"])) == Decimal("6.00")
    assert payload["unit"] == "m2"
    assert payload["source_sheets"] == "AE401"


def test_calculate_measurement_api_rejects_incompatible_calculation_type(client_with_measurement) -> None:
    client, _, measurement_id = client_with_measurement

    response = client.post(
        f"/measurements/{measurement_id}/calculate",
        json={
            "calculation_type": "PARTITION_AREA",
            "wall_length": "4.2",
            "wall_height": "2.7",
            "side_multiplier": "2",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == {
        "message": "PARTITION_AREA is not allowed for FLOOR_AREA.",
        "allowed_calculation_types": ["AREA_RECTANGLE", "CUSTOM"],
    }


def test_calculate_measurement_api_returns_400_for_missing_inputs(client_with_measurement) -> None:
    client, _, measurement_id = client_with_measurement

    response = client.post(
        f"/measurements/{measurement_id}/calculate",
        json={
            "calculation_type": "AREA_RECTANGLE",
            "height": "2.7",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "width is required."


def test_calculate_measurement_api_requires_existing_measurement(client_with_measurement) -> None:
    client, _, _ = client_with_measurement

    response = client.post(
        "/measurements/999/calculate",
        json={
            "calculation_type": "COUNT",
            "count": "1",
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Measurement not found."
