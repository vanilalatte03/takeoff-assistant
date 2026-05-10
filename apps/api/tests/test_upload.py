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
from app.models import DrawingFile, Project


@pytest.fixture()
def client_with_db(tmp_path, monkeypatch) -> Generator[tuple[TestClient, sessionmaker[Session]], None, None]:
    database_url = f"sqlite:///{(tmp_path / 'upload_test.db').as_posix()}"
    engine = create_engine(
        database_url,
        connect_args={"check_same_thread": False},
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    uploads_dir = tmp_path / "uploads"
    monkeypatch.setattr(settings, "uploads_dir", uploads_dir)
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


def _make_pdf(page_count: int = 2) -> bytes:
    document = fitz.open()
    for _ in range(page_count):
        document.new_page()

    buffer = BytesIO()
    document.save(buffer)
    document.close()
    return buffer.getvalue()


def test_upload_pdf_stores_file_and_creates_drawing_file_record(client_with_db) -> None:
    client, session_factory = client_with_db
    with session_factory() as session:
        project = Project(name="Upload Test Project")
        session.add(project)
        session.commit()
        session.refresh(project)
        project_id = project.id

    response = client.post(
        "/drawing-files/upload",
        data={"project_id": str(project_id)},
        files={"file": ("sample.pdf", _make_pdf(3), "application/pdf")},
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["project_id"] == project_id
    assert payload["original_filename"] == "sample.pdf"
    assert payload["page_count"] == 3
    assert payload["created_at"]
    assert payload["stored_path"].endswith(".pdf")

    stored_path = payload["stored_path"]
    assert "uploads" in stored_path
    assert Path(stored_path).is_file()
    assert (settings.uploads_dir / str(project_id)).exists()

    with session_factory() as session:
        drawing_file = session.get(DrawingFile, payload["id"])
        assert drawing_file is not None
        assert drawing_file.original_filename == "sample.pdf"
        assert drawing_file.page_count == 3
        assert drawing_file.created_at is not None
        assert drawing_file.stored_path == stored_path


def test_upload_rejects_non_pdf_extension(client_with_db) -> None:
    client, session_factory = client_with_db
    with session_factory() as session:
        project = Project(name="Upload Test Project")
        session.add(project)
        session.commit()
        session.refresh(project)
        project_id = project.id

    response = client.post(
        "/drawing-files/upload",
        data={"project_id": str(project_id)},
        files={"file": ("notes.txt", b"not a pdf", "text/plain")},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Only PDF files are supported."


def test_upload_rejects_invalid_pdf_content(client_with_db) -> None:
    client, session_factory = client_with_db
    with session_factory() as session:
        project = Project(name="Upload Test Project")
        session.add(project)
        session.commit()
        session.refresh(project)
        project_id = project.id

    response = client.post(
        "/drawing-files/upload",
        data={"project_id": str(project_id)},
        files={"file": ("broken.pdf", b"not a real pdf", "application/pdf")},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Uploaded file is not a valid PDF."
    assert not list(settings.uploads_dir.rglob("*broken.pdf"))


def test_upload_requires_existing_project(client_with_db) -> None:
    client, _ = client_with_db

    response = client.post(
        "/drawing-files/upload",
        data={"project_id": "999"},
        files={"file": ("sample.pdf", _make_pdf(), "application/pdf")},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Project not found."


def test_project_list_and_create_api_support_upload_selection(client_with_db) -> None:
    client, _ = client_with_db

    create_response = client.post(
        "/projects",
        json={
            "name": "New Upload Project",
            "description": "Created from upload screen",
        },
    )
    assert create_response.status_code == 201
    created = create_response.json()
    assert created["name"] == "New Upload Project"
    assert created["description"] == "Created from upload screen"

    list_response = client.get("/projects")

    assert list_response.status_code == 200
    assert [project["name"] for project in list_response.json()] == ["Default Project", "New Upload Project"]
