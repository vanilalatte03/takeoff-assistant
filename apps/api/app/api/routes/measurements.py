from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import CalculationType, DrawingFile, DrawingSheet, Measurement, MeasurementType, ReviewStatus, RoomFinish
from app.schemas import MeasurementCalculationInput, MeasurementGenerationResult, MeasurementRead, MeasurementUpdate
from app.services import (
    CalculationInput,
    DeductionInput,
    build_measurement_candidate,
    build_measurement_candidate_specs,
    build_measurements_workbook,
    candidate_key,
    calculate,
    existing_measurement_keys,
)


router = APIRouter(tags=["measurements"])


@router.post(
    "/drawing-files/{drawing_file_id}/measurements/generate",
    response_model=MeasurementGenerationResult,
)
def generate_measurement_candidates(
    drawing_file_id: int,
    db: Session = Depends(get_db),
) -> MeasurementGenerationResult:
    drawing_file = db.get(DrawingFile, drawing_file_id)
    if drawing_file is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Drawing file not found.",
        )

    room_finishes = _room_finishes_for_drawing_file(db, drawing_file)
    existing_keys = existing_measurement_keys(
        db.query(Measurement)
        .filter(
            Measurement.project_id == drawing_file.project_id,
            Measurement.room_finish_id.in_([row.id for row in room_finishes] or [0]),
        )
        .all()
    )

    created_measurements: list[Measurement] = []
    for room_finish in room_finishes:
        for spec in build_measurement_candidate_specs(room_finish):
            key = candidate_key(room_finish.id, spec)
            if key in existing_keys:
                continue
            measurement = build_measurement_candidate(room_finish, spec)
            db.add(measurement)
            created_measurements.append(measurement)
            existing_keys.add(key)

    db.commit()
    for measurement in created_measurements:
        db.refresh(measurement)

    return MeasurementGenerationResult(
        drawing_file_id=drawing_file.id,
        measurements=created_measurements,
    )


@router.get(
    "/drawing-files/{drawing_file_id}/measurements",
    response_model=list[MeasurementRead],
)
def list_measurements(
    drawing_file_id: int,
    db: Session = Depends(get_db),
) -> list[Measurement]:
    drawing_file = db.get(DrawingFile, drawing_file_id)
    if drawing_file is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Drawing file not found.",
        )

    return _measurements_for_drawing_file(db, drawing_file)


@router.get("/drawing-files/{drawing_file_id}/measurements/export")
def export_measurements(
    drawing_file_id: int,
    db: Session = Depends(get_db),
) -> StreamingResponse:
    drawing_file = db.get(DrawingFile, drawing_file_id)
    if drawing_file is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Drawing file not found.",
        )

    workbook_stream = build_measurements_workbook(_measurements_for_drawing_file(db, drawing_file))
    filename = f"finish_takeoff_drawing_file_{drawing_file.id}.xlsx"
    return StreamingResponse(
        workbook_stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/measurements/{measurement_id}/calculate", response_model=MeasurementRead)
def calculate_measurement(
    measurement_id: int,
    payload: MeasurementCalculationInput,
    db: Session = Depends(get_db),
) -> Measurement:
    measurement = db.get(Measurement, measurement_id)
    if measurement is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Measurement not found.",
        )

    allowed_calculation_types = _allowed_calculation_types(measurement.measurement_type)
    if payload.calculation_type not in allowed_calculation_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": f"{payload.calculation_type.value} is not allowed for {measurement.measurement_type.value}.",
                "allowed_calculation_types": [calculation_type.value for calculation_type in allowed_calculation_types],
            },
        )

    try:
        result = calculate(
            CalculationInput(
                calculation_type=payload.calculation_type,
                width=payload.width,
                height=payload.height,
                wall_length=payload.wall_length,
                wall_height=payload.wall_height,
                side_multiplier=payload.side_multiplier,
                count=payload.count,
                custom_formula=payload.custom_formula,
                custom_quantity=payload.custom_quantity,
                unit=payload.unit,
                source_sheets=payload.source_sheets
                if payload.source_sheets is not None
                else measurement.source_sheets,
                deductions=tuple(
                    DeductionInput(
                        amount=deduction.amount,
                        label=deduction.label,
                        formula=deduction.formula,
                    )
                    for deduction in payload.deductions
                ),
            )
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    measurement.formula = result.formula
    measurement.quantity = result.quantity
    measurement.unit = result.unit
    measurement.source_sheets = result.source_sheets
    measurement.deductions_json = result.deductions_json
    measurement.status = ReviewStatus.DRAFT
    db.commit()
    db.refresh(measurement)
    return measurement


@router.patch("/measurements/{measurement_id}", response_model=MeasurementRead)
def update_measurement(
    measurement_id: int,
    payload: MeasurementUpdate,
    db: Session = Depends(get_db),
) -> Measurement:
    measurement = db.get(Measurement, measurement_id)
    if measurement is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Measurement not found.",
        )

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "source_sheets" and value is None:
            value = ""
        if field == "status" and value is None:
            continue
        setattr(measurement, field, value)

    db.commit()
    db.refresh(measurement)
    return measurement


def _room_finishes_for_drawing_file(db: Session, drawing_file: DrawingFile) -> list[RoomFinish]:
    return (
        db.query(RoomFinish)
        .join(DrawingSheet, RoomFinish.drawing_sheet_id == DrawingSheet.id, isouter=True)
        .filter(
            RoomFinish.project_id == drawing_file.project_id,
            (RoomFinish.drawing_sheet_id.is_(None)) | (DrawingSheet.drawing_file_id == drawing_file.id),
        )
        .order_by(RoomFinish.id)
        .all()
    )


def _measurements_for_drawing_file(db: Session, drawing_file: DrawingFile) -> list[Measurement]:
    room_finish_ids = [row.id for row in _room_finishes_for_drawing_file(db, drawing_file)]
    if not room_finish_ids:
        return []

    return (
        db.query(Measurement)
        .filter(
            Measurement.project_id == drawing_file.project_id,
            Measurement.room_finish_id.in_(room_finish_ids),
        )
        .order_by(Measurement.id)
        .all()
    )


def _allowed_calculation_types(measurement_type: MeasurementType) -> tuple[CalculationType, ...]:
    if measurement_type in {MeasurementType.FLOOR_AREA, MeasurementType.CEILING_AREA}:
        return (CalculationType.AREA_RECTANGLE, CalculationType.CUSTOM)
    if measurement_type == MeasurementType.PERIMETER_LENGTH:
        return (CalculationType.PERIMETER_RECTANGLE, CalculationType.CUSTOM)
    if measurement_type == MeasurementType.WALL_AREA:
        return (CalculationType.WALL_AREA, CalculationType.CUSTOM)
    if measurement_type == MeasurementType.PARTITION_AREA:
        return (CalculationType.PARTITION_AREA, CalculationType.CUSTOM)
    if measurement_type == MeasurementType.COUNT:
        return (CalculationType.COUNT, CalculationType.CUSTOM)
    return (CalculationType.CUSTOM,)
