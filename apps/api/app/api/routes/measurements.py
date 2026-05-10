from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import CalculationType, DrawingFile, DrawingSheet, Measurement, MeasurementType, ReviewStatus, RoomFinish
from app.schemas import (
    DrawingFileRoomStatusResponse,
    MeasurementCalculationInput,
    MeasurementGenerationResult,
    MeasurementMergeRequest,
    MeasurementRead,
    MeasurementUpdate,
    RoomMeasurementStatus,
)
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
    room_no: str | None = Query(default=None),
    category: str | None = Query(default=None),
    code: str | None = Query(default=None),
    measurement_type: MeasurementType | None = Query(default=None),
    status_filter: ReviewStatus | None = Query(default=None, alias="status"),
    db: Session = Depends(get_db),
) -> list[Measurement]:
    drawing_file = db.get(DrawingFile, drawing_file_id)
    if drawing_file is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Drawing file not found.",
        )

    return _measurements_for_drawing_file(
        db,
        drawing_file,
        room_no=room_no,
        category=category,
        code=code,
        measurement_type=measurement_type,
        status_filter=status_filter,
    )


@router.get(
    "/drawing-files/{drawing_file_id}/room-status",
    response_model=DrawingFileRoomStatusResponse,
)
def get_drawing_file_room_status(
    drawing_file_id: int,
    db: Session = Depends(get_db),
) -> DrawingFileRoomStatusResponse:
    drawing_file = db.get(DrawingFile, drawing_file_id)
    if drawing_file is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Drawing file not found.",
        )

    room_finishes = _room_finishes_for_drawing_file(db, drawing_file)
    measurements = _measurements_for_drawing_file(db, drawing_file)
    measurements_by_room_finish: dict[int, list[Measurement]] = {}
    for measurement in measurements:
        if measurement.room_finish_id is None:
            continue
        measurements_by_room_finish.setdefault(measurement.room_finish_id, []).append(measurement)

    rooms: list[RoomMeasurementStatus] = []
    for room_finish in room_finishes:
        active_measurements = [
            measurement
            for measurement in measurements_by_room_finish.get(room_finish.id, [])
            if measurement.status != ReviewStatus.REJECTED
        ]
        rooms.append(
            RoomMeasurementStatus(
                room_no=room_finish.room_no,
                room_name=room_finish.room_name,
                total_count=len(active_measurements),
                quantity_count=sum(1 for measurement in active_measurements if measurement.quantity is not None),
                confirmed_count=sum(1 for measurement in active_measurements if measurement.status == ReviewStatus.CONFIRMED),
                needs_review_count=sum(1 for measurement in active_measurements if measurement.status == ReviewStatus.NEEDS_REVIEW),
                missing_quantity_count=sum(1 for measurement in active_measurements if measurement.quantity is None),
            )
        )

    return DrawingFileRoomStatusResponse(drawing_file_id=drawing_file.id, rooms=rooms)


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


@router.delete("/measurements/{measurement_id}", response_model=MeasurementRead)
def reject_measurement(
    measurement_id: int,
    db: Session = Depends(get_db),
) -> Measurement:
    measurement = db.get(Measurement, measurement_id)
    if measurement is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Measurement not found.",
        )
    if measurement.status == ReviewStatus.CONFIRMED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Confirmed measurements cannot be rejected.",
        )

    measurement.status = ReviewStatus.REJECTED
    db.commit()
    db.refresh(measurement)
    return measurement


@router.post("/measurements/merge", response_model=MeasurementRead)
def merge_measurements(
    payload: MeasurementMergeRequest,
    db: Session = Depends(get_db),
) -> Measurement:
    if not payload.source_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="source_ids must contain at least one measurement id.",
        )
    if payload.target_id in payload.source_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="target_id cannot also be a source id.",
        )

    source_ids = list(dict.fromkeys(payload.source_ids))
    measurements = (
        db.query(Measurement)
        .filter(Measurement.id.in_([payload.target_id, *source_ids]))
        .order_by(Measurement.id)
        .all()
    )
    by_id = {measurement.id: measurement for measurement in measurements}
    target = by_id.get(payload.target_id)
    sources = [by_id.get(source_id) for source_id in source_ids]
    missing_ids = [source_id for source_id, measurement in zip(source_ids, sources) if measurement is None]
    if target is None:
        missing_ids.insert(0, payload.target_id)
    if missing_ids:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": "Measurement not found.", "measurement_ids": missing_ids},
        )

    source_measurements = [measurement for measurement in sources if measurement is not None]
    _validate_merge_rows(target, source_measurements)
    _apply_measurement_merge(target, source_measurements)

    db.commit()
    db.refresh(target)
    return target


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


