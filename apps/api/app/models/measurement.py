from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import JSON, DateTime, Enum, Float, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.enums import MeasurementType, ReviewStatus
from app.models.project import utc_now


class Measurement(Base):
    __tablename__ = "measurements"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    room_finish_id: Mapped[int | None] = mapped_column(
        ForeignKey("room_finishes.id"),
        nullable=True,
        index=True,
    )
    room_no: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    room_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    category: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    finish_code: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    measurement_type: Mapped[MeasurementType] = mapped_column(
        Enum(MeasurementType, native_enum=False, length=64),
        nullable=False,
        index=True,
    )
    formula: Mapped[str | None] = mapped_column(Text, nullable=True)
    quantity: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    unit: Mapped[str | None] = mapped_column(String(16), nullable=True)
    source_sheets: Mapped[str] = mapped_column(String(512), default="", nullable=False)
    status: Mapped[ReviewStatus] = mapped_column(
        Enum(ReviewStatus, native_enum=False, length=32),
        default=ReviewStatus.DRAFT,
        nullable=False,
    )
    memo: Mapped[str | None] = mapped_column(Text, nullable=True)
    coordinates_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    deductions_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    measurement_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )

    project: Mapped["Project"] = relationship(back_populates="measurements")
    room_finish: Mapped["RoomFinish | None"] = relationship(back_populates="measurements")
