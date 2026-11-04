#!/usr/bin/env python3
"""Create the anonymized 4th-phase example dataset Excel template."""

from __future__ import annotations

from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.utils import get_column_letter

from validate_example_dataset import (
    EXCEPTION_HEADERS,
    MEASUREMENT_TYPES,
    SOURCE_HEADERS,
    STATUSES,
    TAKEOFF_HEADERS,
    UNITS,
    VALIDATION_HEADERS,
)


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT = ROOT / "docs" / "templates" / "example_dataset_template.xlsx"


def build_workbook() -> Workbook:
    workbook = Workbook()
    readme = workbook.active
    readme.title = "README"

    _populate_readme(readme)
    takeoff = workbook.create_sheet("TakeoffRows")
    exceptions = workbook.create_sheet("Exceptions")
    sources = workbook.create_sheet("Sources")
    validation = workbook.create_sheet("Validation")

    _write_header_sheet(takeoff, TAKEOFF_HEADERS)
    _write_header_sheet(exceptions, EXCEPTION_HEADERS)
    _write_header_sheet(sources, SOURCE_HEADERS)
    _populate_validation(validation)
    _add_takeoff_validations(takeoff)
    return workbook


def save_template(path: Path = DEFAULT_OUTPUT) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    workbook = build_workbook()
    workbook.save(path)
    return path


def _populate_readme(sheet) -> None:
    rows = [
        ["Takeoff Assistant 4th MVP Example Dataset Template"],
        [""],
        ["Purpose", "Collect 20-50 reviewed takeoff examples for future automation quality work."],
        ["Privacy", "Do not store local absolute paths, client names, or private source file paths in this workbook."],
        ["Workflow", "Fill TakeoffRows, record exception rules, then run scripts/validate_example_dataset.py."],
        ["Template check", "Use --allow-empty-template when validating this blank template."],
    ]
    for row in rows:
        sheet.append(row)
    sheet["A1"].font = Font(bold=True, size=14, color="FFFFFF")
    sheet["A1"].fill = PatternFill("solid", fgColor="172026")
    sheet.merge_cells("A1:B1")
    sheet.column_dimensions["A"].width = 18
    sheet.column_dimensions["B"].width = 92
    for row in sheet.iter_rows(min_row=3, max_col=2):
        row[0].font = Font(bold=True)
        row[1].alignment = Alignment(wrap_text=True, vertical="top")


def _write_header_sheet(sheet, headers: list[str]) -> None:
    sheet.append(headers)
    _format_header_row(sheet)
    sheet.freeze_panes = "A2"
    sheet.auto_filter.ref = sheet.dimensions
    for column_index, header in enumerate(headers, start=1):
        width = max(14, min(32, len(header) + 4))
        sheet.column_dimensions[get_column_letter(column_index)].width = width


def _populate_validation(sheet) -> None:
    sheet.append(VALIDATION_HEADERS)
    max_len = max(len(MEASUREMENT_TYPES), len(UNITS), len(STATUSES), 1)
    measurement_types = sorted(MEASUREMENT_TYPES)
    units = sorted(UNITS)
    statuses = sorted(STATUSES)
    sheet_roles = [
        "FLOOR_PLAN",
        "ENLARGED_FLOOR_PLAN",
        "CEILING_PLAN",
        "PARTITION_PLAN",
        "FINISH_SCHEDULE",
        "PARTITION_DETAIL",
        "DOOR_SCHEDULE",
        "WINDOW_SCHEDULE",
        "DOOR_WINDOW_NUMBERING_PLAN",
    ]
    max_len = max(max_len, len(sheet_roles))
    for index in range(max_len):
        sheet.append(
            [
                measurement_types[index] if index < len(measurement_types) else None,
                units[index] if index < len(units) else None,
                statuses[index] if index < len(statuses) else None,
                sheet_roles[index] if index < len(sheet_roles) else None,
            ]
        )
    _format_header_row(sheet)
    sheet.freeze_panes = "A2"
    for column_index, header in enumerate(VALIDATION_HEADERS, start=1):
        sheet.column_dimensions[get_column_letter(column_index)].width = max(18, len(header) + 4)


def _add_takeoff_validations(sheet) -> None:
    measurement_type_col = TAKEOFF_HEADERS.index("measurement_type") + 1
    unit_col = TAKEOFF_HEADERS.index("unit") + 1
    status_col = TAKEOFF_HEADERS.index("status") + 1

    validations = [
        (measurement_type_col, sorted(MEASUREMENT_TYPES)),
        (unit_col, sorted(UNITS)),
        (status_col, sorted(STATUSES)),
    ]
    for column_index, values in validations:
        column_letter = get_column_letter(column_index)
        validation = DataValidation(type="list", formula1=f'"{",".join(values)}"', allow_blank=False)
        sheet.add_data_validation(validation)
        validation.add(f"{column_letter}2:{column_letter}501")


def _format_header_row(sheet) -> None:
    header_fill = PatternFill("solid", fgColor="172026")
    header_font = Font(color="FFFFFF", bold=True)
    header_alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    for cell in sheet[1]:
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = header_alignment


def main() -> int:
    output = save_template()
    print(f"Created {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