def _measurements_for_drawing_file(
    db: Session,
    drawing_file: DrawingFile,
    *,
    room_no: str | None = None,
    category: str | None = None,
    code: str | None = None,
    measurement_type: MeasurementType | None = None,
    status_filter: ReviewStatus | None = None,
) -> list[Measurement]:
    room_finish_ids = [row.id for row in _room_finishes_for_drawing_file(db, drawing_file)]
    if not room_finish_ids:
        return []

    query = (
        db.query(Measurement)
        .filter(
            Measurement.project_id == drawing_file.project_id,
            Measurement.room_finish_id.in_(room_finish_ids),
        )
    )
    if room_no:
        query = query.filter(Measurement.room_no.ilike(f"%{room_no.strip()}%"))
    if category:
        query = query.filter(Measurement.category.ilike(f"%{category.strip()}%"))
    if code:
        query = query.filter(Measurement.finish_code.ilike(f"%{code.strip()}%"))
    if measurement_type is not None:
        query = query.filter(Measurement.measurement_type == measurement_type)
    if status_filter is not None:
        query = query.filter(Measurement.status == status_filter)

    return query.order_by(Measurement.id).all()


def _validate_merge_rows(target: Measurement, sources: list[Measurement]) -> None:
    all_measurements = [target, *sources]
    confirmed_ids = [measurement.id for measurement in all_measurements if measurement.status == ReviewStatus.CONFIRMED]
    if confirmed_ids:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": "Confirmed measurements cannot be merged.",
                "measurement_ids": confirmed_ids,
            },
        )
    rejected_ids = [measurement.id for measurement in all_measurements if measurement.status == ReviewStatus.REJECTED]
    if rejected_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": "Rejected measurements cannot be merged.",
                "measurement_ids": rejected_ids,
            },
        )

    target_key = _merge_key(target)
    mismatched_ids = [measurement.id for measurement in sources if _merge_key(measurement) != target_key]
    if mismatched_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": "Measurements can only be merged when room, category, code, type, and unit match.",
                "measurement_ids": mismatched_ids,
            },
        )


def _apply_measurement_merge(target: Measurement, sources: list[Measurement]) -> None:
    merge_rows = [target, *sources]
    if all(measurement.quantity is not None for measurement in merge_rows):
        target.quantity = sum((measurement.quantity for measurement in merge_rows), Decimal("0.00"))

    formulas = [f"#{measurement.id}: {measurement.formula}" for measurement in merge_rows if measurement.formula]
    if formulas:
        target.formula = " + ".join(formulas)

    target.source_sheets = _merge_csv_values(measurement.source_sheets for measurement in merge_rows)
    target.memo = _merge_memo_values(merge_rows)
    target.status = ReviewStatus.DRAFT
    for source in sources:
        source.status = ReviewStatus.REJECTED


def _merge_key(measurement: Measurement) -> tuple[str | None, str, str, MeasurementType, str | None]:
    return (
        measurement.room_no,
        measurement.category,
        measurement.finish_code,
        measurement.measurement_type,
        measurement.unit,
    )


def _merge_csv_values(values: list[str] | tuple[str, ...] | object) -> str:
    merged: list[str] = []
    for value in values:
        if not isinstance(value, str):
            continue
        for item in value.replace(";", ",").split(","):
            normalized = item.strip()
            if normalized and normalized not in merged:
                merged.append(normalized)
    return ", ".join(merged)


def _merge_memo_values(measurements: list[Measurement]) -> str | None:
    parts = [f"#{measurement.id}: {measurement.memo}" for measurement in measurements if measurement.memo]
    return "\n".join(parts) if parts else None


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
