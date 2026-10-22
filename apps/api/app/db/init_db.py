from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app import models  # noqa: F401
from app.core.config import settings
from app.db.session import Base, engine
from app.models import Project


def init_db(database_engine: Engine = engine) -> None:
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.uploads_dir.mkdir(parents=True, exist_ok=True)
    settings.rendered_pages_dir.mkdir(parents=True, exist_ok=True)
    settings.exports_dir.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=database_engine)
    _migrate_room_finish_file_ownership(database_engine)

    with Session(database_engine) as session:
        if session.get(Project, 1) is None:
            session.add(
                Project(
                    id=1,
                    name="Default Project",
                    description="Default local project for MVP uploads.",
                )
            )
            session.commit()


def _migrate_room_finish_file_ownership(database_engine: Engine) -> None:
    """Add a nullable owner; only a project-consistent sheet proves legacy ownership.

    Unassigned manual legacy rows are deliberately retained without guessing which
    PDF they belong to. File-scoped APIs exclude them until explicitly reconciled.
    """
    columns = {column["name"] for column in inspect(database_engine).get_columns("room_finishes")}
    with database_engine.begin() as connection:
        if "drawing_file_id" not in columns:
            if database_engine.dialect.name != "sqlite":
                raise RuntimeError("Legacy database migration is supported for SQLite only.")
            connection.execute(text("ALTER TABLE room_finishes ADD COLUMN drawing_file_id INTEGER REFERENCES drawing_files(id)"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS ix_room_finishes_drawing_file_id ON room_finishes (drawing_file_id)"))
        connection.execute(text("""
            UPDATE room_finishes SET drawing_file_id = (
                SELECT drawing_sheets.drawing_file_id FROM drawing_sheets
                JOIN drawing_files ON drawing_files.id = drawing_sheets.drawing_file_id
                WHERE drawing_sheets.id = room_finishes.drawing_sheet_id
                AND drawing_files.project_id = room_finishes.project_id
            ) WHERE drawing_file_id IS NULL AND drawing_sheet_id IS NOT NULL
        """))
