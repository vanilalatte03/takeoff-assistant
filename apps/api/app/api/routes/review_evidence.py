from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models import DrawingSheet, Measurement
from app.services.review_evidence import build_review_evidence

router = APIRouter(tags=['review'])


@router.get('/measurements/{measurement_id}/evidence')
def review(measurement_id: int, db: Session = Depends(get_db)):
    measurement = db.get(Measurement,measurement_id)
    if measurement is None:
        raise HTTPException(404,'Measurement not found.')
    finish = measurement.room_finish
    owner = finish.drawing_sheet.drawing_file if finish and finish.drawing_sheet else None
    sheets = db.query(DrawingSheet).filter(DrawingSheet.drawing_file_id==owner.id).all() if owner else []
    return build_review_evidence(measurement,owner,sheets)
