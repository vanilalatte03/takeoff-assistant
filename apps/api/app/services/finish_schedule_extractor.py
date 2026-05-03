from __future__ import annotations

from dataclasses import dataclass
import re
from collections.abc import Iterable, Sequence
from typing import Any

from app.models import DrawingSheet


HEADER_KEYWORDS = (
    "RM",
    "ROOM",
    "FLOOR",
    "BASE",
    "WALL",
    "CEILING",
)
WALL_GROUPS = ("north_wall", "east_wall", "south_wall", "west_wall")
FINISH_GROUPS = ("floor", "base", *WALL_GROUPS, "ceiling")
HEADER_NOISE = {
    "EXST",
    "REPL",
    "REPL/",
    "NEW",
    "SUBSTRATE",
    "FINISH",
    "ROOM",
    "NUMBER",
    "ROOM NAMES",
    "FLOOR",
    "BASE",
    "NORTH WALL",
    "EAST WALL",
    "SOUTH WALL",
    "WEST WALL",
    "CEILING",
    "HEIGHT",
    "REMARKS",
}


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


@dataclass(frozen=True)
class TextBlock:
    x0: float
    y0: float
    x1: float
    y1: float
    text: str


@dataclass(frozen=True)
class RoomAnchor:
    room_no: str
    y: float
    room_name: str | None = None


@dataclass(frozen=True)
class ColumnWindow:
    x0: float
    x1: float

    def contains(self, block: TextBlock) -> bool:
        center_x = (block.x0 + block.x1) / 2
        return self.x0 <= center_x <= self.x1


def extract_room_finish_candidates(
    sheet: DrawingSheet,
    page_blocks: Sequence[Sequence[Any]] | None = None,
) -> list[RoomFinishCandidate]:
    if page_blocks:
        block_candidates = extract_room_finish_candidates_from_blocks(page_blocks)
        if block_candidates:
            return block_candidates

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


def extract_room_finish_candidates_from_blocks(page_blocks: Sequence[Sequence[Any]]) -> list[RoomFinishCandidate]:
    blocks = _to_text_blocks(page_blocks)
    if not blocks:
        return []

    title_block = _find_first_block(blocks, "INTERIOR FINISH SCHEDULE")
    if title_block is None:
        return []

    table_end_y = _find_table_end_y(blocks, title_block)
    table_blocks = [
        block
        for block in blocks
        if block.y0 >= title_block.y0 and block.y0 < table_end_y
    ]

    room_header = _find_room_header(table_blocks)
    if room_header is None:
        return []

    anchors = _find_room_anchors(table_blocks, room_header, table_end_y)
    if not anchors:
        return []

    first_row_y = min(anchor.y for anchor in anchors)
    header_blocks = [
        block
        for block in table_blocks
        if block.y0 > title_block.y0 and block.y0 < first_row_y
    ]
    windows = _build_column_windows(header_blocks, room_header)
    if not _has_required_table_evidence(windows):
        return []

    room_name_window = ColumnWindow(room_header.x0, windows["floor"].x0 - 8)
    right_bound = windows.get("remarks", windows["height"]).x1 + 120
    candidates: list[RoomFinishCandidate] = []
    seen_room_nos: set[str] = set()
    for anchor in anchors:
        if anchor.room_no in seen_room_nos:
            continue
        row_blocks = _row_blocks(table_blocks, anchor.y, room_header.x0 - 40, right_bound)
        candidate = _candidate_from_row(anchor, row_blocks, room_name_window, windows)
        if candidate:
            candidates.append(candidate)
            seen_room_nos.add(anchor.room_no)
    return candidates


def _to_text_blocks(page_blocks: Sequence[Sequence[Any]]) -> list[TextBlock]:
    blocks: list[TextBlock] = []
    for raw_block in page_blocks:
        if len(raw_block) < 5:
            continue
        text = str(raw_block[4])
        if not text.strip():
            continue
        blocks.append(
            TextBlock(
                x0=float(raw_block[0]),
                y0=float(raw_block[1]),
                x1=float(raw_block[2]),
                y1=float(raw_block[3]),
                text=text,
            )
        )
    return sorted(blocks, key=lambda block: (block.y0, block.x0))


def _find_first_block(blocks: list[TextBlock], phrase: str) -> TextBlock | None:
    return next((block for block in blocks if _contains_compact(block.text, phrase)), None)


def _find_table_end_y(blocks: list[TextBlock], title_block: TextBlock) -> float:
    end_markers = [
        block.y0
        for block in blocks
        if block.y0 > title_block.y0
        and (
            _contains_compact(block.text, "ABBREVIATION")
            or _contains_compact(block.text, "EXTERIOR FINISH SCHEDULE")
        )
    ]
    return min(end_markers) if end_markers else max(block.y1 for block in blocks) + 1


