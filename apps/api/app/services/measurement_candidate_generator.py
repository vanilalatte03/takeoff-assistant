from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Iterable

from app.models import Measurement, MeasurementType, ReviewStatus, RoomFinish


@dataclass(frozen=True)
class MeasurementCandidateSpec:
    category: str
    measurement_type: MeasurementType
    finish_code: str
    unit: str


def build_measurement_candidate_specs(room_finish: RoomFinish) -> list[MeasurementCandidateSpec]:
    specs: list[MeasurementCandidateSpec] = []
    if floor_code := _first_value(room_finish.floor_finish, room_finish.floor_material):
        specs.append(
            MeasurementCandidateSpec(
                category="FLOOR",
                measurement_type=MeasurementType.FLOOR_AREA,
                finish_code=floor_code,
                unit="m2",
            )
        )
    if ceiling_code := _first_value(room_finish.ceiling_finish, room_finish.ceiling_material):
        specs.append(
            MeasurementCandidateSpec(
                category="CEILING",
                measurement_type=MeasurementType.CEILING_AREA,
                finish_code=ceiling_code,
                unit="m2",
            )
        )
    if wall_code := _first_value(room_finish.wall_finish, room_finish.wall_material):
        specs.append(
            MeasurementCandidateSpec(
                category="WALL",
                measurement_type=MeasurementType.WALL_AREA,
                finish_code=wall_code,
                unit="m2",
            )
        )
    if base_code := _first_value(room_finish.base_finish, room_finish.base_material):
        specs.append(
            MeasurementCandidateSpec(
                category="BASE",
                measurement_type=MeasurementType.PERIMETER_LENGTH,
                finish_code=base_code,
                unit="m",
            )
        )
    return specs


def build_measurement_candidate(room_finish: RoomFinish, spec: MeasurementCandidateSpec) -> Measurement:
    return Measurement(
        project_id=room_finish.project_id,
        room_finish_id=room_finish.id,
        room_no=room_finish.room_no,
        room_name=room_finish.room_name,
        category=spec.category,
        finish_code=spec.finish_code,
        measurement_type=spec.measurement_type,
        formula=None,
        quantity=None,
        unit=spec.unit,
        source_sheets=_source_sheets(room_finish),
        status=ReviewStatus.DRAFT,
    )


def candidate_key(room_finish_id: int | None, spec: MeasurementCandidateSpec) -> tuple[int | None, MeasurementType, str]:
    return (room_finish_id, spec.measurement_type, spec.finish_code)


def existing_measurement_keys(measurements: Iterable[Measurement]) -> set[tuple[int | None, MeasurementType, str]]:
    return {
        (measurement.room_finish_id, measurement.measurement_type, measurement.finish_code)
        for measurement in measurements
    }


def _first_value(*values: str | None) -> str | None:
    for value in values:
        if value and value.strip():
            return value.strip()
    return None


def _source_sheets(room_finish: RoomFinish) -> str:
    if room_finish.source_sheet_no:
        return room_finish.source_sheet_no
    if room_finish.drawing_sheet and room_finish.drawing_sheet.sheet_no:
        return room_finish.drawing_sheet.sheet_no
    return ""
