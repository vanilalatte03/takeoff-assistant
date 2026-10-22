"""Shared quantity and unit rules for calculated and manually entered rows."""

from decimal import Decimal, InvalidOperation

from app.models import MeasurementType, ReviewStatus


MAX_QUANTITY = Decimal("9999999999.99")  # Numeric(12, 2)


def nonnegative_decimal(value: Decimal, field: str) -> Decimal:
    try:
        number = Decimal(value)
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be a finite number.") from exc
    if not number.is_finite() or number < 0:
        raise ValueError(f"{field} must be finite and non-negative.")
    return number


def validate_quantity(quantity: Decimal, unit: str, *, count: bool = False) -> None:
    number = nonnegative_decimal(quantity, "quantity")
    if number > MAX_QUANTITY:
        raise ValueError("quantity exceeds Numeric(12, 2) storage capacity.")
    if unit not in {"m2", "m", "EA"}:
        raise ValueError("unit must be m2, m, or EA.")
    if (count or unit == "EA") and number != number.to_integral_value():
        raise ValueError("count must be a whole number.")


def expected_unit(measurement_type: MeasurementType) -> str:
    if measurement_type == MeasurementType.COUNT:
        return "EA"
    if measurement_type == MeasurementType.PERIMETER_LENGTH:
        return "m"
    return "m2"


def validate_measurement_values(*, measurement_type: MeasurementType | None, quantity: Decimal | None,
                                unit: str | None, formula: str | None, source_sheets: str | None,
                                status: ReviewStatus, category: str | None, finish_code: str | None) -> None:
    if measurement_type is None or not category or not category.strip() or not finish_code or not finish_code.strip():
        raise ValueError("measurement_type, category, and finish_code are required.")
    if unit is not None and unit != expected_unit(measurement_type):
        raise ValueError(f"{measurement_type.value} requires unit {expected_unit(measurement_type)}.")
    if quantity is not None:
        if unit != expected_unit(measurement_type):
            raise ValueError(f"A saved quantity requires unit {expected_unit(measurement_type)}.")
        validate_quantity(quantity, unit, count=measurement_type == MeasurementType.COUNT)
    if status == ReviewStatus.CONFIRMED:
        if quantity is None or not unit or not formula or not formula.strip() or not source_sheets or not source_sheets.strip():
            raise ValueError("Confirmation requires quantity, unit, formula, and source_sheets.")
