from decimal import Decimal

import pytest

from app.models import CalculationType
from app.services.calculation_engine import CalculationInput, DeductionInput, calculate


def test_area_rectangle_rounds_to_two_decimal_places() -> None:
    result = calculate(
        CalculationInput(
            calculation_type=CalculationType.AREA_RECTANGLE,
            width=Decimal("4.2"),
            height=Decimal("2.7"),
            source_sheets="AE401, AE101",
        )
    )

    assert result.formula == "4.2 * 2.7"
    assert result.quantity == Decimal("11.34")
    assert result.unit == "m2"
    assert result.source_sheets == "AE401, AE101"
    assert result.deductions_json is None


def test_area_rectangle_supports_floor_or_ceiling_deductions() -> None:
    result = calculate(
        CalculationInput(
            calculation_type=CalculationType.AREA_RECTANGLE,
            width=Decimal("5"),
            height=Decimal("4"),
            source_sheets="AE401, AE101",
            deductions=(
                DeductionInput(label="fixed furniture", amount=Decimal("1.89")),
            ),
        )
    )

    assert result.formula == "5 * 4 - 1.89"
    assert result.quantity == Decimal("18.11")
    assert result.unit == "m2"
    assert result.deductions_json == {
        "items": [
            {
                "label": "fixed furniture",
                "formula": None,
                "amount": "1.89",
            }
        ]
    }


def test_perimeter_rectangle_calculates_length() -> None:
    result = calculate(
        CalculationInput(
            calculation_type=CalculationType.PERIMETER_RECTANGLE,
            width=Decimal("4.2"),
            height=Decimal("2.7"),
        )
    )

    assert result.formula == "(4.2 + 2.7) * 2"
    assert result.quantity == Decimal("13.80")
    assert result.unit == "m"


def test_perimeter_rectangle_supports_length_deductions() -> None:
    result = calculate(
        CalculationInput(
            calculation_type=CalculationType.PERIMETER_RECTANGLE,
            width=Decimal("4.2"),
            height=Decimal("2.7"),
            deductions=(
                DeductionInput(label="opening", amount=Decimal("0.8")),
            ),
        )
    )

    assert result.formula == "(4.2 + 2.7) * 2 - 0.8"
    assert result.quantity == Decimal("13.00")
    assert result.unit == "m"
    assert result.deductions_json == {
        "items": [
            {
                "label": "opening",
                "formula": None,
                "amount": "0.80",
            }
        ]
    }


def test_wall_area_supports_door_window_deductions() -> None:
    result = calculate(
        CalculationInput(
            calculation_type=CalculationType.WALL_AREA,
            wall_length=Decimal("4.2"),
            wall_height=Decimal("4.6"),
            deductions=(
                DeductionInput(label="door", amount=Decimal("1.89"), formula="0.9 * 2.1"),
            ),
        )
    )

    assert result.formula == "4.2 * 4.6 - 0.9 * 2.1"
    assert result.quantity == Decimal("17.43")
    assert result.unit == "m2"


def test_partition_area_supports_two_sided_gwb_calculation() -> None:
    result = calculate(
        CalculationInput(
            calculation_type=CalculationType.PARTITION_AREA,
            wall_length=Decimal("4.2"),
            wall_height=Decimal("4.6"),
            side_multiplier=Decimal("2"),
        )
    )

    assert result.formula == "4.2 * 4.6 * 2"
    assert result.quantity == Decimal("38.64")
    assert result.unit == "m2"


def test_partition_area_defaults_to_one_side_when_multiplier_missing() -> None:
    result = calculate(
        CalculationInput(
            calculation_type=CalculationType.PARTITION_AREA,
            wall_length=Decimal("4.2"),
            wall_height=Decimal("4.6"),
        )
    )

    assert result.formula == "4.2 * 4.6 * 1"
    assert result.quantity == Decimal("19.32")
    assert result.unit == "m2"


def test_count_calculation() -> None:
    result = calculate(
        CalculationInput(
            calculation_type=CalculationType.COUNT,
            count=Decimal("7"),
        )
    )

    assert result.formula == "7"
    assert result.quantity == Decimal("7.00")
    assert result.unit == "EA"


def test_custom_calculation_stores_user_formula_and_quantity() -> None:
    result = calculate(
        CalculationInput(
            calculation_type=CalculationType.CUSTOM,
            custom_formula="manual takeoff from marked plan",
            custom_quantity=Decimal("12.345"),
            unit="m2",
            source_sheets="AE401, AE106",
        )
    )

    assert result.formula == "manual takeoff from marked plan"
    assert result.quantity == Decimal("12.35")
    assert result.unit == "m2"
    assert result.source_sheets == "AE401, AE106"


def test_calculation_requires_needed_inputs() -> None:
    with pytest.raises(ValueError, match="width is required"):
        calculate(
            CalculationInput(
                calculation_type=CalculationType.AREA_RECTANGLE,
                height=Decimal("2.7"),
            )
        )

    with pytest.raises(ValueError, match="unit is required"):
        calculate(
            CalculationInput(
                calculation_type=CalculationType.CUSTOM,
                custom_formula="manual",
                custom_quantity=Decimal("1"),
            )
        )
