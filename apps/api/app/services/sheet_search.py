from __future__ import annotations

import re
from collections.abc import Iterable

from app.models import DrawingSheet


def filter_sheets_by_keyword(sheets: Iterable[DrawingSheet], query: str | None) -> list[DrawingSheet]:
    normalized_query = _normalize_search_text(_legacy_query_term(query or ""))
    if not normalized_query:
        return list(sheets)

    return [
        sheet
        for sheet in sheets
        if _matches_keyword(_sheet_search_text(sheet), normalized_query)
    ]


def filter_sheets_by_sheet_no(sheets: Iterable[DrawingSheet], sheet_no: str | None) -> list[DrawingSheet]:
    normalized_sheet_no = _normalize_sheet_no(sheet_no or "")
    if not normalized_sheet_no:
        return list(sheets)

    return [
        sheet
        for sheet in sheets
        if _normalize_sheet_no(sheet.sheet_no or "") == normalized_sheet_no
    ]


def _sheet_search_text(sheet: DrawingSheet) -> str:
    role_value = sheet.role.value if sheet.role else None
    return " ".join(
        value
        for value in (
            sheet.sheet_no,
            sheet.sheet_title,
            role_value,
            sheet.text_content,
        )
        if value
    )


def _matches_keyword(value: str, normalized_query: str) -> bool:
    normalized_value = _normalize_search_text(value)
    query_tokens = normalized_query.split()
    if _looks_like_room_query(query_tokens):
        room_no = query_tokens[-1]
        return _matches_room_query(normalized_value, room_no)
    return normalized_query in normalized_value or all(token in normalized_value for token in query_tokens)


def _matches_room_query(normalized_value: str, room_no: str) -> bool:
    return (
        re.search(rf"\bROOM\s+{re.escape(room_no)}\b", normalized_value) is not None
        or re.search(rf"\bRM\s+{re.escape(room_no)}\b", normalized_value) is not None
        or re.search(rf"\b{re.escape(room_no)}\b", normalized_value) is not None
    )


def _looks_like_room_query(query_tokens: list[str]) -> bool:
    return (
        len(query_tokens) == 2
        and query_tokens[0] in {"ROOM", "RM"}
        and query_tokens[1].isdigit()
    ) or (len(query_tokens) == 1 and query_tokens[0].isdigit())


def _normalize_search_text(value: str) -> str:
    normalized = value.upper()
    normalized = re.sub(r"[^A-Z0-9]+", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip()


def _normalize_sheet_no(value: str) -> str:
    return re.sub(r"[^A-Z0-9]+", "", value.upper())


def _legacy_query_term(query: str) -> str:
    if "," not in query:
        return query
    return next((part.strip() for part in query.split(",") if part.strip()), "")
