from decimal import Decimal
from openpyxl import load_workbook
from app.models import Measurement, MeasurementType, ReviewStatus
from app.services.measurement_excel_exporter import build_measurements_workbook


def test_rejected_nonzero_quantity_does_not_inflate_summary():
    rows = [Measurement(id=i, project_id=1, room_no='110', category='CEILING', finish_code='ACST',
        measurement_type=MeasurementType.CEILING_AREA, formula='4.2 * 2.7', quantity=Decimal('11.34'),
        unit='m2', source_sheets='ZX201', status=status) for i, status in enumerate([ReviewStatus.DRAFT, ReviewStatus.REJECTED], start=1)]
    book = load_workbook(build_measurements_workbook(rows))
    assert Decimal(str(book['Summary']['D2'].value)) == Decimal('11.34')
    assert book['Review'].max_row == 2
    # Details preserves rejected-row history with its status for auditing.
    assert book['Details'].max_row == 3
    assert book['Details']['J3'].value == 'REJECTED'
