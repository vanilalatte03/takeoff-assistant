from copy import deepcopy
from decimal import Decimal, ROUND_HALF_UP

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, object_session

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
from app.services.measurement_validation import validate_measurement_values


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
    # A corrected finish code still represents the original candidate.
    existing_types = {(key[0], key[1], key[2]) for key in existing_keys}
    for room_finish in room_finishes:
        if room_finish.status == ReviewStatus.REJECTED:
            continue
        for spec in build_measurement_candidate_specs(room_finish):
            key = candidate_key(room_finish.id, spec)
            if key[:3] in existing_types:
                continue
            measurement = build_measurement_candidate(room_finish, spec)
            db.add(measurement)
            created_measurements.append(measurement)
            existing_keys.add(key)
            existing_types.add(key[:3])

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

    _require_editable(measurement)

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
                source_sheets=_merge_csv_values((measurement.source_sheets, payload.source_sheets or "")),
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
        validate_measurement_values(
            measurement_type=measurement.measurement_type, quantity=result.quantity, unit=result.unit,
            formula=result.formula, source_sheets=result.source_sheets, status=ReviewStatus.DRAFT,
            category=measurement.category, finish_code=measurement.finish_code,
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
    evidence = _archive_merge_provenance(dict(measurement.coordinates_json or {}))
    evidence["calculation_inputs"] = payload.model_dump(mode="json")
    evidence["calculation_inputs"]["source_sheets"] = result.source_sheets
    measurement.coordinates_json = evidence
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
    if measurement.room_finish and measurement.room_finish.status == ReviewStatus.REJECTED:
        raise HTTPException(status_code=409, detail="Measurements of rejected room finishes are read-only.")
    if measurement.status == ReviewStatus.CONFIRMED:
        if update_data != {"status": ReviewStatus.DRAFT}:
            raise HTTPException(status_code=409, detail="Confirmed measurements are read-only. Reopen with status DRAFT only.")
        # Older versions accepted invalid units/quantities. Reopening must remain
        # possible so the user can correct those values on the following edit.
        measurement.status = ReviewStatus.DRAFT
        db.commit()
        db.refresh(measurement)
        return measurement
    else:
        _require_editable(measurement)
    if update_data.get("deductions_json") is not None:
        raise HTTPException(status_code=400, detail="Change deductions through the calculation API; PATCH only supports clearing them.")
    candidate = {field: update_data.get(field, getattr(measurement, field))
                 for field in ("measurement_type", "quantity", "unit", "formula", "source_sheets", "status", "category", "finish_code")}
    if candidate["status"] is None:
        candidate["status"] = measurement.status
    try:
        validate_measurement_values(**candidate)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if update_data.get("quantity") is not None:
        update_data["quantity"] = update_data["quantity"].quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    value_changed = any(field in update_data and update_data[field] != getattr(measurement, field)
                        for field in ("measurement_type", "formula", "quantity", "unit"))
    supplied_coordinates = update_data.get("coordinates_json") or {}
    geometry_changed = "coordinates_json" in update_data and any(
        field in supplied_coordinates and supplied_coordinates[field] != (measurement.coordinates_json or {}).get(field)
        for field in ("measurement_mode", "points", "scale", "result", "page_index", "drawing_file_id")
    )
    deductions_cleared = "deductions_json" in update_data and measurement.deductions_json is not None
    manual_replacement = "coordinates_json" in update_data and "deductions_json" in update_data
    dimension_changed = "dimension_assist" in supplied_coordinates and supplied_coordinates["dimension_assist"] != (measurement.coordinates_json or {}).get("dimension_assist")
    invalidate_inputs = value_changed or geometry_changed or deductions_cleared or manual_replacement or dimension_changed
    if "coordinates_json" in update_data or invalidate_inputs:
        # Client-supplied coordinates are evidence, never authoritative server calculation inputs.
        coordinates = deepcopy(measurement.coordinates_json or {})
        coordinates.update(supplied_coordinates)
        coordinates.pop("calculation_inputs", None)
        if not invalidate_inputs and (measurement.coordinates_json or {}).get("calculation_inputs") is not None:
            coordinates["calculation_inputs"] = measurement.coordinates_json["calculation_inputs"]
        if invalidate_inputs:
            coordinates = _archive_merge_provenance(coordinates)
            if value_changed or geometry_changed or manual_replacement:
                update_data.setdefault("deductions_json", None)
        update_data["coordinates_json"] = coordinates or None
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
    if measurement.status in {ReviewStatus.CONFIRMED, ReviewStatus.REJECTED}:
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
    for row in [target, *source_measurements]:
        _require_editable(row)
    file_id = _measurement_drawing_file_id(target)
    if file_id is None or any(row.project_id != target.project_id or _measurement_drawing_file_id(row) != file_id
                              for row in source_measurements):
        raise HTTPException(status_code=400, detail="Measurements must belong to the same assigned drawing file and project.")
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
            ((RoomFinish.drawing_file_id == drawing_file.id)
             & ((RoomFinish.drawing_sheet_id.is_(None)) | (DrawingSheet.drawing_file_id == drawing_file.id)))
            | ((RoomFinish.drawing_file_id.is_(None)) & (DrawingSheet.drawing_file_id == drawing_file.id)),
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
    if any(row.quantity is None or not row.formula or not row.formula.strip() for row in all_measurements):
        raise HTTPException(status_code=400, detail="Every merged measurement requires a quantity and formula.")
    for row in all_measurements:
        try:
            validate_measurement_values(measurement_type=row.measurement_type, quantity=row.quantity, unit=row.unit,
                                        formula=row.formula, source_sheets=row.source_sheets,
                                        status=ReviewStatus.CONFIRMED, category=row.category, finish_code=row.finish_code)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=f"Measurement #{row.id}: {exc}") from exc


