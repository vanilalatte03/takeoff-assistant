from decimal import Decimal
import pytest
from app.models import DrawingSheet
from app.services.dimension_assist import _extract_candidates_from_text


@pytest.mark.parametrize('text,raw,value,unit', [
    ('width 2.7m', '2.7m', '2.700', 'm'),
    ('length 4200mm', '4200mm', '4.200', 'mm'),
    ('width 2.7 m', '2.7 m', '2.700', 'm'),
    ('length 80mm', '80mm', '0.080', 'mm'),
    ('width 4200', '4200', '4.200', 'mm'),
])
def test_metric_suffix_does_not_truncate_decimal(text, raw, value, unit):
    candidates = _extract_candidates_from_text(text, DrawingSheet(page_index=0, sheet_no='ZX201'), [])
    assert len(candidates) == 1
    assert candidates[0].raw_text == raw
    assert candidates[0].normalized_value == Decimal(value)
    assert candidates[0].unit_guess == unit


def test_room_identifier_and_sheet_code_are_not_dimensions():
    assert _extract_candidates_from_text('ZX201 Room 110', DrawingSheet(page_index=0), []) == []
