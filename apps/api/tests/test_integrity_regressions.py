from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from openpyxl import load_workbook
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.session import Base, get_db
from app.main import app
from app.models import DrawingFile, DrawingSheet, Measurement, MeasurementType, Project, ReviewStatus, RoomFinish


def test_failed_recalculation_preserves_existing_valid_result(integrity_client):
    client, factory, ids = integrity_client
    target_id = ids["measurements"][0]
    metadata = {"category": "FLOOR", "finish_code": "VCT", "measurement_type": "FLOOR_AREA", "unit": "m2"}
    assert client.patch(f"/measurements/{target_id}", json=metadata).status_code == 200
    response = client.post(f"/measurements/{target_id}/calculate", json={
        "calculation_type": "AREA_RECTANGLE", "width": "2", "height": "3", "deductions": [{"amount": "7"}],
    })
    assert response.status_code == 400
    with factory() as db:
        row = db.get(Measurement, target_id)
        assert row.quantity == Decimal("10.00")
        assert row.formula == "5 * 2"


@pytest.fixture
def integrity_client():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as db:
        projects = [Project(name="one"), Project(name="two")]
        db.add_all(projects)
        db.flush()
        files = [DrawingFile(project_id=projects[i // 2].id, original_filename=f"{i}.pdf", stored_path="unused", page_count=1) for i in range(4)]
        db.add_all(files)
        db.flush()
        sheets = [DrawingSheet(drawing_file_id=f.id, page_index=0, sheet_no=f"A10{i}") for i, f in enumerate(files)]
        db.add_all(sheets)
        db.flush()
        rooms = [RoomFinish(project_id=f.project_id, drawing_sheet_id=s.id, room_no="101", floor_finish="VCT") for f, s in zip(files, sheets)]
        db.add_all(rooms)
        db.flush()
        measurements = [Measurement(project_id=f.project_id, room_finish_id=r.id, room_no="101", category="FLOOR", finish_code="VCT", measurement_type=MeasurementType.FLOOR_AREA, quantity=Decimal("10"), formula="5 * 2", unit="m2", source_sheets=s.sheet_no, status=ReviewStatus.DRAFT) for f, s, r in zip(files, sheets, rooms)]
        db.add_all(measurements)
        db.commit()
        ids = {"files": [f.id for f in files], "rooms": [r.id for r in rooms], "measurements": [m.id for m in measurements]}

    def override():
        with factory() as db:
            yield db

    app.dependency_overrides[get_db] = override
    try:
        yield TestClient(app), factory, ids
    finally:
        app.dependency_overrides.pop(get_db, None)
        engine.dispose()


def test_manual_room_stays_with_its_pdf(integrity_client):
    client, _, ids = integrity_client
    first, second = ids["files"][:2]
    row = client.post(f"/drawing-files/{first}/room-finishes", json={"room_no": "manual", "floor_finish": "VCT"})
    assert row.status_code == 201
    assert row.json()["id"] in [r["id"] for r in client.get(f"/drawing-files/{first}/room-finishes").json()]
    assert row.json()["id"] not in [r["id"] for r in client.get(f"/drawing-files/{second}/room-finishes").json()]


@pytest.mark.parametrize("source_index", [1, 2])
def test_merge_rejects_other_pdf_and_project(integrity_client, source_index):
    client, _, ids = integrity_client
    response = client.post("/measurements/merge", json={"target_id": ids["measurements"][0], "source_ids": [ids["measurements"][source_index]]})
    assert response.status_code == 400


def _same_file_source(factory, ids, quantity=Decimal("6")):
    with factory() as db:
        target = db.get(Measurement, ids["measurements"][0])
        source = Measurement(project_id=target.project_id, room_finish_id=target.room_finish_id, room_no=target.room_no, category=target.category, finish_code=target.finish_code, measurement_type=target.measurement_type, quantity=quantity, formula="2 * 3", unit=target.unit, source_sheets="A102", status=ReviewStatus.DRAFT, coordinates_json={"points": [{"x": 1, "y": 2}]}, deductions_json={"items": [{"amount": "1"}]})
        db.add(source)
        db.commit()
        return source.id


def test_merge_export_excludes_rejected_and_keeps_provenance(integrity_client):
    client, factory, ids = integrity_client
    target = ids["measurements"][0]
    source = _same_file_source(factory, ids)
    response = client.post("/measurements/merge", json={"target_id": target, "source_ids": [source]})
    assert response.status_code == 200
    row = response.json()
    assert Decimal(row["quantity"]) == Decimal("16")
    assert {r["measurement_id"] for r in row["coordinates_json"]["merge_provenance"]["rows"]} == {target, source}
    assert row["coordinates_json"]["merge_provenance"]["rows"][1]["deductions_json"] == {"items": [{"amount": "1"}]}
    from io import BytesIO
    workbook = load_workbook(BytesIO(client.get(f'/drawing-files/{ids["files"][0]}/measurements/export').content), data_only=True)
    assert workbook["Summary"]["D2"].value == 16


def test_merge_rejects_missing_quantity(integrity_client):
    client, factory, ids = integrity_client
    source = _same_file_source(factory, ids, quantity=None)
    assert client.post("/measurements/merge", json={"target_id": ids["measurements"][0], "source_ids": [source]}).status_code == 400
    with factory() as db:
        assert db.get(Measurement, source).status == ReviewStatus.DRAFT


def test_confirmed_requires_explicit_reopen_and_rejected_is_immutable(integrity_client):
    client, factory, ids = integrity_client
    target = ids["measurements"][0]
    assert client.patch(f"/measurements/{target}", json={"status": "CONFIRMED"}).status_code == 200
    for patch in ({"quantity": "4"}, {"status": "REJECTED"}, {"status": "DRAFT", "memo": "change"}):
        assert client.patch(f"/measurements/{target}", json=patch).status_code == 409
    assert client.post(f"/measurements/{target}/calculate", json={"calculation_type": "AREA_RECTANGLE", "width": 2, "height": 3}).status_code == 409
    assert client.patch(f"/measurements/{target}", json={"status": "DRAFT"}).status_code == 200
    assert client.delete(f"/measurements/{target}").status_code == 200
    assert client.patch(f"/measurements/{target}", json={"status": "DRAFT"}).status_code == 409


@pytest.mark.parametrize("patch", [{"quantity": "-2"}, {"unit": "EA"}, {"unit": None}, {"quantity": "10000000000.00"}, {"formula": None, "status": "CONFIRMED"}, {"source_sheets": "", "status": "CONFIRMED"}])
def test_patch_rejects_invalid_quantity_unit_and_confirmation(integrity_client, patch):
    client, _, ids = integrity_client
    assert client.patch(f'/measurements/{ids["measurements"][0]}', json=patch).status_code in (400, 422)


@pytest.mark.parametrize("payload", [
    {"calculation_type": "AREA_RECTANGLE", "width": -2, "height": 3},
    {"calculation_type": "AREA_RECTANGLE", "width": 2, "height": 3, "unit": "EA"},
    {"calculation_type": "AREA_RECTANGLE", "width": 2, "height": 3, "deductions": [{"amount": -1}]},
    {"calculation_type": "AREA_RECTANGLE", "width": 2, "height": 3, "deductions": [{"amount": 7}]},
    {"calculation_type": "AREA_RECTANGLE", "width": 2, "height": 3, "deductions": [{"amount": "1e1000000"}]},
])
def test_calculation_rejects_invalid_inputs(integrity_client, payload):
    client, _, ids = integrity_client
    assert client.post(f'/measurements/{ids["measurements"][0]}/calculate', json=payload).status_code in (400, 422)


def test_calculation_inputs_round_trip_and_manual_patch_invalidates(integrity_client):
    client, factory, ids = integrity_client
    target = ids["measurements"][0]
    with factory() as db:
        db.get(Measurement, target).coordinates_json = {"dimension_assist": {"region": {"x": 1}}}
        db.commit()
    payload = {"calculation_type": "AREA_RECTANGLE", "width": "5", "height": "4", "deductions": [{"amount": "1.89"}]}
    response = client.post(f"/measurements/{target}/calculate", json=payload)
    assert response.status_code == 200
    row = response.json()
    assert row["coordinates_json"]["calculation_inputs"]["deductions"][0]["amount"] == "1.89"
    assert "dimension_assist" in row["coordinates_json"]
    response = client.patch(f"/measurements/{target}", json={"quantity": "8", "formula": "manual", "deductions_json": None, "coordinates_json": {**row["coordinates_json"], "points": []}})
    assert response.status_code == 200
    assert "calculation_inputs" not in response.json()["coordinates_json"]
    assert response.json()["deductions_json"] is None
    assert "dimension_assist" in response.json()["coordinates_json"]


def test_rejected_parent_is_not_generated(integrity_client):
    client, factory, ids = integrity_client
    with factory() as db:
        room = db.get(RoomFinish, ids["rooms"][0])
        room.wall_finish = "new-wall"
        room.status = ReviewStatus.REJECTED
        db.commit()
    response = client.post(f'/drawing-files/{ids["files"][0]}/measurements/generate')
    assert response.status_code == 200
    assert response.json()["measurements"] == []


def test_inputs_survive_metadata_noop_and_are_invalidated_by_new_dimension_evidence(integrity_client):
    client, _, ids = integrity_client
    url = f'/measurements/{ids["measurements"][0]}'
    payload = {"calculation_type": "AREA_RECTANGLE", "width": "5", "height": "4", "deductions": [{"amount": "1"}]}
    row = client.post(f"{url}/calculate", json=payload).json()
    row = client.patch(url, json={"formula": row["formula"], "quantity": row["quantity"], "unit": row["unit"], "memo": "metadata"}).json()
    assert "calculation_inputs" in row["coordinates_json"]
    row = client.patch(url, json={"coordinates_json": {"dimension_assist": {"region": {"x": 99}}}}).json()
    assert "calculation_inputs" not in row["coordinates_json"]
    assert row["deductions_json"]["items"][0]["amount"] == "1.00"


def test_patch_cannot_forge_calculation_inputs_or_deductions(integrity_client):
    client, _, ids = integrity_client
    url = f'/measurements/{ids["measurements"][0]}'
    row = client.patch(url, json={"coordinates_json": {"calculation_inputs": {"width": "999"}}}).json()
    assert "calculation_inputs" not in (row["coordinates_json"] or {})
    assert client.patch(url, json={"deductions_json": {"items": [{"amount": "-1"}]}}).status_code == 400


def test_patch_type_and_unit_are_validated_together(integrity_client):
    client, _, ids = integrity_client
    url = f'/measurements/{ids["measurements"][0]}'
    assert client.patch(url, json={"measurement_type": "COUNT", "unit": "EA", "quantity": "2"}).status_code == 200
    assert client.patch(url, json={"measurement_type": "COUNT", "unit": "m2"}).status_code == 400
    assert client.patch(url, json={"quantity": "1.5"}).status_code == 400


def test_calculation_unions_sources_and_archives_merge_provenance(integrity_client):
    client, factory, ids = integrity_client
    target = ids["measurements"][0]
    source = _same_file_source(factory, ids)
    row = client.post("/measurements/merge", json={"target_id": target, "source_ids": [source]}).json()
    row = client.post(f"/measurements/{target}/calculate", json={"calculation_type": "AREA_RECTANGLE", "width": "2", "height": "3", "source_sheets": "A999"}).json()
    assert row["source_sheets"] == "A100, A102, A999"
    assert "merge_provenance" not in row["coordinates_json"]
    assert row["coordinates_json"]["history"][0]["merge_provenance"]["rows"][1]["measurement_id"] == source


def test_manual_geometry_always_clears_old_deductions_and_inputs(integrity_client):
    client, _, ids = integrity_client
    url = f'/measurements/{ids["measurements"][0]}'
    row = client.post(f"{url}/calculate", json={"calculation_type": "AREA_RECTANGLE", "width": "5", "height": "4", "deductions": [{"amount": "1"}]}).json()
    row = client.patch(url, json={"coordinates_json": {"measurement_mode": "RECTANGLE_AREA", "points": [{"x": 1, "y": 1}, {"x": 2, "y": 2}]}}).json()
    assert row["deductions_json"] is None
    assert "calculation_inputs" not in row["coordinates_json"]


def test_conflicting_legacy_file_sheet_is_excluded(integrity_client):
    client, factory, ids = integrity_client
    with factory() as db:
        row = db.get(RoomFinish, ids["rooms"][0])
        row.drawing_file_id = ids["files"][1]
        db.commit()
    for file_id in ids["files"][:2]:
        rows = client.get(f"/drawing-files/{file_id}/room-finishes").json()
        assert ids["rooms"][0] not in [row["id"] for row in rows]


def test_legacy_sqlite_migration_preserves_rows_and_only_backfills_proven_owners(tmp_path):
    from app.db.init_db import init_db
    engine = create_engine(f"sqlite:///{(tmp_path / 'legacy.db').as_posix()}")
    Base.metadata.create_all(engine, tables=[table for table in Base.metadata.sorted_tables if table.name != "room_finishes"])
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE room_finishes(id INTEGER PRIMARY KEY, project_id INTEGER, drawing_sheet_id INTEGER)"))
        connection.execute(text("INSERT INTO projects(id,name,created_at) VALUES (1,'one','2026-01-01'),(2,'two','2026-01-01')"))
        connection.execute(text("INSERT INTO drawing_files(id,project_id,original_filename,stored_path,page_count,created_at) VALUES (1,1,'one.pdf','unused',1,'2026-01-01'),(2,2,'two.pdf','unused',1,'2026-01-01')"))
        connection.execute(text("INSERT INTO drawing_sheets(id,drawing_file_id,page_index,role,text_content,status) VALUES(1,1,0,'UNKNOWN','','DRAFT'),(2,2,0,'UNKNOWN','','DRAFT')"))
        connection.execute(text("INSERT INTO room_finishes VALUES(1,1,1),(2,1,NULL),(3,1,2)"))
        connection.execute(text("INSERT INTO measurements(id,project_id,room_finish_id,category,finish_code,measurement_type,quantity,unit,source_sheets,status,created_at) VALUES(77,1,2,'FLOOR','legacy','FLOOR_AREA',7,'m2','A100','DRAFT','2026-01-01')"))
    init_db(engine)
    init_db(engine)
    with engine.connect() as connection:
        assert connection.execute(text("SELECT id,drawing_file_id FROM room_finishes ORDER BY id")).all() == [(1, 1), (2, None), (3, None)]
        assert connection.execute(text("SELECT id,room_finish_id,quantity FROM measurements WHERE id=77")).one() == (77, 2, 7)
    engine.dispose()


def test_invalid_legacy_confirmed_row_can_be_reopened_then_corrected(integrity_client):
    client, factory, ids = integrity_client
    target = ids["measurements"][0]
    with factory() as db:
        row = db.get(Measurement, target)
        row.status = ReviewStatus.CONFIRMED
        row.unit = "m"
        db.commit()
    assert client.patch(f"/measurements/{target}", json={"status": "DRAFT"}).status_code == 200
    assert client.patch(f"/measurements/{target}", json={"unit": "m2"}).status_code == 200


def test_manual_quantity_rounds_half_up(integrity_client):
    client, _, ids = integrity_client
    response = client.patch(f'/measurements/{ids["measurements"][0]}', json={"quantity": "1.005"})
    assert response.status_code == 200
    assert Decimal(response.json()["quantity"]) == Decimal("1.01")


@pytest.mark.parametrize("changes", [{"quantity": Decimal("-1")}, {"unit": None}, {"source_sheets": ""}])
def test_merge_refuses_legacy_invalid_calculation_rows(integrity_client, changes):
    client, factory, ids = integrity_client
    source_id = _same_file_source(factory, ids)
    with factory() as db:
        source = db.get(Measurement, source_id)
        for field, value in changes.items():
            setattr(source, field, value)
        if "unit" in changes:
            db.get(Measurement, ids["measurements"][0]).unit = None
        db.commit()
    assert client.post("/measurements/merge", json={"target_id": ids["measurements"][0], "source_ids": [source_id]}).status_code == 400


def test_unassigned_legacy_rows_are_preserved_but_excluded_from_all_file_apis(integrity_client):
    from io import BytesIO
    client, factory, ids = integrity_client
    with factory() as db:
        project_id = db.get(DrawingFile, ids["files"][0]).project_id
        room = RoomFinish(project_id=project_id, room_no="legacy", floor_finish="legacy")
        db.add(room)
        db.flush()
        measurement = Measurement(project_id=project_id, room_finish_id=room.id, room_no="legacy", category="FLOOR", finish_code="legacy", measurement_type=MeasurementType.FLOOR_AREA, quantity=Decimal("7"), formula="7", unit="m2", source_sheets="A100", status=ReviewStatus.DRAFT)
        db.add(measurement)
        db.commit()
        room_id, measurement_id = room.id, measurement.id
    for file_id in ids["files"][:2]:
        assert room_id not in [row["id"] for row in client.get(f"/drawing-files/{file_id}/room-finishes").json()]
        assert measurement_id not in [row["id"] for row in client.get(f"/drawing-files/{file_id}/measurements").json()]
        assert client.post(f"/drawing-files/{file_id}/measurements/generate").json()["measurements"] == []
        workbook = load_workbook(BytesIO(client.get(f"/drawing-files/{file_id}/measurements/export").content), data_only=True)
        assert workbook["Summary"]["D2"].value == 10
        assert "legacy" not in [row[1] for row in list(workbook["Details"].values)[1:]]
    with factory() as db:
        assert db.get(RoomFinish, room_id).drawing_file_id is None
        assert db.get(Measurement, measurement_id).quantity == Decimal("7")


def test_room_finish_confirmation_requires_reopen_before_edit(integrity_client):
    client, _, ids = integrity_client
    url = f'/room-finishes/{ids["rooms"][0]}'
    assert client.patch(url, json={"status": "CONFIRMED"}).status_code == 200
    assert client.patch(url, json={"room_name": "changed"}).status_code == 409
    assert client.patch(url, json={"status": "DRAFT", "room_name": "changed"}).status_code == 409
    assert client.patch(url, json={"status": "DRAFT"}).status_code == 200
    assert client.patch(url, json={"room_name": "changed"}).status_code == 200


def test_explicit_clear_allows_recalculation_as_a_different_measurement_type(integrity_client):
    client, _, ids = integrity_client
    url = f'/measurements/{ids["measurements"][0]}'
    assert client.patch(url, json={"quantity": "17.43", "formula": "legacy area"}).status_code == 200
    response = client.patch(url, json={"measurement_type": "COUNT", "unit": "EA", "quantity": None, "formula": None})
    assert response.status_code == 200
    assert response.json()["quantity"] is None
    assert response.json()["formula"] is None
    response = client.post(f"{url}/calculate", json={"calculation_type": "COUNT", "count": "2"})
    assert response.status_code == 200
    assert Decimal(response.json()["quantity"]) == Decimal("2")
    assert response.json()["unit"] == "EA"


def test_explicit_clear_recovers_invalid_legacy_confirmed_calculation(integrity_client):
    client, factory, ids = integrity_client
    target = ids["measurements"][0]
    url = f"/measurements/{target}"
    with factory() as db:
        row = db.get(Measurement, target)
        row.quantity = Decimal("-8")
        row.unit = "EA"
        row.status = ReviewStatus.CONFIRMED
        db.commit()
    assert client.patch(url, json={"status": "DRAFT"}).status_code == 200
    assert client.patch(url, json={"measurement_type": "FLOOR_AREA", "unit": "m2", "quantity": None, "formula": None}).status_code == 200
    response = client.post(f"{url}/calculate", json={"calculation_type": "AREA_RECTANGLE", "width": "4", "height": "2"})
    assert response.status_code == 200
    assert Decimal(response.json()["quantity"]) == Decimal("8")
    assert response.json()["unit"] == "m2"
