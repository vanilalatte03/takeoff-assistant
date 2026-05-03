from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )

    drawing_files: Mapped[list["DrawingFile"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
    )
    room_finishes: Mapped[list["RoomFinish"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
    )
    measurements: Mapped[list["Measurement"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
    )
