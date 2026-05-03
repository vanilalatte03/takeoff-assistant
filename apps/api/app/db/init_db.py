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
