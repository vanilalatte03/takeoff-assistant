#!/usr/bin/env python3
"""Validate the private 4th-phase example takeoff dataset workbook."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from openpyxl import load_workbook
from openpyxl.worksheet.worksheet import Worksheet


REQUIRED_SHEETS = ("README", "TakeoffRows", "Exceptions", "Sources", "Validation")

TAKEOFF_HEADERS = [
    "row_id",
    "room_no",
    "room_name",
    "category",
    "finish_code",
    "measurement_type",
    "source_sheets",
    "dimension_source",
    "width_m",
    "depth_m",
    "wall_length_m",
    "wall_height_m",
    "side_multiplier",
    "count",
    "deductions_json",
    "formula",
    "quantity",
    "unit",
    "status",
    "exception_tags",
    "evidence_json",
    "review_notes",
]

EXCEPTION_HEADERS = [
    "exception_tag",
    "description",
    "applies_to",
    "default_rule",
    "example_row_id",
    "notes",
]

SOURCE_HEADERS = [
    "source_id",
    "sheet_no",
    "sheet_title",
    "sheet_role",
    "page_index",
    "notes",
]

VALIDATION_HEADERS = ["measurement_type", "unit", "status", "sheet_role"]

MEASUREMENT_TYPES = {
    "FLOOR_AREA",
    "CEILING_AREA",
    "PERIMETER_LENGTH",
    "WALL_AREA",
    "PARTITION_AREA",
    "COUNT",
}

UNITS = {"m2", "m", "EA"}
STATUSES = {"DRAFT", "NEEDS_REVIEW", "CONFIRMED"}

PRIVATE_PATH_PATTERNS = [
    re.compile(r"[A-Za-z]:[\\/]"),
    re.compile(r"\\\\[^\\]+\\[^\\]+"),
    re.compile(r"(^|[\\/])(Users|home)[\\/]", re.IGNORECASE),
    re.compile(r"data[\\/](samples|uploads|rendered)", re.IGNORECASE),
]


@dataclass(frozen=True)
class ValidationIssue:
    sheet: str
    row: int | None
    column: str | None
    message: str

    def format(self) -> str:
        location = self.sheet
        if self.row is not None:
            location += f"!{self.row}"
        if self.column:
            location += f"[{self.column}]"
        return f"{location}: {self.message}"


def validate_workbook(
    path: Path,
    *,
    min_rows: int = 20,
    max_rows: int = 50,
    allow_empty_template: bool = False,
) -> list[ValidationIssue]:
    workbook = load_workbook(path, data_only=False)
    issues: list[ValidationIssue] = []

    for sheet_name in REQUIRED_SHEETS:
        if sheet_name not in workbook.sheetnames:
            issues.append(ValidationIssue(sheet_name, None, None, "required sheet is missing"))

    if issues:
        issues.extend(_private_path_issues(workbook.worksheets))
        return issues

    issues.extend(_header_issues(workbook["TakeoffRows"], TAKEOFF_HEADERS))
    issues.extend(_header_issues(workbook["Exceptions"], EXCEPTION_HEADERS))
    issues.extend(_header_issues(workbook["Sources"], SOURCE_HEADERS))
    issues.extend(_header_issues(workbook["Validation"], VALIDATION_HEADERS))

    takeoff_rows = _records(workbook["TakeoffRows"], TAKEOFF_HEADERS)
    if allow_empty_template and not takeoff_rows:
        pass
    elif len(takeoff_rows) < min_rows or len(takeoff_rows) > max_rows:
        issues.append(
            ValidationIssue(
                "TakeoffRows",
                None,
                None,
                f"expected {min_rows}-{max_rows} populated rows, found {len(takeoff_rows)}",
            )
        )

    issues.extend(_takeoff_row_issues(takeoff_rows))
    issues.extend(_private_path_issues(workbook.worksheets))
    return issues


def _header_issues(sheet: Worksheet, expected: list[str]) -> list[ValidationIssue]:
    actual = [_normalize(sheet.cell(1, column).value) for column in range(1, len(expected) + 1)]
    if actual == expected:
        return []
    return [
        ValidationIssue(
            sheet.title,
            1,
            None,
            f"header mismatch; expected {expected}, found {actual}",
        )
    ]


def _records(sheet: Worksheet, headers: list[str]) -> list[tuple[int, dict[str, Any]]]:
    records: list[tuple[int, dict[str, Any]]] = []
    for row_index in range(2, sheet.max_row + 1):
        record = {
            header: sheet.cell(row_index, column_index).value
            for column_index, header in enumerate(headers, start=1)
        }
        if all(_is_blank(value) for value in record.values()):
            continue
        records.append((row_index, record))
    return records


def _takeoff_row_issues(records: list[tuple[int, dict[str, Any]]]) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    seen_row_ids: set[str] = set()

    required_columns = (
        "row_id",
        "category",
        "finish_code",
        "measurement_type",
        "source_sheets",
        "formula",
        "quantity",
        "unit",
        "status",
    )

    for row_index, record in records:
        for column in required_columns:
            if _is_blank(record.get(column)):
                issues.append(ValidationIssue("TakeoffRows", row_index, column, "required value is blank"))

        row_id = _normalize(record.get("row_id"))
        if row_id:
            if row_id in seen_row_ids:
                issues.append(ValidationIssue("TakeoffRows", row_index, "row_id", "row_id must be unique"))
            seen_row_ids.add(row_id)

        measurement_type = _normalize(record.get("measurement_type"))
        if measurement_type and measurement_type not in MEASUREMENT_TYPES:
            issues.append(
                ValidationIssue(
                    "TakeoffRows",
                    row_index,
                    "measurement_type",
                    f"invalid measurement_type '{measurement_type}'",
                )
            )

        unit = _normalize(record.get("unit"))
        if unit and unit not in UNITS:
            issues.append(ValidationIssue("TakeoffRows", row_index, "unit", f"invalid unit '{unit}'"))

        status = _normalize(record.get("status"))
        if status and status not in STATUSES:
            issues.append(ValidationIssue("TakeoffRows", row_index, "status", f"invalid status '{status}'"))

        quantity = record.get("quantity")
        if not _is_blank(quantity):
            try:
                if not Decimal(str(quantity)).is_finite():
                    raise ValueError("quantity must be finite")
            except (InvalidOperation, ValueError):
                issues.append(ValidationIssue("TakeoffRows", row_index, "quantity", "quantity must be a finite number"))

        for column in ("deductions_json", "evidence_json"):
            value = record.get(column)
            if _is_blank(value):
                continue
            try:
                parsed = json.loads(str(value))
            except json.JSONDecodeError:
                issues.append(ValidationIssue("TakeoffRows", row_index, column, "value must be valid JSON"))
                continue
            if not isinstance(parsed, (dict, list)):
                issues.append(ValidationIssue("TakeoffRows", row_index, column, "JSON value must be object or array"))

    return issues


def _private_path_issues(sheets: list[Worksheet]) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for sheet in sheets:
        for row in sheet.iter_rows():
            for cell in row:
                value = cell.value
                if not isinstance(value, str):
                    continue
                for pattern in PRIVATE_PATH_PATTERNS:
                    if pattern.search(value):
                        issues.append(
                            ValidationIssue(
                                sheet.title,
                                cell.row,
                                cell.column_letter,
                                "cell contains a local/private filesystem path",
                            )
                        )
                        break
    return issues


def _normalize(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _is_blank(value: Any) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate a 4th-phase example takeoff dataset workbook.")
    parser.add_argument("workbook", type=Path, help="Path to the private dataset .xlsx workbook")
    parser.add_argument("--min-rows", type=int, default=20)
    parser.add_argument("--max-rows", type=int, default=50)
    parser.add_argument(
        "--allow-empty-template",
        action="store_true",
        help="Validate workbook structure while allowing zero TakeoffRows records.",
    )
    args = parser.parse_args(argv)

    if not args.workbook.is_file():
        print(f"ERROR: workbook not found: {args.workbook}", file=sys.stderr)
        return 1

    issues = validate_workbook(
        args.workbook,
        min_rows=args.min_rows,
        max_rows=args.max_rows,
        allow_empty_template=args.allow_empty_template,
    )
    if issues:
        print(f"FAILED: {len(issues)} validation issue(s)")
        for issue in issues:
            print(f"- {issue.format()}")
        return 1

    print(f"OK: {args.workbook} passed example dataset validation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