def _find_room_header(blocks: list[TextBlock]) -> TextBlock | None:
    for block in blocks:
        compact = _compact(block.text)
        if "ROOMNUMBER" in compact and "ROOMNAMES" in compact:
            return block
    return None


def _find_room_anchors(blocks: list[TextBlock], room_header: TextBlock, table_end_y: float) -> list[RoomAnchor]:
    anchors: list[RoomAnchor] = []
    room_no_left = room_header.x0 - 30
    room_no_right = room_header.x0 + 110
    for block in blocks:
        if block.y0 <= room_header.y1 or block.y0 >= table_end_y:
            continue
        if block.x0 < room_no_left or block.x0 > room_no_right:
            continue
        anchor = _room_anchor_from_block(block)
        if anchor:
            anchors.append(anchor)
    return sorted(anchors, key=lambda anchor: anchor.y)


def _room_anchor_from_block(block: TextBlock) -> RoomAnchor | None:
    lines = _block_lines(block)
    room_no_lines = [line for line in lines if _looks_like_room_no(line)]
    if not room_no_lines:
        return None
    room_no = room_no_lines[-1]
    room_name_lines = [line for line in lines if line != room_no and not _looks_like_room_no(line)]
    room_name = _join_unique(room_name_lines)
    return RoomAnchor(room_no=room_no, y=block.y0, room_name=room_name)


def _build_column_windows(header_blocks: list[TextBlock], room_header: TextBlock) -> dict[str, ColumnWindow]:
    label_blocks = {
        "floor": _find_label_block(header_blocks, "FLOOR"),
        "base": _find_label_block(header_blocks, "BASE"),
        "north_wall": _find_label_block(header_blocks, "NORTH WALL"),
        "east_wall": _find_label_block(header_blocks, "EAST WALL"),
        "south_wall": _find_label_block(header_blocks, "SOUTH WALL"),
        "west_wall": _find_label_block(header_blocks, "WEST WALL"),
        "ceiling": _find_label_block(header_blocks, "CEILING"),
        "height": _find_label_block(header_blocks, "HEIGHT"),
        "remarks": _find_label_block(header_blocks, "REMARKS"),
    }
    centers = {
        name: (block.x0 + block.x1) / 2
        for name, block in label_blocks.items()
        if block is not None
    }
    extents: dict[str, list[float]] = {
        name: [block.x0, block.x1]
        for name, block in label_blocks.items()
        if block is not None
    }

    for block in header_blocks:
        if not _looks_like_subheader_block(block):
            continue
        nearest_group = _nearest_group(block, centers)
        if nearest_group is None:
            continue
        extent = extents.setdefault(nearest_group, [block.x0, block.x1])
        extent[0] = min(extent[0], block.x0)
        extent[1] = max(extent[1], block.x1)

    for name, padding in {"height": 42, "remarks": 90}.items():
        if name in extents:
            extents[name][0] -= padding
            extents[name][1] += padding

    windows = {
        name: ColumnWindow(x0=values[0] - 4, x1=values[1] + 4)
        for name, values in extents.items()
    }
    if "floor" in windows:
        windows["floor"] = ColumnWindow(max(room_header.x1 + 20, windows["floor"].x0), windows["floor"].x1)
    return windows


def _find_label_block(blocks: list[TextBlock], phrase: str) -> TextBlock | None:
    normalized_phrase = _normalize_label(phrase)
    for block in blocks:
        lines = [_normalize_label(line) for line in _block_lines(block)]
        if normalized_phrase in lines or _contains_compact(block.text, phrase):
            return block
    return None


def _looks_like_subheader_block(block: TextBlock) -> bool:
    normalized = _normalize_label(block.text)
    return any(token in normalized for token in ("SUBSTRATE", "FINISH", "EXST", "REPL", "NEW"))


def _nearest_group(block: TextBlock, centers: dict[str, float]) -> str | None:
    if not centers:
        return None
    center_x = (block.x0 + block.x1) / 2
    return min(centers, key=lambda name: abs(centers[name] - center_x))


def _has_required_table_evidence(windows: dict[str, ColumnWindow]) -> bool:
    return all(key in windows for key in ("floor", "base", "ceiling"))


def _row_blocks(blocks: list[TextBlock], row_y: float, left_bound: float, right_bound: float) -> list[TextBlock]:
    return [
        block
        for block in blocks
        if block.x0 >= left_bound
        and block.x0 <= right_bound
        and block.y0 <= row_y + 8
        and block.y1 >= row_y - 8
    ]


