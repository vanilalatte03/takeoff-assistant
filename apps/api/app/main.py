from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI

from app.api.routes.drawing_files import router as drawing_files_router
from app.api.routes.measurements import router as measurements_router
from app.api.routes.projects import router as projects_router
from app.api.routes.room_finishes import router as room_finishes_router
from app.api.routes.assist import router as assist_router
from app.api.routes.review_evidence import router as review_evidence_router
from app.api.routes.workflow import router as workflow_router
from app.core.config import settings
from app.db.init_db import init_db


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    init_db()
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
)

app.include_router(drawing_files_router)
app.include_router(measurements_router)
app.include_router(projects_router)
app.include_router(room_finishes_router)
app.include_router(assist_router)
app.include_router(review_evidence_router)
app.include_router(workflow_router)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {
        "status": "ok",
        "service": settings.app_name,
        "version": settings.app_version,
    }
