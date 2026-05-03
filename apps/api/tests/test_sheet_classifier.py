from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.init_db import init_db
from app.db.session import get_db
from app.main import app
from app.models import DrawingFile, DrawingSheet, DrawingSheetRole, Project
from app.services.sheet_classifier import classify_and_apply_sheet_roles, classify_sheet_role


@pytest.fixture()
def client_with_db(tmp_path) -> Generator[tuple[TestClient, sessionmaker[Session]], None, None]:
    database_url = f"sqlite:///{(tmp_path / 'sheet_classifier_test.db').as_posix()}"
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


@pytest.mark.parametrize(
    ("sheet_title", "expected_role"),
    [
        ("INTR / EXT FINISH SCHEDULE", DrawingSheetRole.FINISH_SCHEDULE),
        ("EXTERIOR & INTERIOR FINISH SCHEDULE", DrawingSheetRole.FINISH_SCHEDULE),
        ("NEW FLOOR PLAN", DrawingSheetRole.FLOOR_PLAN),
        ("ENLARGED FLOOR PLAN", DrawingSheetRole.ENLARGED_FLOOR_PLAN),
        ("REFLECTED CEILING PLAN", DrawingSheetRole.CEILING_PLAN),
        ("PARTITION WALL PLAN", DrawingSheetRole.PARTITION_PLAN),
        ("FLOOR PARTITION TYPE KEY PLAN", DrawingSheetRole.PARTITION_PLAN),
        ("PARTITION WALL DETAILS", DrawingSheetRole.PARTITION_DETAIL),
        ("DOOR / WINDOW SCHEDULE", DrawingSheetRole.DOOR_SCHEDULE),
        ("DOOR SCHEDULE", DrawingSheetRole.DOOR_SCHEDULE),
        ("WINDOW SCHEDULE", DrawingSheetRole.WINDOW_SCHEDULE),
        ("LOUVER SCHEDULE", DrawingSheetRole.WINDOW_SCHEDULE),
        ("MILLWORK DETAILS", DrawingSheetRole.DETAIL),
        ("COVER SHEET", DrawingSheetRole.UNKNOWN),
    ],
)
def test_classify_sheet_role_from_sheet_title(sheet_title, expected_role) -> None:
    assert classify_sheet_role(sheet_title) == expected_role


def test_classify_sheet_role_falls_back_to_text_content_when_title_missing() -> None:
    role = classify_sheet_role(None, "PROJECT NAME\nAE101 NEW FLOOR PLAN\nDRAWING NUMBER")

    assert role == DrawingSheetRole.FLOOR_PLAN


def test_classify_sheet_role_scans_title_like_lines_in_text_content() -> None:
    assert (
        classify_sheet_role(
            None,
            """
            PROJECT TITLE
            AE401
            INTR / EXT FINISH SCHEDULE
            SHEET NUMBER
            """,
        )
        == DrawingSheetRole.FINISH_SCHEDULE
    )
    assert (
        classify_sheet_role(
            None,
            """
            TITLE BLOCK
            REFLECTED CEILING PLAN
            A-201
            """,
        )
        == DrawingSheetRole.CEILING_PLAN
    )


def test_classify_sheet_role_does_not_use_sheet_number() -> None:
    sheets = [
        DrawingSheet(
            drawing_file_id=1,
            page_index=0,
            sheet_no="AE601",
            sheet_title="NEW FLOOR PLAN",
            text_content="AE601 NEW FLOOR PLAN",
        ),
        DrawingSheet(
            drawing_file_id=1,
            page_index=1,
            sheet_no="AE101",
            sheet_title="INTR / EXT FINISH SCHEDULE",
            text_content="AE101 INTR / EXT FINISH SCHEDULE",
        ),
    ]

    classified = classify_and_apply_sheet_roles(sheets)

    assert classified[0].role == DrawingSheetRole.FLOOR_PLAN
    assert classified[1].role == DrawingSheetRole.FINISH_SCHEDULE


def test_classify_sheet_role_supports_multiple_sheets_with_same_role() -> None:
    sheets = [
        DrawingSheet(
            drawing_file_id=1,
            page_index=0,
            sheet_title="INTR / EXT FINISH SCHEDULE",
        ),
        DrawingSheet(
            drawing_file_id=1,
            page_index=1,
            sheet_title="EXTERIOR & INTERIOR FINISH SCHEDULE",
        ),
    ]

    classified = classify_and_apply_sheet_roles(sheets)

    assert [sheet.role for sheet in classified] == [
        DrawingSheetRole.FINISH_SCHEDULE,
        DrawingSheetRole.FINISH_SCHEDULE,
    ]


def test_classify_sheet_role_ignores_index_page_text_without_title() -> None:
    role = classify_sheet_role(
        None,
        """
        INDEX OF DRAWINGS
        AE401 INTR / EXT FINISH SCHEDULE
        AE101 NEW FLOOR PLAN
        """,
    )

    assert role == DrawingSheetRole.UNKNOWN


def test_classify_endpoint_updates_sheet_roles(client_with_db) -> None:
    client, session_factory = client_with_db
    with session_factory() as session:
        project = Project(name="Sheet Classifier Project")
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
                    sheet_no="AE401",
                    sheet_title="INTR / EXT FINISH SCHEDULE",
                ),
                DrawingSheet(
                    drawing_file_id=drawing_file.id,
                    page_index=1,
                    sheet_no="AE402",
                    sheet_title="INTR / EXT FINISH SCHEDULE",
                ),
                DrawingSheet(
                    drawing_file_id=drawing_file.id,
                    page_index=2,
                    sheet_no="AE101",
                    sheet_title="NEW FLOOR PLAN",
                ),
                DrawingSheet(
                    drawing_file_id=drawing_file.id,
                    page_index=3,
                    sheet_no="AE102",
                    sheet_title="PARTITION WALL DETAILS",
                ),
            ]
        )
        session.commit()
        drawing_file_id = drawing_file.id

    response = client.post(f"/drawing-files/{drawing_file_id}/sheets/classify")

    assert response.status_code == 200
    payload = response.json()
    assert payload["drawing_file_id"] == drawing_file_id
    assert [sheet["role"] for sheet in payload["sheets"]] == [
        DrawingSheetRole.FINISH_SCHEDULE,
        DrawingSheetRole.FINISH_SCHEDULE,
        DrawingSheetRole.FLOOR_PLAN,
        DrawingSheetRole.PARTITION_DETAIL,
    ]

    with session_factory() as session:
        roles = [
            sheet.role
            for sheet in session.query(DrawingSheet)
            .filter(DrawingSheet.drawing_file_id == drawing_file_id)
            .order_by(DrawingSheet.page_index)
            .all()
        ]
        assert roles == [
            DrawingSheetRole.FINISH_SCHEDULE,
            DrawingSheetRole.FINISH_SCHEDULE,
            DrawingSheetRole.FLOOR_PLAN,
            DrawingSheetRole.PARTITION_DETAIL,
        ]


def test_classify_endpoint_requires_existing_drawing_file(client_with_db) -> None:
    client, _ = client_with_db

    response = client.post("/drawing-files/999/sheets/classify")

    assert response.status_code == 404
    assert response.json()["detail"] == "Drawing file not found."
