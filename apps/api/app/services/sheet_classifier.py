from __future__ import annotations

import re
from collections.abc import Iterable

from app.models import DrawingSheet, DrawingSheetRole


INDEX_PAGE_TITLES = (
    "INDEX OF DRAWINGS",
    "SCHEDULE OF DRAWINGS",
)
FLOOR_PLAN_EXCLUSIONS = (
    "REMOVAL",
    "DEMOLITION",
    "DEMO",
    "ENLARGED",
    "PARTITION",
)


def classify_and_apply_sheet_roles(sheets: Iterable[DrawingSheet]) -> list[DrawingSheet]:
    ordered_sheets = sorted(sheets, key=lambda sheet: sheet.page_index)
    for sheet in ordered_sheets:
        sheet.role = classify_sheet_role(sheet.sheet_title, sheet.text_content)
    return ordered_sheets


def classify_sheet_role(sheet_title: str | None, text_content: str | None = None) -> DrawingSheetRole:
    title = _normalize(sheet_title or "")
    text = _normalize(text_content or "")
    if not title and not text:
        return DrawingSheetRole.UNKNOWN

    if not title and _contains_any(text, INDEX_PAGE_TITLES):
        return DrawingSheetRole.UNKNOWN

    if title and text_content and _is_finish_schedule(title) and not _has_finish_schedule_page_evidence(text_content):
        return DrawingSheetRole.UNKNOWN

    for candidate in _classification_candidates(sheet_title, text_content):
        role = _classify_candidate(candidate)
        if role == DrawingSheetRole.FINISH_SCHEDULE and not _has_finish_schedule_candidate_evidence(candidate, text_content or ""):
            continue
        if role != DrawingSheetRole.UNKNOWN:
            return role
    return DrawingSheetRole.UNKNOWN


def _classification_candidates(sheet_title: str | None, text_content: str | None) -> list[str]:
    candidates: list[str] = []
    if sheet_title:
        candidates.append(_normalize(sheet_title))
    for line in (text_content or "").splitlines():
        normalized = _normalize(line)
        if normalized and _looks_like_role_candidate(normalized):
            candidates.append(normalized)
    return candidates


def _classify_candidate(classification_text: str) -> DrawingSheetRole:
    if _is_finish_schedule(classification_text):
        return DrawingSheetRole.FINISH_SCHEDULE
    if _contains_phrase(classification_text, "ENLARGED FLOOR PLAN"):
        return DrawingSheetRole.ENLARGED_FLOOR_PLAN
    if _contains_phrase(classification_text, "REFLECTED CEILING PLAN") or _contains_phrase(
        classification_text,
        "CEILING PLAN",
    ):
        return DrawingSheetRole.CEILING_PLAN
    if _contains_word(classification_text, "PARTITION") and _contains_detail(classification_text):
        return DrawingSheetRole.PARTITION_DETAIL
    if _contains_word(classification_text, "PARTITION") and _contains_word(classification_text, "PLAN"):
        return DrawingSheetRole.PARTITION_PLAN
    if _contains_word(classification_text, "DOOR") and _contains_word(classification_text, "SCHEDULE"):
        return DrawingSheetRole.DOOR_SCHEDULE
    if (
        _contains_word(classification_text, "WINDOW") or _contains_word(classification_text, "LOUVER")
    ) and _contains_word(classification_text, "SCHEDULE"):
        return DrawingSheetRole.WINDOW_SCHEDULE
    if _contains_phrase(classification_text, "FLOOR PLAN") and not _contains_any(
        classification_text,
        FLOOR_PLAN_EXCLUSIONS,
    ):
        return DrawingSheetRole.FLOOR_PLAN
    if _contains_detail(classification_text):
        return DrawingSheetRole.DETAIL
    return DrawingSheetRole.UNKNOWN


def _is_finish_schedule(value: str) -> bool:
    return (
        _contains_compact(value, "INTERIOR FINISH SCHEDULE")
        or _contains_compact(value, "EXTERIOR FINISH SCHEDULE")
        or (_contains_word(value, "FINISH") and _contains_word(value, "SCHEDULE"))
    )


def _has_finish_schedule_candidate_evidence(candidate: str, text_content: str) -> bool:
    if not text_content:
        return _contains_finish_schedule_title(candidate)
    return _has_finish_schedule_page_evidence(text_content) or _contains_finish_schedule_title(candidate)


def _has_finish_schedule_page_evidence(text_content: str) -> bool:
    lines = [_normalize(line) for line in text_content.splitlines() if line.strip()]
    non_reference_lines = [line for line in lines if not _is_reference_line(line)]
    if any(_contains_finish_schedule_title(line) for line in non_reference_lines):
        return True
    return _has_finish_schedule_table_evidence(non_reference_lines)


def _contains_finish_schedule_title(value: str) -> bool:
    return (
        _contains_compact(value, "EXTERIOR INTERIOR FINISH SCHEDULE")
        or _contains_compact(value, "EXTERIOR AND INTERIOR FINISH SCHEDULE")
        or _contains_compact(value, "INTERIOR FINISH SCHEDULE")
        or _contains_compact(value, "INTR EXT FINISH SCHEDULE")
    )


def _has_finish_schedule_table_evidence(lines: list[str]) -> bool:
    text = " ".join(lines)
    required_terms = ("ROOM", "FLOOR", "BASE", "CEILING")
    return "FINISH" in text and all(term in text for term in required_terms)


def _looks_like_role_candidate(value: str) -> bool:
    if _is_reference_line(value):
        return False
    if _contains_any(
        value,
        (
            "GENERAL SHEET NOTES",
            "SHEET KEYNOTES",
            "LEGEND",
            "SCALE",
        ),
    ):
        return False
    if len(value) > 120:
        return False
    return any(
        marker in value
        for marker in (
            "PLAN",
            "SCHEDULE",
            "DETAIL",
            "ELEVATION",
            "SECTION",
        )
    ) or _contains_compact(value, "INTERIOR FINISH SCHEDULE")


def _is_reference_line(value: str) -> bool:
    return bool(re.search(r"\b(REFER|SEE)\s+TO\b", value))


def _normalize(value: str) -> str:
    normalized = value.upper()
    normalized = normalized.replace("&", " AND ")
    normalized = re.sub(r"[/\\|_-]+", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip()


def _contains_phrase(value: str, phrase: str) -> bool:
    return _normalize(phrase) in value


def _contains_any(value: str, candidates: Iterable[str]) -> bool:
    return any(_normalize(candidate) in value for candidate in candidates)


def _contains_word(value: str, word: str) -> bool:
    return re.search(rf"\b{re.escape(_normalize(word))}\b", value) is not None


def _contains_detail(value: str) -> bool:
    return re.search(r"\bDETAILS?\b", value) is not None


def _contains_compact(value: str, phrase: str) -> bool:
    return re.sub(r"[^A-Z0-9]+", "", phrase.upper()) in re.sub(r"[^A-Z0-9]+", "", value.upper())
