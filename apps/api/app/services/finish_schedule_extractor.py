from __future__ import annotations

from dataclasses import dataclass
import re
from collections.abc import Iterable

from app.models import DrawingSheet


HEADER_KEYWORDS = (
    "RM",
    "ROOM",
    "FLOOR",
    "BASE",
    "WALL",
    "CEILING",
)


@dataclass(frozen=True)
class RoomFinishCandidate:
    room_no: str
    room_name: str | None
    floor_finish: str | None
    base_finish: str | None
    wall_finish: str | None
    ceiling_finish: str | None
    height: str | None
    remarks: str | None
    confidence: float


def extract_room_finish_candidates(sheet: DrawingSheet) -> list[RoomFinishCandidate]:
    lines = _normalized_lines(sheet.text_content)
    if not lines:
        return []

    header_index = _find_header_index(lines)
    if header_index is None:
        return _extract_without_header(lines)

    candidates: list[RoomFinishCandidate] = []
    for line in lines[header_index + 1 :]:
        candidate = _parse_finish_row(line, confidence=0.65)
        if candidate is not None:
            candidates.append(candidate)
    return candidates


def _extract_without_header(lines: Iterable[str]) -> list[RoomFinishCandidate]:
    candidates: list[RoomFinishCandidate] = []
    for line in lines:
        candidate = _parse_finish_row(line, confidence=0.45)
        if candidate is not None:
            candidates.append(candidate)
    return candidates


def _find_header_index(lines: list[str]) -> int | None:
    for index, line in enumerate(lines):
        normalized = line.upper()
        keyword_count = sum(1 for keyword in HEADER_KEYWORDS if keyword in normalized)
        if keyword_count >= 4:
            return index
    return None


def _parse_finish_row(line: str, confidence: float) -> RoomFinishCandidate | None:
    if _looks_like_header_or_note(line):
        return None

    columns = _split_columns(line)
    if len(columns) < 6:
        return None

    room_no = columns[0]
    if not _looks_like_room_no(room_no):
        return None

    room_name = columns[1] if len(columns) > 1 else None
    floor_finish = columns[2] if len(columns) > 2 else None
    base_finish = columns[3] if len(columns) > 3 else None
    wall_finish = columns[4] if len(columns) > 4 else None
    ceiling_finish = columns[5] if len(columns) > 5 else None
    height = columns[6] if len(columns) > 6 else None
    remarks = " ".join(columns[7:]) if len(columns) > 7 else None

    return RoomFinishCandidate(
        room_no=room_no,
        room_name=room_name,
        floor_finish=floor_finish,
        base_finish=base_finish,
        wall_finish=wall_finish,
        ceiling_finish=ceiling_finish,
        height=height,
        remarks=remarks,
        confidence=confidence,
    )


def _normalized_lines(text: str) -> list[str]:
    return [
        line.strip(" \t|")
        for line in text.splitlines()
        if line.strip()
    ]


def _split_columns(line: str) -> list[str]:
    if "|" in line:
        return [part.strip() for part in line.split("|") if part.strip()]
    if "\t" in line:
        return [part.strip() for part in line.split("\t") if part.strip()]
    return [part.strip() for part in re.split(r"\s{2,}", line) if part.strip()]


def _looks_like_header_or_note(line: str) -> bool:
    normalized = line.upper()
    return normalized.startswith("RM ") or normalized.startswith("ROOM ") or normalized.startswith("NOTE")


def _looks_like_room_no(value: str) -> bool:
    return re.search(r"\d", value) is not None and len(value) <= 32
