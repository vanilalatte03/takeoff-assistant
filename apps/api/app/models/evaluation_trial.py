from sqlalchemy import ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column
from app.db.session import Base


class EvaluationTrial(Base):
    __tablename__ = 'evaluation_trials'
    id: Mapped[int] = mapped_column(primary_key=True)
    drawing_file_id: Mapped[int] = mapped_column(ForeignKey('drawing_files.id'), index=True)
    data: Mapped[dict] = mapped_column(JSON)
