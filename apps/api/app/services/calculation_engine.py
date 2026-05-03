from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

from app.models import CalculationType


TWO_PLACES = Decimal("0.01")


@dataclass(frozen=True)
class DeductionInput:
    amount: Decimal
    label: str | None = None
    formula: str | None = None


@dataclass(frozen=True)
class CalculationInput:
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
    source_sheets: str = ""
    deductions: tuple[DeductionInput, ...] = ()


@dataclass(frozen=True)
class CalculationResult:
    formula: str
    quantity: Decimal
    unit: str
    source_sheets: str
    deductions_json: dict[str, object] | None = None


def calculate(input_data: CalculationInput) -> CalculationResult:
    calculation_type = input_data.calculation_type
    if calculation_type == CalculationType.AREA_RECTANGLE:
        return _calculate_area_rectangle(input_data)
    if calculation_type == CalculationType.PERIMETER_RECTANGLE:
        return _calculate_perimeter_rectangle(input_data)
    if calculation_type == CalculationType.WALL_AREA:
        return _calculate_wall_area(input_data)
    if calculation_type == CalculationType.PARTITION_AREA:
        return _calculate_partition_area(input_data)
    if calculation_type == CalculationType.COUNT:
        return _calculate_count(input_data)
    if calculation_type == CalculationType.CUSTOM:
        return _calculate_custom(input_data)
    raise ValueError(f"Unsupported calculation type: {calculation_type}")


def _calculate_area_rectangle(input_data: CalculationInput) -> CalculationResult:
    width = _required_decimal(input_data.width, "width")
    height = _required_decimal(input_data.height, "height")
    base_quantity = width * height
    formula = f"{_format_decimal(width)} * {_format_decimal(height)}"
    return _with_deductions(input_data, base_quantity, formula, input_data.unit or "m2")


def _calculate_perimeter_rectangle(input_data: CalculationInput) -> CalculationResult:
    width = _required_decimal(input_data.width, "width")
    height = _required_decimal(input_data.height, "height")
    base_quantity = (width + height) * Decimal("2")
    formula = f"({_format_decimal(width)} + {_format_decimal(height)}) * 2"
    return _with_deductions(input_data, base_quantity, formula, input_data.unit or "m")


def _calculate_wall_area(input_data: CalculationInput) -> CalculationResult:
    wall_length = _required_decimal(input_data.wall_length, "wall_length")
    wall_height = _required_decimal(input_data.wall_height, "wall_height")
    base_quantity = wall_length * wall_height
    formula = f"{_format_decimal(wall_length)} * {_format_decimal(wall_height)}"
    return _with_deductions(input_data, base_quantity, formula, input_data.unit or "m2")


def _calculate_partition_area(input_data: CalculationInput) -> CalculationResult:
    wall_length = _required_decimal(input_data.wall_length, "wall_length")
    wall_height = _required_decimal(input_data.wall_height, "wall_height")
    side_multiplier = input_data.side_multiplier or Decimal("1")
    base_quantity = wall_length * wall_height * side_multiplier
    formula = (
        f"{_format_decimal(wall_length)} * "
        f"{_format_decimal(wall_height)} * "
        f"{_format_decimal(side_multiplier)}"
    )
    return _with_deductions(input_data, base_quantity, formula, input_data.unit or "m2")


def _calculate_count(input_data: CalculationInput) -> CalculationResult:
    count = _required_decimal(input_data.count, "count")
    return CalculationResult(
        formula=_format_decimal(count),
        quantity=_round_quantity(count),
        unit=input_data.unit or "EA",
        source_sheets=input_data.source_sheets,
    )


def _calculate_custom(input_data: CalculationInput) -> CalculationResult:
    if not input_data.custom_formula or not input_data.custom_formula.strip():
        raise ValueError("custom_formula is required for CUSTOM calculations.")
    custom_quantity = _required_decimal(input_data.custom_quantity, "custom_quantity")
    if not input_data.unit or not input_data.unit.strip():
        raise ValueError("unit is required for CUSTOM calculations.")
    return CalculationResult(
        formula=input_data.custom_formula.strip(),
        quantity=_round_quantity(custom_quantity),
        unit=input_data.unit.strip(),
        source_sheets=input_data.source_sheets,
    )


def _with_deductions(
    input_data: CalculationInput,
    base_quantity: Decimal,
    base_formula: str,
    unit: str,
) -> CalculationResult:
    deduction_total = sum((deduction.amount for deduction in input_data.deductions), Decimal("0"))
    quantity = base_quantity - deduction_total
    formula = base_formula
    deductions_json = None
    if input_data.deductions:
        formula = f"{base_formula} - {_deduction_formula(input_data.deductions)}"
        deductions_json = {
            "items": [
                {
                    "label": deduction.label,
                    "formula": deduction.formula,
                    "amount": str(_round_quantity(deduction.amount)),
                }
                for deduction in input_data.deductions
            ]
        }

    return CalculationResult(
        formula=formula,
        quantity=_round_quantity(quantity),
        unit=unit,
        source_sheets=input_data.source_sheets,
        deductions_json=deductions_json,
    )


def _deduction_formula(deductions: tuple[DeductionInput, ...]) -> str:
    terms = [
        deduction.formula.strip() if deduction.formula and deduction.formula.strip() else _format_decimal(deduction.amount)
        for deduction in deductions
    ]
    if len(terms) == 1:
        return terms[0]
    return f"({' + '.join(terms)})"


def _required_decimal(value: Decimal | None, field_name: str) -> Decimal:
    if value is None:
        raise ValueError(f"{field_name} is required.")
    return Decimal(value)


def _round_quantity(value: Decimal) -> Decimal:
    return value.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


def _format_decimal(value: Decimal) -> str:
    normalized = value.normalize()
    if normalized == normalized.to_integral():
        return str(normalized.quantize(Decimal("1")))
    return format(normalized, "f")
