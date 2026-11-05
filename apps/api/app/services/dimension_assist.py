from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any

import fitz

from app.models import DrawingFile, DrawingSheet, DrawingSheetRole, Measurement, ReviewStatus, RoomFinish


PLAN_ROLES = {
    DrawingSheetRole.FLOOR_PLAN,
    DrawingSheetRole.ENLARGED_FLOOR_PLAN,
    DrawingSheetRole.CEILING_PLAN,
    DrawingSheetRole.PARTITION_PLAN,
}

DIMENSION_PATTERN = re.compile(
    r"""
    (?P<feet>\d+(?:\.\d+)?)\s*'\s*-?\s*(?P<inches>\d+(?:\.\d+)?)?\s*"?
    |
    (?P<number>(?<![\w.])\d+(?:\.\d+)?)(?:\s*(?P<metric_unit>mm|m)\b|(?![\w.]))
    """,
    re.VERBOSE,
)
ROOM_IDENTIFIER_PREFIX_PATTERN = re.compile(
    r"(?:\bROOM\s*(?:NO\.?|NUMBER|#)?|\bRM\.?\s*(?:NO\.?|#)?)\s*$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class RoomPageCandidateData:
    page_index: int
    sheet_no: str | None
    sheet_title: str | None
    sheet_role: DrawingSheetRole
    room_no: str | None
    room_name: str | None
    evidence: list[str]
    confidence: float


@dataclass(frozen=True)
class DimensionRegionData:
    x: float
    y: float
    width: float
    height: float
    image_width: float | None = None
    image_height: float | None = None
    zoom: float | None = None
    pan_x: float | None = None
    pan_y: float | None = None


@dataclass(frozen=True)
class DimensionCandidateData:
    raw_text: str
    normalized_value: Decimal | None
    normalized_unit: str | None
    unit_guess: str | None
    source_sheet: str | None
    page_index: int
    bbox: dict[str, float] | None
    confidence: float
    status: ReviewStatus
    warning: str | None = None


def build_room_page_candidates(
    sheets: list[DrawingSheet],
    room_finishes: list[RoomFinish],
    measurements: list[Measurement],
    room_query: str,
) -> tuple[list[RoomPageCandidateData], list[str]]:
    normalized_query = _normalize_search_text(room_query)
    warnings: list[str] = []
    if not normalized_query:
        return [], ["room_query is required."]

    matching_room_finishes = [
        row
        for row in room_finishes
        if _matches_room_identity(row.room_no, row.room_name, normalized_query)
    ]
    matching_measurements = [
        row
        for row in measurements
        if _matches_room_identity(row.room_no, row.room_name, normalized_query)
    ]

    candidate_by_page: dict[int, RoomPageCandidateData] = {}
    for sheet in sheets:
        evidence: list[str] = []
        confidence = 0.0
        text = _sheet_text(sheet)
        if _matches_room_text(text, normalized_query):
            evidence.append("sheet text matches room query")
            confidence = max(confidence, 0.82)

        for room_finish in matching_room_finishes:
            if room_finish.drawing_sheet_id == sheet.id:
                evidence.append(f"room finish #{room_finish.id} links to this sheet")
                confidence = max(confidence, 0.74)
            if room_finish.source_sheet_no and _same_sheet_no(room_finish.source_sheet_no, sheet.sheet_no):
                evidence.append(f"room finish #{room_finish.id} source sheet {room_finish.source_sheet_no}")
                confidence = max(confidence, 0.68)

        for measurement in matching_measurements:
            if sheet.sheet_no and _csv_contains_sheet(measurement.source_sheets, sheet.sheet_no):
                evidence.append(f"measurement #{measurement.id} source sheet {sheet.sheet_no}")
                confidence = max(confidence, 0.58)

        if not evidence:
            continue

        room_no, room_name = _best_room_identity(matching_room_finishes, matching_measurements)
        candidate_by_page[sheet.page_index] = RoomPageCandidateData(
            page_index=sheet.page_index,
            sheet_no=sheet.sheet_no,
            sheet_title=sheet.sheet_title,
            sheet_role=sheet.role,
            room_no=room_no,
            room_name=room_name,
            evidence=list(dict.fromkeys(evidence)),
            confidence=_boost_plan_role(confidence, sheet.role),
        )

    candidates = sorted(
        candidate_by_page.values(),
        key=lambda candidate: (
            0 if candidate.sheet_role in PLAN_ROLES else 1,
            -candidate.confidence,
            candidate.page_index,
        ),
    )
    if not candidates:
        warnings.append("No room page candidates found. Try sheet search or open the page manually.")
    return candidates, warnings


def extract_dimension_candidates(
    drawing_file: DrawingFile,
    sheet: DrawingSheet,
    region: DimensionRegionData | None,
) -> tuple[list[DimensionCandidateData], list[str]]:
    warnings: list[str] = []
    candidates = _extract_candidates_from_pdf_blocks(drawing_file, sheet, region, warnings)
    if not candidates:
        candidates = _extract_candidates_from_text(sheet.text_content, sheet, warnings)
    if not candidates:
        warnings.append("No dimension-like text candidates found. Enter values manually.")
    if region is None:
        warnings.append("No region was provided, so sheet-level text candidates were used.")
    return _dedupe_candidates(candidates), list(dict.fromkeys(warnings))


def _extract_candidates_from_pdf_blocks(
    drawing_file: DrawingFile,
    sheet: DrawingSheet,
    region: DimensionRegionData | None,
    warnings: list[str],
) -> list[DimensionCandidateData]:
    pdf_path = Path(drawing_file.stored_path)
    if not pdf_path.is_file():
        warnings.append("Stored PDF file was not found; falling back to sheet text.")
        return []

    try:
        with fitz.open(pdf_path) as document:
            if sheet.page_index < 0 or sheet.page_index >= document.page_count:
                warnings.append("Requested page index is outside the stored PDF.")
                return []
            page = document.load_page(sheet.page_index)
            blocks = page.get_text("blocks")
            page_rect = page.rect
    except Exception:
        warnings.append("Could not read PDF text blocks; falling back to sheet text.")
        return []

    candidates: list[DimensionCandidateData] = []
    for block in blocks:
        if len(block) < 5:
            continue
        text = str(block[4] or "")
        bbox = _scale_bbox(
            {
                "x": float(block[0]),
                "y": float(block[1]),
                "width": float(block[2] - block[0]),
                "height": float(block[3] - block[1]),
            },
            page_width=float(page_rect.width),
            page_height=float(page_rect.height),
            image_width=region.image_width if region else None,
            image_height=region.image_height if region else None,
        )
        if region is not None and not _bbox_near_region(bbox, region):
            continue
        confidence = 0.78 if region is not None and _bbox_intersects_region(bbox, region) else 0.62
        candidates.extend(_dimension_matches_to_candidates(text, sheet, bbox, confidence))

    if region is not None and not candidates:
        warnings.append("No PDF text block candidates overlapped the selected region; falling back to sheet text.")
    return candidates


def _extract_candidates_from_text(
    text: str,
    sheet: DrawingSheet,
    warnings: list[str],
) -> list[DimensionCandidateData]:
    if not text.strip():
        warnings.append("Sheet text is empty.")
        return []
    return _dimension_matches_to_candidates(text, sheet, None, 0.42)


def _dimension_matches_to_candidates(
    text: str,
    sheet: DrawingSheet,
    bbox: dict[str, float] | None,
    confidence: float,
) -> list[DimensionCandidateData]:
    candidates: list[DimensionCandidateData] = []
    for match in DIMENSION_PATTERN.finditer(text):
        raw_text = match.group(0).strip()
        if not raw_text:
            continue
        if match.group("number") is not None and _looks_like_room_identifier(text, match):
            continue
        normalized_value, unit_guess, warning = _normalize_dimension(raw_text, match)
        if normalized_value is None and not warning:
            continue
        candidates.append(
            DimensionCandidateData(
                raw_text=raw_text,
                normalized_value=normalized_value,
                normalized_unit="m" if normalized_value is not None else None,
                unit_guess=unit_guess,
                source_sheet=sheet.sheet_no,
                page_index=sheet.page_index,
                bbox=bbox,
                confidence=confidence if normalized_value is not None else min(confidence, 0.3),
                status=ReviewStatus.NEEDS_REVIEW,
                warning=warning,
            )
        )
    return candidates


def _looks_like_room_identifier(text: str, match: re.Match[str]) -> bool:
    prefix = text[max(0, match.start() - 32) : match.start()]
    return ROOM_IDENTIFIER_PREFIX_PATTERN.search(prefix) is not None


def _normalize_dimension(raw_text: str, match: re.Match[str]) -> tuple[Decimal | None, str | None, str | None]:
    feet = match.group("feet")
    if feet is not None:
        inches = Decimal(match.group("inches") or "0")
        meters = (Decimal(feet) * Decimal("0.3048")) + (inches * Decimal("0.0254"))
        return _round_decimal(meters), "ft-in", None

    number_text = match.group("number")
    if number_text is None:
        return None, None, "Could not normalize dimension text."

    value = Decimal(number_text)
    metric_unit = match.group('metric_unit')
    if metric_unit == 'mm':
        return _round_decimal(value / Decimal('1000')), 'mm', None
    if metric_unit == 'm':
        return _round_decimal(value), 'm', None
    if value >= Decimal("100"):
        return _round_decimal(value / Decimal("1000")), "mm", None
    if Decimal("0") < value < Decimal("100"):
        return _round_decimal(value), "m", None
    return None, None, "Dimension value must be positive."


def _round_decimal(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)


def _dedupe_candidates(candidates: list[DimensionCandidateData]) -> list[DimensionCandidateData]:
    unique: dict[tuple[str, int, str | None], DimensionCandidateData] = {}
    for candidate in candidates:
        key = (candidate.raw_text, candidate.page_index, candidate.source_sheet)
        existing = unique.get(key)
        if existing is None or candidate.confidence > existing.confidence:
            unique[key] = candidate
    return sorted(unique.values(), key=lambda candidate: (-candidate.confidence, candidate.raw_text))[:30]


def _scale_bbox(
    bbox: dict[str, float],
    *,
    page_width: float,
    page_height: float,
    image_width: float | None,
    image_height: float | None,
) -> dict[str, float]:
    if not image_width or not image_height or not page_width or not page_height:
        return bbox
    x_scale = image_width / page_width
    y_scale = image_height / page_height
    return {
        "x": bbox["x"] * x_scale,
        "y": bbox["y"] * y_scale,
        "width": bbox["width"] * x_scale,
        "height": bbox["height"] * y_scale,
    }


def _bbox_intersects_region(bbox: dict[str, float], region: DimensionRegionData) -> bool:
    return not (
        bbox["x"] + bbox["width"] < region.x
        or region.x + region.width < bbox["x"]
        or bbox["y"] + bbox["height"] < region.y
        or region.y + region.height < bbox["y"]
    )


def _bbox_near_region(bbox: dict[str, float], region: DimensionRegionData) -> bool:
    margin = max(region.width, region.height, 48) * 0.35
    expanded = DimensionRegionData(
        x=region.x - margin,
        y=region.y - margin,
        width=region.width + margin * 2,
        height=region.height + margin * 2,
        image_width=region.image_width,
        image_height=region.image_height,
    )
    return _bbox_intersects_region(bbox, expanded)


def _sheet_text(sheet: DrawingSheet) -> str:
    return " ".join(value for value in (sheet.sheet_no, sheet.sheet_title, sheet.role.value, sheet.text_content) if value)


def _matches_room_identity(room_no: str | None, room_name: str | None, normalized_query: str) -> bool:
    values = [_normalize_search_text(value or "") for value in (room_no, room_name)]
    return any(value and (normalized_query in value or value in normalized_query) for value in values)


def _matches_room_text(text: str, normalized_query: str) -> bool:
    normalized_text = _normalize_search_text(text)
    if not normalized_query:
        return False
    if normalized_query in normalized_text:
        return True
    tokens = normalized_query.split()
    if len(tokens) == 1 and tokens[0].isdigit():
        token = re.escape(tokens[0])
        return re.search(rf"\b(?:ROOM|RM|ROOM NO)\s+{token}\b", normalized_text) is not None
    return all(token in normalized_text for token in tokens)


def _best_room_identity(
    room_finishes: list[RoomFinish],
    measurements: list[Measurement],
) -> tuple[str | None, str | None]:
    for row in [*room_finishes, *measurements]:
        if row.room_no or row.room_name:
            return row.room_no, row.room_name
    return None, None


def _boost_plan_role(confidence: float, role: DrawingSheetRole) -> float:
    if role in PLAN_ROLES:
        return min(confidence + 0.08, 0.98)
    return confidence


def _same_sheet_no(left: str | None, right: str | None) -> bool:
    return bool(left and right and _normalize_sheet_no(left) == _normalize_sheet_no(right))


def _csv_contains_sheet(source_sheets: str | None, sheet_no: str) -> bool:
    normalized_sheet_no = _normalize_sheet_no(sheet_no)
    if not source_sheets or not normalized_sheet_no:
        return False
    return any(_normalize_sheet_no(item) == normalized_sheet_no for item in re.split(r"[,;]", source_sheets))


def _normalize_search_text(value: str) -> str:
    normalized = value.upper()
    normalized = re.sub(r"[^A-Z0-9]+", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip()


def _normalize_sheet_no(value: str) -> str:
    return re.sub(r"[^A-Z0-9]+", "", value.upper())


def dimension_region_from_mapping(value: Any) -> DimensionRegionData | None:
    if value is None:
        return None
    return DimensionRegionData(
        x=float(value.x),
        y=float(value.y),
        width=float(value.width),
        height=float(value.height),
        image_width=float(value.image_width) if value.image_width is not None else None,
        image_height=float(value.image_height) if value.image_height is not None else None,
        zoom=float(value.zoom) if value.zoom is not None else None,
        pan_x=float(value.pan_x) if value.pan_x is not None else None,
        pan_y=float(value.pan_y) if value.pan_y is not None else None,
    )
