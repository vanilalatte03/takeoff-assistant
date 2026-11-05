"""Synthetic acceptance baseline; these numbers are assumptions, not field truth."""
from io import BytesIO
from decimal import Decimal

import fitz
import pytest
from fastapi.testclient import TestClient
from openpyxl import load_workbook
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.db.init_db import init_db
from app.db.session import get_db
from app.main import app


@pytest.fixture()
def workflow(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{(tmp_path / 'baseline.db').as_posix()}", connect_args={"check_same_thread": False})
    factory = sessionmaker(bind=engine)
    init_db(engine)
    monkeypatch.setattr(settings, "uploads_dir", tmp_path / "uploads")
    monkeypatch.setattr(settings, "rendered_pages_dir", tmp_path / "rendered")

    def db():
        with factory() as session:
            yield session

    app.dependency_overrides[get_db] = db
    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def synthetic_pdf():
    with fitz.open() as document:
        for text in (
            'ZX701 FINISH SCHEDULE\nRM NOS | ROOM NAMES | FLOOR | BASE | INTERIOR WALL | CEILING | HGT\n110 | OFFICE | VCT | RB | GWB | ACST | 2.7m\n119 | OFFICE | VCT | RB | GWB | ACST | 4.6m',
            'ZX201 FLOOR PLAN\nRoom 110 OFFICE\n4200 2700\nRoom 119 OFFICE\n4200',
            'ZX501 PARTITION DETAIL\nRoom 119 type 5A\nHeight 4600\nSingle side example; deductions excluded',
        ):
            page = document.new_page()
            page.insert_text((40, 60), text, fontsize=9)
        return document.tobytes()


def prepare(client):
    project = client.post('/projects', json={'name': 'Synthetic acceptance'}).json()
    response = client.post('/drawing-files/upload', data={'project_id': project['id']}, files={'file': ('synthetic.pdf', synthetic_pdf(), 'application/pdf')})
    assert response.status_code == 201, response.text
    file_id = response.json()['id']
    root = f'/drawing-files/{file_id}'
    for path in ('pages/process', 'sheets/detect', 'sheets/classify'):
        response = client.post(f'{root}/{path}')
        assert response.status_code == 200, response.text
    extracted = client.post(f'{root}/room-finishes/extract')
    assert extracted.status_code == 200
    assert {r['room_no'] for r in extracted.json()['room_finishes']} == {'110', '119'}
    response = client.post(f'{root}/measurements/generate')
    assert response.status_code == 200
    return project['id'], file_id, response.json()['measurements']


def test_known_examples_pdf_to_excel(workflow):
    client = workflow
    project_id, file_id, rows = prepare(client)
    selected = []
    for room, kind, code, inputs, quantity, formula, sources in (
        ('110', 'CEILING_AREA', 'ACST', {'calculation_type': 'AREA_RECTANGLE', 'width': '4.2', 'height': '2.7'}, '11.34', '4.2 * 2.7', 'ZX701, ZX201'),
        ('119', 'PARTITION_AREA', '5A', {'calculation_type': 'PARTITION_AREA', 'wall_length': '4.2', 'wall_height': '4.6', 'side_multiplier': '1'}, '19.32', '4.2 * 4.6 * 1', 'ZX701, ZX201, ZX501'),
    ):
        row = next(r for r in rows if r['room_no'] == room and r['measurement_type'] == kind)
        assert row['status'] != 'CONFIRMED'
        # Partition type and face count are explicitly reviewed by the user.
        assert client.patch(f"/measurements/{row['id']}", json={'finish_code': code, 'memo': 'Synthetic: no deductions; user selected face count.'}).status_code == 200
        result = client.post(f"/measurements/{row['id']}/calculate", json={**inputs, 'source_sheets': sources})
        assert result.status_code == 200, result.text
        saved = result.json()
        assert Decimal(str(saved['quantity'])) == Decimal(quantity)
        assert (saved['formula'], saved['unit'], saved['source_sheets'], saved['status']) == (formula, 'm2', sources, 'DRAFT')
        assert client.patch(f"/measurements/{row['id']}", json={'status': 'CONFIRMED'}).status_code == 200
        assert client.post(f"/measurements/{row['id']}/calculate", json=inputs).status_code == 409
        selected.append((room, code, quantity, formula, sources))

    assert client.post(f'/drawing-files/{file_id}/measurements/generate').json()['measurements'] == []
    response = client.get(f'/drawing-files/{file_id}/measurements/export')
    assert response.status_code == 200
    workbook = load_workbook(BytesIO(response.content))
    assert workbook.sheetnames == ['Summary', 'Details', 'Review']
    details = list(workbook['Details'].values)
    records = [dict(zip(details[0], row)) for row in details[1:]]
    for room, code, quantity, formula, sources in selected:
        row = next(r for r in records if r['Room No'] == room and r['Code'] == code)
        assert Decimal(str(row['Quantity'])) == Decimal(quantity)
        assert (row['Formula'], row['Source Sheets'], row['Status'], row['Unit']) == (formula, sources, 'CONFIRMED', 'm2')
        summary = list(workbook['Summary'].values)
        summary_row = next(r for r in summary[1:] if r[1] == code and Decimal(str(r[3])) > 0)
        assert Decimal(str(summary_row[3])) == Decimal(quantity)



def test_missing_input_does_not_create_quantity(workflow):
    client = workflow
    _, file_id, rows = prepare(client)
    row = next(r for r in rows if r['measurement_type'] == 'CEILING_AREA')
    assert client.post(f"/measurements/{row['id']}/calculate", json={'calculation_type': 'AREA_RECTANGLE', 'width': '4.2'}).status_code == 400
    saved = next(r for r in client.get(f'/drawing-files/{file_id}/measurements').json() if r['id'] == row['id'])
    assert saved['quantity'] is None
    assert saved['status'] != 'CONFIRMED'