def _candidate_from_row(
    anchor: RoomAnchor,
    row_blocks: list[TextBlock],
    room_name_window: ColumnWindow,
    windows: dict[str, ColumnWindow],
) -> RoomFinishCandidate | None:
    room_name = anchor.room_name or _join_unique(_tokens_in_window(row_blocks, room_name_window, exclude_room_nos=True))
    floor_finish = _finish_value(_tokens_in_window(row_blocks, windows["floor"]))
    base_finish = _finish_value(_tokens_in_window(row_blocks, windows["base"]))
    wall_finish = _wall_finish(row_blocks, windows)
    ceiling_finish = _finish_value(_tokens_in_window(row_blocks, windows["ceiling"]))
    height = _finish_value(_tokens_in_window(row_blocks, windows["height"])) if "height" in windows else None
    remarks = _join_unique(_tokens_in_window(row_blocks, windows["remarks"])) if "remarks" in windows else None

    if not any((floor_finish, base_finish, wall_finish, ceiling_finish, height, remarks)):
        return None

    return RoomFinishCandidate(
        room_no=anchor.room_no,
        room_name=room_name,
        floor_finish=floor_finish,
        base_finish=base_finish,
        wall_finish=wall_finish,
        ceiling_finish=ceiling_finish,
        height=height,
        remarks=remarks,
        confidence=0.72,
    )


def _tokens_in_window(
    row_blocks: list[TextBlock],
    window: ColumnWindow,
    *,
    exclude_room_nos: bool = False,
) -> list[str]:
    tokens: list[str] = []
    for block in sorted((block for block in row_blocks if window.contains(block)), key=lambda value: value.x0):
        for token in _block_value_tokens(block):
            if exclude_room_nos and _looks_like_room_no(token):
                continue
            if token not in tokens:
                tokens.append(token)
    return tokens


def _finish_value(tokens: list[str]) -> str | None:
    values = [token for token in tokens if token != "-"]
    if not values:
        return None
    return values[-1]


def _wall_finish(row_blocks: list[TextBlock], windows: dict[str, ColumnWindow]) -> str | None:
    ordered_tokens: list[str] = []
    for group in WALL_GROUPS:
        if group not in windows:
            continue
        for token in _tokens_in_window(row_blocks, windows[group]):
            if token != "-" and token not in ordered_tokens:
                ordered_tokens.append(token)
    return " / ".join(ordered_tokens) if ordered_tokens else None


def _block_value_tokens(block: TextBlock) -> list[str]:
    lines = _block_lines(block)
    tokens: list[str] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        if line.endswith("/") and index + 1 < len(lines):
            line = f"{line.rstrip('/').strip()} / {lines[index + 1]}"
            index += 2
        else:
            index += 1
        cleaned = _clean_value_token(line)
        if cleaned and cleaned not in tokens:
            tokens.append(cleaned)
    return tokens


def _clean_value_token(value: str) -> str | None:
    cleaned = re.sub(r"\s+", " ", value).strip(" \t|")
    if cleaned.endswith("/"):
        cleaned = cleaned.rstrip("/").strip()
    if not cleaned:
        return None
    normalized = _normalize_label(cleaned)
    if normalized in HEADER_NOISE:
        return None
    if normalized.startswith("SCALE") or "SHEET KEYNOTE" in normalized:
        return None
    return cleaned.upper()


def _block_lines(block: TextBlock) -> list[str]:
    return [
        re.sub(r"\s+", " ", line).strip(" \t|")
        for line in block.text.splitlines()
        if line.strip()
    ]


def _join_unique(values: Iterable[str | None]) -> str | None:
    unique_values: list[str] = []
    for value in values:
        if value and value not in unique_values:
            unique_values.append(value)
    return " / ".join(unique_values) if unique_values else None


def _contains_compact(value: str, phrase: str) -> bool:
    return _compact(phrase) in _compact(value)


def _compact(value: str) -> str:
    return re.sub(r"[^A-Z0-9]+", "", value.upper())


def _normalize_label(value: str) -> str:
    normalized = value.upper().replace("&", " AND ")
    normalized = re.sub(r"[/\\|_-]+", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip()


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
    normalized = re.sub(r"\s+", " ", value.upper()).strip()
    return (
        len(normalized) <= 32
        and re.fullmatch(r"\d+[A-Z]?(?:\s*(?:,|/|&|~|-|TO)\s*\d+[A-Z]?)*", normalized) is not None
    )
