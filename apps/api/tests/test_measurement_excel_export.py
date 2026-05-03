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


@pytest.fixture()
def client_with_export_data(tmp_path) -> Generator[tuple[TestClient, int], None, None]:
    database_url = f"sqlite:///{(tmp_path / 'measurement_export_test.db').as_posix()}"
    engine = create_engine(
        database_url,
        connect_args={"check_same_thread": False},
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    init_db(engine)

    with TestingSessionLocal() as session:
        project = Project(name="Export Project")
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

        sheet = DrawingSheet(
            drawing_file_id=drawing_file.id,
            page_index=0,
            sheet_no="AE401",
            sheet_title="INTR / EXT FINISH SCHEDULE",
        )
        session.add(sheet)
        session.flush()

        room_110 = RoomFinish(
            project_id=project.id,
            drawing_sheet_id=sheet.id,
            room_no="110",
            room_name="OFFICE",
            source_sheet_no="AE401",
            status=ReviewStatus.NEEDS_REVIEW,
        )
        room_111 = RoomFinish(
            project_id=project.id,
            drawing_sheet_id=sheet.id,
            room_no="111",
            room_name="STORAGE",
            source_sheet_no="AE401",
            status=ReviewStatus.NEEDS_REVIEW,
        )
        session.add_all([room_110, room_111])
        session.flush()

        session.add_all(
            [
                Measurement(
                    project_id=project.id,
                    room_finish_id=room_110.id,
                    room_no="110",
                    room_name="OFFICE",
                    category="FLOOR",
                    finish_code="VCT",
                    measurement_type=MeasurementType.FLOOR_AREA,
                    formula="5 * 2 - 0.25",
                    quantity=Decimal("9.75"),
                    unit="m2",
                    source_sheets="AE401, AE101",
                    status=ReviewStatus.DRAFT,
                    memo="checked by user",
                ),
                Measurement(
                    project_id=project.id,
                    room_finish_id=room_111.id,
                    room_no="111",
                    room_name="STORAGE",
                    category="FLOOR",
                    finish_code="VCT",
                    measurement_type=MeasurementType.FLOOR_AREA,
                    formula="3 * 2",
                    quantity=Decimal("6.00"),
                    unit="m2",
                    source_sheets="AE402",
                    status=ReviewStatus.CONFIRMED,
                ),
                Measurement(
                    project_id=project.id,
                    room_finish_id=room_110.id,
                    room_no="110",
                    room_name="OFFICE",
                    category="WALL",
                    finish_code="GWB",
                    measurement_type=MeasurementType.WALL_AREA,
                    formula=None,
                    quantity=None,
                    unit="m2",
                    source_sheets="AE401",
                    status=ReviewStatus.NEEDS_REVIEW,
                    memo="needs manual measurement",
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
        yield TestClient(app), drawing_file_id
    finally:
        app.dependency_overrides.clear()


def test_measurement_export_contains_summary_and_details(client_with_export_data) -> None:
    client, drawing_file_id = client_with_export_data

    response = client.get(f"/drawing-files/{drawing_file_id}/measurements/export")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    assert "finish_takeoff_drawing_file_" in response.headers["content-disposition"]

    workbook = load_workbook(BytesIO(response.content), data_only=True)
    assert workbook.sheetnames == ["Summary", "Details"]

    summary_sheet = workbook["Summary"]
    assert [summary_sheet.cell(1, column).value for column in range(1, 6)] == [
        "Category",
        "Code",
        "Unit",
        "Total Quantity",
        "Source Sheets",
    ]
    assert [summary_sheet.cell(2, column).value for column in range(1, 4)] == ["FLOOR", "VCT", "m2"]
    assert Decimal(str(summary_sheet["D2"].value)) == Decimal("15.75")
    assert summary_sheet["E2"].value == "AE401, AE101, AE402"
    assert [summary_sheet.cell(3, column).value for column in range(1, 4)] == ["WALL", "GWB", "m2"]
    assert Decimal(str(summary_sheet["D3"].value)) == Decimal("0")
    assert summary_sheet["E3"].value == "AE401"
    assert summary_sheet["D2"].number_format == "0.00"

    details_sheet = workbook["Details"]
    assert [details_sheet.cell(1, column).value for column in range(1, 12)] == [
        "Drawing No",
        "Room No",
        "Room Name",
        "Category",
        "Code",
        "Formula",
        "Quantity",
        "Unit",
        "Source Sheets",
        "Status",
        "Memo",
    ]
    assert [details_sheet.cell(2, column).value for column in range(1, 7)] == [
        "AE401",
        "110",
        "OFFICE",
        "FLOOR",
        "VCT",
        "5 * 2 - 0.25",
    ]
    assert Decimal(str(details_sheet["G2"].value)) == Decimal("9.75")
    assert [details_sheet.cell(2, column).value for column in range(8, 12)] == [
        "m2",
        "AE401, AE101",
        "DRAFT",
        "checked by user",
    ]
    assert details_sheet["G2"].number_format == "0.00"


def test_measurement_export_requires_existing_drawing_file(client_with_export_data) -> None:
    client, _ = client_with_export_data

    response = client.get("/drawing-files/999/measurements/export")

    assert response.status_code == 404
    assert response.json()["detail"] == "Drawing file not found."
