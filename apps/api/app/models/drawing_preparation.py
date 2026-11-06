from sqlalchemy import ForeignKey, Integer, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class DrawingPreparation(Base):
    """Additive checkpoints; never inferred from review status or quantity."""

    __tablename__ = "drawing_preparations"
    drawing_file_id: Mapped[int] = mapped_column(ForeignKey("drawing_files.id"), primary_key=True)
    completed: Mapped[int] = mapped_column(Integer, default=0)
    owned_sheet_ids: Mapped[list] = mapped_column(JSON, default=list)
    warnings: Mapped[list] = mapped_column(JSON, default=list)
