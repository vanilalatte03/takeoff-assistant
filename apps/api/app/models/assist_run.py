from datetime import datetime, timezone
from sqlalchemy import DateTime, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.db.session import Base


class AssistRun(Base):
    __tablename__ = "assist_runs"
    id: Mapped[int] = mapped_column(primary_key=True)
    drawing_file_id: Mapped[int] = mapped_column(ForeignKey("drawing_files.id"), index=True)
    request: Mapped[str] = mapped_column(Text)
    mode: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(30))
    result: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
