import sys
from pathlib import Path

import pytest

from openpyxl import load_workbook

sys.path.insert(0, str(Path(__file__).parent))
from create_example_dataset_template import build_workbook
from validate_example_dataset import validate_workbook


def _save_workbook(path: Path, row_count: int = 20) -> Path:
    workbook = build_workbook()
    sheet = workbook["TakeoffRows"]
    for index in range(1, row_count + 1):
        sheet.append(
            [
                f"ROW-{index:03d}",
                "110",
                "OFFICE",
                "FLOOR",
                "VCT-1",
                "FLOOR_AREA",
                "AE401, AE101",
                "plan dimension text",
                4.2,
                2.7,
                None,
                None,
                None,
                None,
                "{}",
                "4.2 * 2.7",
                11.34,
                "m2",
                "CONFIRMED",
                "",
                "{}",
                "anonymized example",
            ]
        )
    workbook.save(path)
    return path


def test_valid_dataset_passes(tmp_path):
    path = _save_workbook(tmp_path / "dataset.xlsx")

    assert validate_workbook(path) == []


def test_blank_template_passes_only_in_template_mode(tmp_path):
    path = tmp_path / "template.xlsx"
    build_workbook().save(path)

    assert validate_workbook(path, allow_empty_template=True) == []
    issues = validate_workbook(path)
    assert any("expected 20-50 populated rows" in issue.message for issue in issues)


def test_missing_required_sheet_fails(tmp_path):
    path = _save_workbook(tmp_path / "dataset.xlsx")
    workbook = load_workbook(path)
    del workbook["Sources"]
    workbook.save(path)

    issues = validate_workbook(path)

    assert any(issue.sheet == "Sources" and "required sheet" in issue.message for issue in issues)


def test_invalid_enum_values_fail(tmp_path):
    path = _save_workbook(tmp_path / "dataset.xlsx")
    workbook = load_workbook(path)
    sheet = workbook["TakeoffRows"]
    sheet["F2"] = "AUTO_AREA"
    sheet["R2"] = "SQM"
    sheet["S2"] = "DONE"
    workbook.save(path)

    issues = validate_workbook(path)

    assert any(issue.column == "measurement_type" for issue in issues)
    assert any(issue.column == "unit" for issue in issues)
    assert any(issue.column == "status" for issue in issues)


def test_missing_formula_quantity_and_source_fail(tmp_path):
    path = _save_workbook(tmp_path / "dataset.xlsx")
    workbook = load_workbook(path)
    sheet = workbook["TakeoffRows"]
    sheet["G2"] = None
    sheet["P2"] = None
    sheet["Q2"] = None
    workbook.save(path)

    issues = validate_workbook(path)

    assert any(issue.column == "source_sheets" for issue in issues)
    assert any(issue.column == "formula" for issue in issues)
    assert any(issue.column == "quantity" for issue in issues)


def test_invalid_json_fields_fail(tmp_path):
    path = _save_workbook(tmp_path / "dataset.xlsx")
    workbook = load_workbook(path)
    sheet = workbook["TakeoffRows"]
    sheet["O2"] = "{not json}"
    sheet["U2"] = '"not an object"'
    workbook.save(path)

    issues = validate_workbook(path)

    assert any(issue.column == "deductions_json" and "valid JSON" in issue.message for issue in issues)
    assert any(issue.column == "evidence_json" and "object or array" in issue.message for issue in issues)


def test_private_path_leak_fails(tmp_path):
    path = _save_workbook(tmp_path / "dataset.xlsx")
    workbook = load_workbook(path)
    workbook["TakeoffRows"]["V2"] = r"C:\WorkSpace\finish-takeoff\takeoff-assistant\data\samples\secret.pdf"
    workbook.save(path)

    issues = validate_workbook(path)

    assert any("private filesystem path" in issue.message for issue in issues)


@pytest.mark.parametrize("quantity", ["NaN", "Infinity", "-Infinity", "not a number"])
def test_non_finite_or_invalid_quantity_fails(tmp_path, quantity):
    path = _save_workbook(tmp_path / "dataset.xlsx")
    workbook = load_workbook(path)
    workbook["TakeoffRows"]["Q2"] = quantity
    workbook.save(path)

    issues = validate_workbook(path)

    assert any(issue.column == "quantity" and "finite number" in issue.message for issue in issues)


def test_duplicate_row_id_and_incorrect_header_fail(tmp_path):
    path = _save_workbook(tmp_path / "dataset.xlsx")
    workbook = load_workbook(path)
    workbook["TakeoffRows"]["A3"] = "ROW-001"
    workbook["Sources"]["A1"] = "wrong_header"
    workbook.save(path)

    issues = validate_workbook(path)

    assert any(issue.column == "row_id" and "unique" in issue.message for issue in issues)
    assert any(issue.sheet == "Sources" and "header mismatch" in issue.message for issue in issues)


@pytest.mark.parametrize("row_count", [19, 51])
def test_dataset_row_count_bounds_fail(tmp_path, row_count):
    path = _save_workbook(tmp_path / "dataset.xlsx", row_count=row_count)

    issues = validate_workbook(path)

    assert any("expected 20-50 populated rows" in issue.message for issue in issues)
