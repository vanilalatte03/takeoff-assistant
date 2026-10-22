from __future__ import annotations

from sqlalchemy import Enum, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.enums import ReviewStatus


class RoomFinish(Base):
    __tablename__ = "room_finishes"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    drawing_file_id: Mapped[int | None] = mapped_column(ForeignKey("drawing_files.id"), nullable=True, index=True)
    drawing_sheet_id: Mapped[int | None] = mapped_column(
        ForeignKey("drawing_sheets.id"),
        nullable=True,
        index=True,
    )
    room_no: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    room_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    floor_material: Mapped[str | None] = mapped_column(String(128), nullable=True)
    floor_finish: Mapped[str | None] = mapped_column(String(128), nullable=True)
    base_material: Mapped[str | None] = mapped_column(String(128), nullable=True)
    base_finish: Mapped[str | None] = mapped_column(String(128), nullable=True)
    wall_material: Mapped[str | None] = mapped_column(String(128), nullable=True)
    wall_finish: Mapped[str | None] = mapped_column(String(128), nullable=True)
    ceiling_material: Mapped[str | None] = mapped_column(String(128), nullable=True)
    ceiling_finish: Mapped[str | None] = mapped_column(String(128), nullable=True)
    height: Mapped[str | None] = mapped_column(String(64), nullable=True)
    remarks: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_sheet_no: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[ReviewStatus] = mapped_column(
        Enum(ReviewStatus, native_enum=False, length=32),
        default=ReviewStatus.NEEDS_REVIEW,
        nullable=False,
    )

    project: Mapped["Project"] = relationship(back_populates="room_finishes")
    drawing_sheet: Mapped["DrawingSheet | None"] = relationship(back_populates="room_finishes")
    measurements: Mapped[list["Measurement"]] = relationship(back_populates="room_finish")
