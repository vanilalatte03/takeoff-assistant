from collections.abc import Generator
from io import BytesIO
from pathlib import Path

import fitz
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.db.init_db import init_db
from app.db.session import get_db
from app.main import app
from app.models import DrawingFile, DrawingSheet, Project, ReviewStatus


@pytest.fixture()
def client_with_db(tmp_path, monkeypatch) -> Generator[tuple[TestClient, sessionmaker[Session]], None, None]:
    database_url = f"sqlite:///{(tmp_path / 'page_processing_test.db').as_posix()}"
    engine = create_engine(
        database_url,
        connect_args={"check_same_thread": False},
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    monkeypatch.setattr(settings, "uploads_dir", tmp_path / "uploads")
    monkeypatch.setattr(settings, "rendered_pages_dir", tmp_path / "rendered")
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


def _make_text_and_blank_pdf() -> bytes:
    document = fitz.open()
    text_page = document.new_page()
    text_page.insert_text((72, 72), "AE101 NEW FLOOR PLAN")
    document.new_page()

    buffer = BytesIO()
    document.save(buffer)
    document.close()
    return buffer.getvalue()


def _create_project(session_factory: sessionmaker[Session]) -> int:
    with session_factory() as session:
        project = Project(name="Page Processing Test Project")
        session.add(project)
        session.commit()
        session.refresh(project)
        return project.id


def _upload_pdf(client: TestClient, project_id: int) -> int:
    response = client.post(
        "/drawing-files/upload",
        data={"project_id": str(project_id)},
        files={"file": ("sample.pdf", _make_text_and_blank_pdf(), "application/pdf")},
    )
    assert response.status_code == 201
    return int(response.json()["id"])


def test_process_pages_extracts_text_and_renders_images(client_with_db) -> None:
    client, session_factory = client_with_db
    project_id = _create_project(session_factory)
    drawing_file_id = _upload_pdf(client, project_id)

    response = client.post(f"/drawing-files/{drawing_file_id}/pages/process")

    assert response.status_code == 200
    payload = response.json()
    assert payload["drawing_file_id"] == drawing_file_id
    assert payload["page_count"] == 2
    assert len(payload["sheets"]) == 2
    assert payload["sheets"][0]["page_index"] == 0
    assert "AE101 NEW FLOOR PLAN" in payload["sheets"][0]["text_content"]
    assert payload["sheets"][0]["status"] == ReviewStatus.DRAFT
    assert payload["sheets"][1]["page_index"] == 1
    assert payload["sheets"][1]["text_content"] == ""
    assert payload["sheets"][1]["status"] == ReviewStatus.NEEDS_REVIEW

    first_image = settings.rendered_pages_dir / str(drawing_file_id) / "page_0.png"
    second_image = settings.rendered_pages_dir / str(drawing_file_id) / "page_1.png"
    assert first_image.is_file()
    assert second_image.is_file()

    with session_factory() as session:
        drawing_file = session.get(DrawingFile, drawing_file_id)
        assert drawing_file is not None
        assert drawing_file.page_count == 2
        sheets = (
            session.query(DrawingSheet)
            .filter(DrawingSheet.drawing_file_id == drawing_file_id)
            .order_by(DrawingSheet.page_index)
            .all()
        )
        assert len(sheets) == 2
        assert "AE101 NEW FLOOR PLAN" in sheets[0].text_content
        assert sheets[0].status == ReviewStatus.DRAFT
        assert sheets[1].text_content == ""
        assert sheets[1].status == ReviewStatus.NEEDS_REVIEW


def test_page_image_endpoint_returns_rendered_png(client_with_db) -> None:
    client, session_factory = client_with_db
    project_id = _create_project(session_factory)
    drawing_file_id = _upload_pdf(client, project_id)
    process_response = client.post(f"/drawing-files/{drawing_file_id}/pages/process")
    assert process_response.status_code == 200

    response = client.get(f"/drawing-files/{drawing_file_id}/pages/0/image")

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert response.content.startswith(b"\x89PNG")


def test_processing_pages_is_idempotent(client_with_db) -> None:
    client, session_factory = client_with_db
    project_id = _create_project(session_factory)
    drawing_file_id = _upload_pdf(client, project_id)

    first_response = client.post(f"/drawing-files/{drawing_file_id}/pages/process")
    second_response = client.post(f"/drawing-files/{drawing_file_id}/pages/process")

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    with session_factory() as session:
        sheet_count = (
            session.query(DrawingSheet)
            .filter(DrawingSheet.drawing_file_id == drawing_file_id)
            .count()
        )
        assert sheet_count == 2


def test_page_image_endpoint_requires_existing_rendered_file(client_with_db) -> None:
    client, session_factory = client_with_db
    project_id = _create_project(session_factory)
    drawing_file_id = _upload_pdf(client, project_id)

    response = client.get(f"/drawing-files/{drawing_file_id}/pages/0/image")

    assert response.status_code == 404
    assert response.json()["detail"] == "Rendered page image not found."


def test_processing_rejects_missing_stored_pdf(client_with_db, tmp_path) -> None:
    client, session_factory = client_with_db
    with session_factory() as session:
        project = Project(name="Missing PDF Project")
        session.add(project)
        session.flush()
        drawing_file = DrawingFile(
            project_id=project.id,
            original_filename="missing.pdf",
            stored_path=str(Path(tmp_path) / "missing.pdf"),
            page_count=0,
        )
        session.add(drawing_file)
        session.commit()
        session.refresh(drawing_file)
        drawing_file_id = drawing_file.id

    response = client.post(f"/drawing-files/{drawing_file_id}/pages/process")

    assert response.status_code == 404
    assert response.json()["detail"] == "Stored PDF file not found."
