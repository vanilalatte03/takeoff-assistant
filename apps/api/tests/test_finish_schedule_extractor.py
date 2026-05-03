from pathlib import Path

import pytest

from app.models import DrawingSheet
from app.services.finish_schedule_extractor import extract_room_finish_candidates, extract_room_finish_candidates_from_blocks


def test_extract_room_finish_candidates_from_pipe_delimited_schedule() -> None:
    sheet = DrawingSheet(
        drawing_file_id=1,
        page_index=0,
        text_content="""
        RM NOS | ROOM NAMES | FLOOR | BASE | INTERIOR WALL | CEILING | HGT
        110 | OFFICE | VCT | RB | GWB | ACT | 9'-0"
        111 | CORRIDOR | LVT | RB | PT | ACT | 8'-6" | VERIFY
        """,
    )

    candidates = extract_room_finish_candidates(sheet)

    assert len(candidates) == 2
    assert candidates[0].room_no == "110"
    assert candidates[0].room_name == "OFFICE"
    assert candidates[0].floor_finish == "VCT"
    assert candidates[0].base_finish == "RB"
    assert candidates[0].wall_finish == "GWB"
    assert candidates[0].ceiling_finish == "ACT"
    assert candidates[0].height == "9'-0\""
    assert candidates[0].confidence == 0.65
    assert candidates[1].remarks == "VERIFY"


def test_extract_room_finish_candidates_from_multiple_space_columns() -> None:
    sheet = DrawingSheet(
        drawing_file_id=1,
        page_index=0,
        text_content="""
        RM NOS    ROOM NAMES    FLOOR    BASE    INTERIOR WALL    CEILING    HGT
        210       TOILET        TILE     TILE    TILE             GYP        8'-0"
        """,
    )

    candidates = extract_room_finish_candidates(sheet)

    assert len(candidates) == 1
    assert candidates[0].room_no == "210"
    assert candidates[0].room_name == "TOILET"
    assert candidates[0].floor_finish == "TILE"
    assert candidates[0].base_finish == "TILE"
    assert candidates[0].wall_finish == "TILE"
    assert candidates[0].ceiling_finish == "GYP"
    assert candidates[0].height == "8'-0\""


def test_extract_room_finish_candidates_returns_empty_for_unparseable_text() -> None:
    sheet = DrawingSheet(
        drawing_file_id=1,
        page_index=0,
        text_content="This finish schedule page did not preserve table text in row order.",
    )

    assert extract_room_finish_candidates(sheet) == []