def _apply_measurement_merge(target: Measurement, sources: list[Measurement]) -> None:
    merge_rows = [target, *sources]
    snapshots = [{"measurement_id": row.id, "project_id": row.project_id, "room_finish_id": row.room_finish_id,
                  "formula": row.formula, "quantity": str(row.quantity), "unit": row.unit,
                  "source_sheets": row.source_sheets, "coordinates_json": deepcopy(row.coordinates_json),
                  "deductions_json": deepcopy(row.deductions_json)} for row in merge_rows]
    quantity = sum((measurement.quantity for measurement in merge_rows), Decimal("0.00"))
    try:
        validate_measurement_values(measurement_type=target.measurement_type, quantity=quantity, unit=target.unit,
                                    formula=target.formula, source_sheets=target.source_sheets,
                                    status=ReviewStatus.DRAFT, category=target.category, finish_code=target.finish_code)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    target.quantity = quantity
    target.coordinates_json = {"merge_provenance": {"rows": snapshots}}
    target.deductions_json = None

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


def _measurement_drawing_file_id(measurement: Measurement) -> int | None:
    room = measurement.room_finish
    if room is None or room.project_id != measurement.project_id:
        return None
    sheet_file_id = room.drawing_sheet.drawing_file_id if room.drawing_sheet else None
    if room.drawing_file_id is not None and sheet_file_id is not None and room.drawing_file_id != sheet_file_id:
        return None
    file_id = room.drawing_file_id if room.drawing_file_id is not None else sheet_file_id
    if file_id is None:
        return None
    session = object_session(measurement)
    drawing_file = session.get(DrawingFile, file_id) if session else None
    return file_id if drawing_file and drawing_file.project_id == measurement.project_id else None


def _require_editable(measurement: Measurement) -> None:
    if measurement.status in {ReviewStatus.CONFIRMED, ReviewStatus.REJECTED}:
        raise HTTPException(status_code=409, detail="Confirmed or rejected measurements are read-only.")
    if measurement.room_finish and measurement.room_finish.status == ReviewStatus.REJECTED:
        raise HTTPException(status_code=409, detail="Measurements of rejected room finishes are read-only.")


def _archive_merge_provenance(coordinates: dict) -> dict:
    provenance = coordinates.pop("merge_provenance", None)
    if provenance is not None:
        previous_history = coordinates.get("history", [])
        history = list(previous_history) if isinstance(previous_history, list) else [{"legacy_history": previous_history}]
        coordinates["history"] = [*history, {"merge_provenance": provenance}]
    return coordinates


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
