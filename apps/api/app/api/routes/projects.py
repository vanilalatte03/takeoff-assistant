from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import Project
from app.schemas import ProjectCreate, ProjectRead


router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("", response_model=list[ProjectRead])
def list_projects(db: Session = Depends(get_db)) -> list[Project]:
    return db.query(Project).order_by(Project.created_at, Project.id).all()


@router.post("", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
def create_project(payload: ProjectCreate, db: Session = Depends(get_db)) -> Project:
    name = payload.name.strip()
    if not name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Project name is required.",
        )

    project = Project(name=name, description=payload.description)
    db.add(project)
    db.commit()
    db.refresh(project)
    return project
