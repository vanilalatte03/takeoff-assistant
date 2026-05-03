from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.init_db import init_db
from app.db.session import get_db
from app.main import app
from app.models import DrawingFile, DrawingSheet, DrawingSheetRole, Project
from app.services.sheet_search import filter_sheets_by_keyword, filter_sheets_by_sheet_no


@pytest.fixture()
def client_with_db(tmp_path) -> Generator[tuple[TestClient, sessionmaker[Session], int], None, None]:
    database_url = f"sqlite:///{(tmp_path / 'sheet_search_test.db').as_posix()}"
    engine = create_engine(
        database_url,
        connect_args={"check_same_thread": False},
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    init_db(engine)

    with TestingSessionLocal() as session:
        project = Project(name="Sheet Search Project")
        session.add(project)
        session.flush()
        drawing_file = DrawingFile(
            project_id=project.id,
            original_filename="sample.pdf",
            stored_path="data/uploads/sample.pdf",
            page_count=5,
        )
        session.add(drawing_file)
        session.flush()
        session.add_all(
            [
                DrawingSheet(
                    drawing_file_id=drawing_file.id,
                    page_index=0,
                    sheet_no="AE101",
                    sheet_title="NEW FLOOR PLAN",
                    role=DrawingSheetRole.FLOOR_PLAN,
                    text_content="Room 110 Office floor finish VCT base RB",
                    sheet_detection_confidence=0.95,
                ),
                DrawingSheet(
                    drawing_file_id=drawing_file.id,
                    page_index=1,
                    sheet_no="AE401",
                    sheet_title="INTR / EXT FINISH SCHEDULE",
                    role=DrawingSheetRole.FINISH_SCHEDULE,
                    text_content="RM NOS ROOM NAMES FLOOR BASE WALL CEILING Room No 110 VCT GWB ACT",
                    sheet_detection_confidence=0.95,
                ),
                DrawingSheet(
                    drawing_file_id=drawing_file.id,
                    page_index=2,
                    sheet_no="AE402",
                    sheet_title="INTR / EXT FINISH SCHEDULE",
                    role=DrawingSheetRole.FINISH_SCHEDULE,
                    text_content="Room 210 LVT PT ACT",
                    sheet_detection_confidence=0.95,
                ),
                DrawingSheet(
                    drawing_file_id=drawing_file.id,
                    page_index=3,
                    sheet_no="AE103",
                    sheet_title="PARTITION WALL PLAN",
                    role=DrawingSheetRole.PARTITION_PLAN,
                    text_content="GWB partition layout and wall tags",
                    sheet_detection_confidence=0.8,
                ),
                DrawingSheet(
                    drawing_file_id=drawing_file.id,
                    page_index=4,
                    sheet_no="AE405",
                    sheet_title="DOOR SCHEDULE",
                    role=DrawingSheetRole.DOOR_SCHEDULE,
                    text_content="Door hardware schedule",
                    sheet_detection_confidence=0.8,
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


def test_filter_sheets_by_keyword_matches_room_no_tokens() -> None:
    sheets = [
        DrawingSheet(
            drawing_file_id=1,
            page_index=0,
            sheet_no="AE401",
            sheet_title="INTR / EXT FINISH SCHEDULE",
            text_content="RM NOS ROOM NAMES ROOM NO 110 VCT",
        )
    ]

    assert filter_sheets_by_keyword(sheets, "Room 110") == sheets
    assert filter_sheets_by_keyword(sheets, "RM 110") == sheets
    assert filter_sheets_by_keyword(sheets, "110") == sheets


def test_filter_sheets_by_sheet_no_matches_exact_normalized_sheet_number() -> None:
    sheets = [
        DrawingSheet(drawing_file_id=1, page_index=0, sheet_no="AE101"),
        DrawingSheet(drawing_file_id=1, page_index=1, sheet_no="AE401"),
    ]

    assert filter_sheets_by_sheet_no(sheets, "AE101") == [sheets[0]]


def test_search_by_sheet_no(client_with_db) -> None:
    client, _, drawing_file_id = client_with_db

    response = client.get(f"/drawing-files/{drawing_file_id}/sheets/search", params={"sheet_no": "AE101"})

    assert response.status_code == 200
    payload = response.json()
    assert [result["sheet_no"] for result in payload["results"]] == ["AE101"]
    assert payload["results"][0] == {
        "page_index": 0,
        "sheet_no": "AE101",
        "sheet_title": "NEW FLOOR PLAN",
        "sheet_role": "FLOOR_PLAN",
        "confidence": 0.95,
    }


def test_search_by_sheet_title(client_with_db) -> None:
    client, _, drawing_file_id = client_with_db

    response = client.get(
        f"/drawing-files/{drawing_file_id}/sheets/search",
        params={"query": "finish schedule"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert [result["sheet_no"] for result in payload["results"]] == ["AE401", "AE402"]


def test_search_by_sheet_role_filter(client_with_db) -> None:
    client, _, drawing_file_id = client_with_db

    response = client.get(
        f"/drawing-files/{drawing_file_id}/sheets/search",
        params={"sheet_role": "FINISH_SCHEDULE"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert [result["sheet_no"] for result in payload["results"]] == ["AE401", "AE402"]
    assert all(result["sheet_role"] == "FINISH_SCHEDULE" for result in payload["results"])


def test_search_text_content_by_room_no_and_finish_codes(client_with_db) -> None:
    client, _, drawing_file_id = client_with_db

    room_response = client.get(
        f"/drawing-files/{drawing_file_id}/sheets/search",
        params={"keyword": "Room 110"},
    )
    rm_response = client.get(
        f"/drawing-files/{drawing_file_id}/sheets/search",
        params={"keyword": "RM 110"},
    )
    room_no_response = client.get(
        f"/drawing-files/{drawing_file_id}/sheets/search",
        params={"keyword": "110"},
    )
    vct_response = client.get(
        f"/drawing-files/{drawing_file_id}/sheets/search",
        params={"keyword": "VCT"},
    )
    gwb_response = client.get(
        f"/drawing-files/{drawing_file_id}/sheets/search",
        params={"keyword": "GWB"},
    )

    assert room_response.status_code == 200
    assert [result["sheet_no"] for result in room_response.json()["results"]] == ["AE101", "AE401"]
    assert rm_response.status_code == 200
    assert [result["sheet_no"] for result in rm_response.json()["results"]] == ["AE101", "AE401"]
    assert room_no_response.status_code == 200
    assert [result["sheet_no"] for result in room_no_response.json()["results"]] == ["AE101", "AE401"]
    assert vct_response.status_code == 200
    assert [result["sheet_no"] for result in vct_response.json()["results"]] == ["AE101", "AE401"]
    assert gwb_response.status_code == 200
    assert [result["sheet_no"] for result in gwb_response.json()["results"]] == ["AE401", "AE103"]


def test_search_combines_keyword_and_role_filter(client_with_db) -> None:
    client, _, drawing_file_id = client_with_db

    response = client.get(
        f"/drawing-files/{drawing_file_id}/sheets/search",
        params={"keyword": "GWB", "sheet_role": "FINISH_SCHEDULE"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert [result["sheet_no"] for result in payload["results"]] == ["AE401"]


def test_legacy_comma_query_uses_first_term_instead_of_overbroad_matching(client_with_db) -> None:
    client, _, drawing_file_id = client_with_db

    response = client.get(
        f"/drawing-files/{drawing_file_id}/sheets/search",
        params={"query": "AE101, Room 110, VCT, GWB"},
    )

    assert response.status_code == 200
    assert [result["sheet_no"] for result in response.json()["results"]] == ["AE101"]


def test_search_returns_empty_results_when_no_match(client_with_db) -> None:
    client, _, drawing_file_id = client_with_db

    response = client.get(
        f"/drawing-files/{drawing_file_id}/sheets/search",
        params={"query": "not-present"},
    )

    assert response.status_code == 200
    assert response.json()["results"] == []


def test_search_requires_existing_drawing_file(client_with_db) -> None:
    client, _, _ = client_with_db

    response = client.get("/drawing-files/999/sheets/search", params={"query": "AE101"})

    assert response.status_code == 404
    assert response.json()["detail"] == "Drawing file not found."
