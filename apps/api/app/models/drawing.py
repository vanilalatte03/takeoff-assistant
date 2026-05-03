from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.enums import DrawingSheetRole, ReviewStatus
from app.models.project import utc_now


class DrawingFile(Base):
    __tablename__ = "drawing_files"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    page_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )

    project: Mapped["Project"] = relationship(back_populates="drawing_files")
    sheets: Mapped[list["DrawingSheet"]] = relationship(
        back_populates="drawing_file",
        cascade="all, delete-orphan",
    )


class DrawingSheet(Base):
    __tablename__ = "drawing_sheets"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    drawing_file_id: Mapped[int] = mapped_column(
        ForeignKey("drawing_files.id"),
        nullable=False,
        index=True,
    )
    page_index: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    sheet_no: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    sheet_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role: Mapped[DrawingSheetRole] = mapped_column(
        Enum(DrawingSheetRole, native_enum=False, length=64),
        default=DrawingSheetRole.UNKNOWN,
        nullable=False,
        index=True,
    )
    text_content: Mapped[str] = mapped_column(Text, default="", nullable=False)
    sheet_detection_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[ReviewStatus] = mapped_column(
        Enum(ReviewStatus, native_enum=False, length=32),
        default=ReviewStatus.DRAFT,
        nullable=False,
    )

    drawing_file: Mapped[DrawingFile] = relationship(back_populates="sheets")
    room_finishes: Mapped[list["RoomFinish"]] = relationship(back_populates="drawing_sheet")
