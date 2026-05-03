from __future__ import annotations

from dataclasses import dataclass
import re
from collections.abc import Iterable

from app.models import DrawingSheet, ReviewStatus


INDEX_PAGE_TITLES = (
    "INDEX OF DRAWINGS",
    "SCHEDULE OF DRAWINGS",
)
SHEET_NO_PATTERN = re.compile(r"(?<![A-Z0-9])([A-Z]{1,2}\s*-?\s*\d{3}[A-Z]?)(?![A-Z0-9])")


@dataclass(frozen=True)
class SheetDetection:
    sheet_no: str | None
    sheet_title: str | None
    confidence: float


def detect_and_apply_sheet_metadata(sheets: Iterable[DrawingSheet]) -> list[DrawingSheet]:
    ordered_sheets = sorted(sheets, key=lambda sheet: sheet.page_index)
    index_titles = _build_index_title_map(ordered_sheets)
    index_sequence = _build_index_sequence(ordered_sheets)
    non_index_position = 0

    for sheet in ordered_sheets:
        detection = detect_sheet_metadata(sheet.text_content, index_titles)
        if not _is_index_page(sheet.text_content):
            if detection.confidence <= 0.3 and non_index_position < len(index_sequence):
                index_detection = index_sequence[non_index_position]
                detection = SheetDetection(
                    sheet_no=index_detection.sheet_no,
                    sheet_title=index_detection.sheet_title,
                    confidence=max(detection.confidence, 0.45),
                )
            non_index_position += 1
        sheet.sheet_no = detection.sheet_no
        sheet.sheet_title = detection.sheet_title
        sheet.sheet_detection_confidence = detection.confidence
        if detection.confidence == 0:
            sheet.status = ReviewStatus.NEEDS_REVIEW
        elif sheet.status == ReviewStatus.NEEDS_REVIEW and sheet.text_content.strip():
            sheet.status = ReviewStatus.DRAFT

    return ordered_sheets


def detect_sheet_metadata(text: str, index_titles: dict[str, str] | None = None) -> SheetDetection:
    index_titles = index_titles or {}
    is_index = _is_index_page(text)
    title_block_detection = _detect_from_title_block(text, is_index_page=is_index)
    if title_block_detection.sheet_no is None:
        return title_block_detection

    index_title = index_titles.get(_canonical_sheet_no(title_block_detection.sheet_no))
    if index_title:
        return SheetDetection(
            sheet_no=title_block_detection.sheet_no,
            sheet_title=index_title,
            confidence=max(title_block_detection.confidence, 0.95),
        )

    return title_block_detection


def _build_index_title_map(sheets: Iterable[DrawingSheet]) -> dict[str, str]:
    titles: dict[str, str] = {}
    for parsed in _index_detections(sheets):
        if parsed.sheet_no and parsed.sheet_title:
            titles.setdefault(_canonical_sheet_no(parsed.sheet_no), parsed.sheet_title)
    return titles


def _build_index_sequence(sheets: Iterable[DrawingSheet]) -> list[SheetDetection]:
    return [
        parsed
        for parsed in _index_detections(sheets)
        if parsed.sheet_no and parsed.sheet_title
    ]


def _index_detections(sheets: Iterable[DrawingSheet]) -> list[SheetDetection]:
    detections: list[SheetDetection] = []
    for sheet in sheets:
        if not _is_index_page(sheet.text_content):
            continue
        for line in _normalized_lines(sheet.text_content):
            parsed = _parse_sheet_line(line)
            if parsed.sheet_no and parsed.sheet_title:
                detections.append(parsed)
    return detections


def _detect_from_title_block(text: str, is_index_page: bool) -> SheetDetection:
    lines = _normalized_lines(text)
    if not lines:
        return SheetDetection(sheet_no=None, sheet_title=None, confidence=0)

    if is_index_page:
        for line in lines:
            parsed = _parse_sheet_line(line)
            if parsed.sheet_no and parsed.sheet_title and _contains_index_title(parsed.sheet_title):
                return SheetDetection(parsed.sheet_no, parsed.sheet_title, 0.85)
        return SheetDetection(sheet_no=None, sheet_title=None, confidence=0)

    for line in lines:
        parsed = _parse_sheet_line(line)
        if parsed.sheet_no and parsed.sheet_title:
            return SheetDetection(parsed.sheet_no, parsed.sheet_title, 0.8)

    for index, line in enumerate(lines):
        sheet_no = _parse_standalone_sheet_no(line)
        if not sheet_no:
            continue
        title = _nearest_title_line(lines, index)
        if title:
            return SheetDetection(sheet_no=sheet_no, sheet_title=title, confidence=0.65)
        return SheetDetection(sheet_no=sheet_no, sheet_title=None, confidence=0.3)

    return SheetDetection(sheet_no=None, sheet_title=None, confidence=0)


def _is_index_page(text: str) -> bool:
    upper_text = text.upper()
    return any(title in upper_text for title in INDEX_PAGE_TITLES)


def _contains_index_title(text: str) -> bool:
    upper_text = text.upper()
    return any(title in upper_text for title in INDEX_PAGE_TITLES)


def _normalized_lines(text: str) -> list[str]:
    return [
        re.sub(r"\s+", " ", line).strip(" \t:-|")
        for line in text.splitlines()
        if line.strip()
    ]


def _parse_sheet_line(line: str) -> SheetDetection:
    match = SHEET_NO_PATTERN.search(line.upper())
    if not match:
        return SheetDetection(sheet_no=None, sheet_title=None, confidence=0)

    sheet_no = _normalize_sheet_no(match.group(1))
    title = _clean_title(line[match.end() :])
    if not title:
        return SheetDetection(sheet_no=sheet_no, sheet_title=None, confidence=0)
    return SheetDetection(sheet_no=sheet_no, sheet_title=title, confidence=0.8)


def _parse_standalone_sheet_no(line: str) -> str | None:
    clean_line = line.upper().strip()
    match = SHEET_NO_PATTERN.fullmatch(clean_line)
    if not match:
        return None
    return _normalize_sheet_no(match.group(1))


def _nearest_title_line(lines: list[str], sheet_no_index: int) -> str | None:
    for offset in (1, -1, 2, -2):
        candidate_index = sheet_no_index + offset
        if candidate_index < 0 or candidate_index >= len(lines):
            continue
        title = _clean_title(lines[candidate_index])
        if title and not SHEET_NO_PATTERN.search(title):
            return title
    return None


def _clean_title(value: str) -> str | None:
    title = re.sub(r"\s+", " ", value).strip(" \t:-|.")
    if not title:
        return None
    upper_title = title.upper()
    if upper_title in {"SHEET", "SHEET NO", "SHEET NUMBER", "DRAWING NO", "DRAWING NUMBER"}:
        return None
    if not re.search(r"[A-Z]", upper_title):
        return None
    return upper_title


def _normalize_sheet_no(value: str) -> str:
    return re.sub(r"\s+", "", value.upper())


def _canonical_sheet_no(value: str) -> str:
    return _normalize_sheet_no(value)