def test_extract_room_finish_candidates_from_sample_like_blocks() -> None:
    blocks = [
        (900, 60, 1400, 85, "I N T E R I O R    F I N I S H    S C H E D U L E", 0, 0),
        (460, 108, 505, 118, "FLOOR", 0, 0),
        (405, 135, 580, 145, "SUBSTRATE\nFINISH", 0, 0),
        (635, 108, 665, 118, "BASE", 0, 0),
        (610, 135, 690, 145, "FINISH", 0, 0),
        (780, 108, 845, 118, "NORTH WALL", 0, 0),
        (725, 135, 905, 145, "SUBSTRATE\nFINISH", 0, 0),
        (1000, 108, 1055, 118, "EAST WALL", 0, 0),
        (945, 135, 1120, 145, "SUBSTRATE\nFINISH", 0, 0),
        (1210, 108, 1275, 118, "SOUTH WALL", 0, 0),
        (1160, 135, 1335, 145, "SUBSTRATE\nFINISH", 0, 0),
        (1430, 108, 1488, 118, "WEST WALL", 0, 0),
        (1375, 135, 1550, 145, "SUBSTRATE\nFINISH", 0, 0),
        (1655, 108, 1695, 118, "CEILING", 0, 0),
        (1590, 135, 1770, 145, "SUBSTRATE\nFINISH", 0, 0),
        (1790, 149, 1830, 159, "HEIGHT", 0, 0),
        (2028, 135, 2075, 145, "REMARKS", 0, 0),
        (115, 129, 245, 151, "ROOM\nNUMBER\nROOM NAMES", 0, 0),
        (127, 190, 229, 199, "VESTIBULE\n101", 0, 0),
        (504, 190, 523, 199, "VCT", 0, 0),
        (554, 190, 583, 199, "VCT-1", 0, 0),
        (612, 190, 690, 199, "VCB\nVCB-1", 0, 0),
        (718, 190, 741, 199, "GWB", 0, 0),
        (823, 190, 899, 199, "P-2\nPAINT", 0, 0),
        (934, 190, 957, 199, "GWB", 0, 0),
        (1039, 190, 1068, 199, "PAINT", 0, 0),
        (1150, 190, 1173, 199, "GWB", 0, 0),
        (1255, 190, 1284, 199, "PAINT", 0, 0),
        (1366, 190, 1389, 199, "GWB", 0, 0),
        (1471, 190, 1500, 199, "PAINT", 0, 0),
        (1582, 190, 1605, 199, "GWB", 0, 0),
        (1687, 190, 1764, 199, "P-1\nPAINT", 0, 0),
        (1799, 190, 1821, 199, "2450", 0, 0),
        (127, 217, 143, 226, "101~106", 0, 0),
        (177, 217, 255, 226, "MULTI ROOM", 0, 0),
        (504, 217, 523, 226, "VCT", 0, 0),
        (554, 217, 583, 226, "VCT-1", 0, 0),
        (612, 217, 690, 226, "VCB\nVCB-1", 0, 0),
        (718, 217, 741, 226, "GWB", 0, 0),
        (934, 217, 957, 226, "GWB", 0, 0),
        (1582, 217, 1607, 226, "ACST", 0, 0),
        (1739, 217, 1773, 226, "ACST-1", 0, 0),
        (1799, 217, 1821, 226, "2700", 0, 0),
        (390, 980, 1855, 1004, "A B B R E V I A T I O N\nE X T E R I O R    F I N I S H    S C H E D U L E", 0, 0),
    ]

    candidates = extract_room_finish_candidates_from_blocks(blocks)

    assert len(candidates) == 2
    assert candidates[0].room_no == "101"
    assert candidates[0].room_name == "VESTIBULE"
    assert candidates[0].floor_finish == "VCT-1"
    assert candidates[0].base_finish == "VCB-1"
    assert candidates[0].wall_finish == "GWB / P-2 / PAINT"
    assert candidates[0].ceiling_finish == "PAINT"
    assert candidates[0].height == "2450"
    assert candidates[0].confidence == 0.72
    assert candidates[1].room_no == "101~106"
    assert candidates[1].room_name == "MULTI ROOM"


def test_block_parser_falls_back_to_line_parser_when_no_block_candidates() -> None:
    sheet = DrawingSheet(
        drawing_file_id=1,
        page_index=0,
        text_content="""
        RM NOS | ROOM NAMES | FLOOR | BASE | INTERIOR WALL | CEILING | HGT
        110 | OFFICE | VCT | RB | GWB | ACT | 9'-0"
        """,
    )

    candidates = extract_room_finish_candidates(sheet, page_blocks=[(0, 0, 10, 10, "UNRELATED", 0, 0)])

    assert len(candidates) == 1
    assert candidates[0].room_no == "110"


def test_sample_pdf_page_56_smoke_extracts_room_finish_candidates() -> None:
    fitz = pytest.importorskip("fitz")
    sample_pdf = Path(__file__).resolve().parents[3] / "data" / "samples" / "25BA005_Drawings-1.pdf"
    if not sample_pdf.is_file():
        pytest.skip("sample PDF is not available")

    with fitz.open(sample_pdf) as document:
        page = document.load_page(56)
        sheet = DrawingSheet(drawing_file_id=1, page_index=56, text_content=page.get_text("text"))
        candidates = extract_room_finish_candidates(sheet, page.get_text("blocks"))

    assert len(candidates) >= 20
    assert candidates[0].room_no == "101"
    assert any(candidate.room_no == "110" for candidate in candidates)
