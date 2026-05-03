from app.models import DrawingSheet
from app.services.finish_schedule_extractor import extract_room_finish_candidates


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
