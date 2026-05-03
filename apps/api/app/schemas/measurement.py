from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import CalculationType, MeasurementType, ReviewStatus


class MeasurementBase(BaseModel):
    project_id: int
    room_finish_id: int | None = None
    room_no: str | None = None
    room_name: str | None = None
    category: str
    finish_code: str
    measurement_type: MeasurementType
    formula: str | None = None
    quantity: Decimal | None = None
    unit: str | None = None
    source_sheets: str = ""
    status: ReviewStatus = ReviewStatus.DRAFT
    memo: str | None = None
    coordinates_json: dict[str, Any] | None = None
    deductions_json: dict[str, Any] | None = None
    measurement_confidence: float | None = None


class MeasurementCreate(MeasurementBase):
    pass


class MeasurementUpdate(BaseModel):
    category: str | None = None
    finish_code: str | None = None
    measurement_type: MeasurementType | None = None
    formula: str | None = None
    quantity: Decimal | None = None
    unit: str | None = None
    source_sheets: str | None = None
    status: ReviewStatus | None = None
    memo: str | None = None
    coordinates_json: dict[str, Any] | None = None
    measurement_confidence: float | None = None


class MeasurementRead(MeasurementBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MeasurementGenerationResult(BaseModel):
    drawing_file_id: int
    measurements: list[MeasurementRead]


class MeasurementDeductionInput(BaseModel):
    amount: Decimal
    label: str | None = None
    formula: str | None = None


class MeasurementCalculationInput(BaseModel):
    calculation_type: CalculationType
    width: Decimal | None = None
    height: Decimal | None = None
    wall_length: Decimal | None = None
    wall_height: Decimal | None = None
    side_multiplier: Decimal | None = None
    count: Decimal | None = None
    custom_formula: str | None = None
    custom_quantity: Decimal | None = None
    unit: str | None = None
    source_sheets: str | None = None
    deductions: list[MeasurementDeductionInput] = Field(default_factory=list)
