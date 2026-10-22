from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from decimal import Decimal
from io import BytesIO

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from app.models import Measurement, ReviewStatus


DETAIL_HEADERS = [
    "Drawing No",
    "Room No",
    "Room Name",
    "Category",
    "Code",
    "Formula",
    "Quantity",
    "Unit",
    "Source Sheets",
    "Status",
    "Memo",
]

SUMMARY_HEADERS = [
    "Category",
    "Code",
    "Unit",
    "Total Quantity",
    "Source Sheets",
]

REVIEW_HEADERS = [
    "Drawing No",
    "Room No",
    "Room Name",
    "Category",
    "Code",
    "Formula",
    "Quantity",
    "Unit",
    "Status",
    "Memo",
]


@dataclass
class SummaryRow:
    category: str
    code: str
    unit: str
    total_quantity: Decimal
    source_sheets: list[str]


def build_measurements_workbook(measurements: list[Measurement]) -> BytesIO:
    workbook = Workbook()
    summary_sheet = workbook.active
    summary_sheet.title = "Summary"
    details_sheet = workbook.create_sheet("Details")
    review_sheet = workbook.create_sheet("Review")

    summary_rows = _build_summary_rows(measurements)
    _populate_summary_sheet(summary_sheet, summary_rows)
    _populate_details_sheet(details_sheet, measurements)
    _populate_review_sheet(review_sheet, measurements)

    output = BytesIO()
    workbook.save(output)
    output.seek(0)
    return output


def _build_summary_rows(measurements: list[Measurement]) -> list[SummaryRow]:
    grouped: OrderedDict[tuple[str, str, str], SummaryRow] = OrderedDict()
    for measurement in measurements:
        if measurement.status == ReviewStatus.REJECTED or measurement.quantity is None:
            continue
        key = (
            measurement.category,
            measurement.finish_code,
            measurement.unit or "",
        )
        if key not in grouped:
            grouped[key] = SummaryRow(
                category=measurement.category,
                code=measurement.finish_code,
                unit=measurement.unit or "",
                total_quantity=Decimal("0.00"),
                source_sheets=[],
            )

        row = grouped[key]
        row.total_quantity += measurement.quantity
        for source_sheet in _split_source_sheets(measurement.source_sheets):
            if source_sheet not in row.source_sheets:
                row.source_sheets.append(source_sheet)

    return sorted(grouped.values(), key=lambda row: (row.category, row.code, row.unit))


def _populate_summary_sheet(sheet, rows: list[SummaryRow]) -> None:
    sheet.append(SUMMARY_HEADERS)
    for row in rows:
        sheet.append(
            [
                row.category,
                row.code,
                row.unit,
                row.total_quantity,
                ", ".join(row.source_sheets),
            ]
        )
    _format_sheet(sheet, numeric_columns={4}, widths={1: 18, 2: 22, 3: 12, 4: 18, 5: 36})


def _populate_details_sheet(sheet, measurements: list[Measurement]) -> None:
    sheet.append(DETAIL_HEADERS)
    for measurement in measurements:
        sheet.append(
            [
                _drawing_no_from_source_sheets(measurement.source_sheets),
                measurement.room_no,
                measurement.room_name,
                measurement.category,
                measurement.finish_code,
                measurement.formula,
                measurement.quantity,
                measurement.unit,
                measurement.source_sheets,
                measurement.status.value,
                measurement.memo,
            ]
        )
    _format_sheet(
        sheet,
        numeric_columns={7},
        widths={1: 16, 2: 14, 3: 24, 4: 16, 5: 22, 6: 36, 7: 14, 8: 10, 9: 28, 10: 16, 11: 34},
    )


def _populate_review_sheet(sheet, measurements: list[Measurement]) -> None:
    sheet.append(REVIEW_HEADERS)
    review_measurements = sorted(
        (measurement for measurement in measurements if measurement.status != ReviewStatus.REJECTED),
        key=lambda measurement: (
            measurement.room_no or "",
            measurement.category,
            measurement.finish_code,
            measurement.id,
        ),
    )
    for measurement in review_measurements:
        sheet.append(
            [
                _drawing_no_from_source_sheets(measurement.source_sheets),
                measurement.room_no,
                measurement.room_name,
                measurement.category,
                measurement.finish_code,
                measurement.formula,
                measurement.quantity,
                _review_unit(measurement.unit),
                measurement.status.value,
                measurement.memo,
            ]
        )
    _format_sheet(
        sheet,
        numeric_columns={7},
        widths={1: 16, 2: 14, 3: 24, 4: 16, 5: 22, 6: 36, 7: 14, 8: 10, 9: 16, 10: 34},
    )


def _format_sheet(sheet, numeric_columns: set[int], widths: dict[int, int]) -> None:
    header_fill = PatternFill("solid", fgColor="172026")
    header_font = Font(color="FFFFFF", bold=True)
    header_alignment = Alignment(horizontal="center", vertical="center")
    body_alignment = Alignment(vertical="top", wrap_text=True)

    for cell in sheet[1]:
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = header_alignment

    sheet.freeze_panes = "A2"
    sheet.auto_filter.ref = sheet.dimensions

    for row in sheet.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = body_alignment
            if cell.column in numeric_columns:
                cell.number_format = "0.00"

    for index, width in widths.items():
        sheet.column_dimensions[get_column_letter(index)].width = width


def _drawing_no_from_source_sheets(source_sheets: str | None) -> str:
    source_sheet_list = _split_source_sheets(source_sheets)
    return source_sheet_list[0] if source_sheet_list else ""


def _split_source_sheets(source_sheets: str | None) -> list[str]:
    if not source_sheets:
        return []
    return [value.strip() for value in source_sheets.replace(";", ",").split(",") if value.strip()]


def _review_unit(unit: str | None) -> str | None:
    if unit == "m2":
        return "m²"
    return unit
