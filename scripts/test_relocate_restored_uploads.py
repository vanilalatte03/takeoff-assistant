"""Synthetic stopped-backup relocation; never opens a user DB or external API."""
from contextlib import closing
import hashlib
from io import BytesIO
from pathlib import Path
import shutil
import sqlite3
import sys
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent))
from relocate_restored_uploads import RecoveryError, main, relocate_database


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture
def backup(tmp_path):
    old = tmp_path / 'old uploads'
    new = tmp_path / 'recovery' / 'uploads'
    source = tmp_path / 'backup.db'
    output = new.parent / 'recovered.db'
    for project in (1, 2):
        path = old / str(project) / f'{project:032x}_synthetic.pdf'
        path.parent.mkdir(parents=True)
        path.write_bytes(b'%PDF-synthetic-' + str(project).encode())
    new.parent.mkdir()
    shutil.copytree(old, new)
    with closing(sqlite3.connect(source)) as db:
        db.executescript('CREATE TABLE projects(id INTEGER PRIMARY KEY);'
                         'INSERT INTO projects VALUES(1),(2);'
                         'CREATE TABLE drawing_files(id INTEGER PRIMARY KEY, project_id INTEGER, stored_path TEXT);'
                         'CREATE TABLE preserved(id INTEGER, quantity TEXT, status TEXT, coordinates_json TEXT, deductions_json TEXT);'
                         'INSERT INTO preserved VALUES(1,"11.34","CONFIRMED",\'{"formula":"4.2 * 2.7","sources":["ZX701","ZX201"]}\',\'[]\');')
        for project in (1, 2):
            db.execute('INSERT INTO drawing_files VALUES(?,?,?)', (project, project, str(next((old / str(project)).iterdir()))))
        db.commit()
    return source, old, new, output


def test_dry_run_then_new_db_preserves_every_other_value_and_input(backup, capsys):
    source, old, new, output = backup
    before = digest(source)
    files = {p: digest(p) for root in (old, new) for p in root.rglob('*.pdf')}
    assert main(['--source-db', str(source), '--old-uploads', str(old), '--new-uploads', str(new), '--output-db', str(output)]) == 0
    assert 'DRY_RUN' in capsys.readouterr().out
    assert not output.exists()
    report = relocate_database(*backup, apply=True)
    assert report == {'status': 'CREATED', 'drawing_file_count': 2, 'originals_hash_checked': 2, 'originals_unavailable': 0}
    with closing(sqlite3.connect(source)) as src, closing(sqlite3.connect(output)) as dst:
        assert src.execute('SELECT * FROM preserved').fetchall() == dst.execute('SELECT * FROM preserved').fetchall()
        assert src.execute('SELECT * FROM projects').fetchall() == dst.execute('SELECT * FROM projects').fetchall()
        assert {Path(row[0]).parent for row in dst.execute('SELECT stored_path FROM drawing_files')} == {new / '1', new / '2'}
    assert digest(source) == before
    assert all(digest(path) == value for path, value in files.items())
    assert not list(new.parent.glob('.takeoff-recovery-*'))


@pytest.mark.parametrize('failure', ['missing', 'wrong-project', 'outside', 'relative', 'traversal', 'duplicate', 'bad-copy', 'orphan', 'null-path'])
def test_invalid_or_ambiguous_backup_never_publishes_partial_output(backup, failure):
    source, old, new, output = backup
    with closing(sqlite3.connect(source)) as db:
        if failure == 'missing':
            next((new / '2').iterdir()).unlink()
        elif failure == 'wrong-project':
            db.execute('UPDATE drawing_files SET project_id=2 WHERE id=1')
        elif failure == 'outside':
            db.execute('UPDATE drawing_files SET stored_path=? WHERE id=1', (str(source.parent / 'elsewhere.pdf'),))
        elif failure == 'relative':
            db.execute('UPDATE drawing_files SET stored_path="relative.pdf" WHERE id=1')
        elif failure == 'traversal':
            db.execute('UPDATE drawing_files SET stored_path=? WHERE id=1', (str(old / '1' / '..' / '1' / next((old / '1').iterdir()).name),))
        elif failure == 'duplicate':
            db.execute('UPDATE drawing_files SET project_id=1, stored_path=(SELECT stored_path FROM drawing_files WHERE id=1) WHERE id=2')
        elif failure == 'bad-copy':
            next((new / '2').iterdir()).write_bytes(b'different')
        elif failure == 'orphan':
            db.execute('DELETE FROM projects WHERE id=2')
        elif failure == 'null-path':
            db.execute('UPDATE drawing_files SET stored_path=NULL WHERE id=2')
        db.commit()
    before = digest(source)
    with pytest.raises(RecoveryError):
        relocate_database(*backup, apply=True)
    assert not output.exists()
    assert digest(source) == before
    assert not list(new.parent.glob('.takeoff-recovery-*'))


@pytest.mark.parametrize('failure', ['same-db', 'existing-output', 'same-uploads', 'nested-uploads', 'wrong-output-directory', 'sidecar'])
def test_path_and_stopped_backup_guards(backup, failure):
    source, old, new, output = backup
    if failure == 'same-db':
        output = source
    elif failure == 'existing-output':
        output.write_bytes(b'user-owned sentinel')
    elif failure == 'same-uploads':
        new = old
    elif failure == 'nested-uploads':
        new = old / 'nested'
        new.mkdir()
    elif failure == 'wrong-output-directory':
        output = old.parent / 'would-write-next-to-old.db'
    elif failure == 'sidecar':
        Path(str(source) + '-wal').write_bytes(b'not a stopped standalone backup')
    existing = output.read_bytes() if output.is_file() else None
    with pytest.raises(RecoveryError):
        relocate_database(source, old, new, output, apply=True)
    if existing is not None:
        assert output.read_bytes() == existing
    else:
        assert not output.exists()


def test_publish_race_keeps_user_output_and_discards_only_own_temp(backup):
    source, old, new, output = backup
    before = digest(source)
    def race(_temporary, target):
        target.write_bytes(b'another creator owns this')
        raise FileExistsError()
    with patch('relocate_restored_uploads.os.link', race), pytest.raises(RecoveryError):
        relocate_database(*backup, apply=True)
    assert output.read_bytes() == b'another creator owns this'
    assert digest(source) == before
    assert not list(new.parent.glob('.takeoff-recovery-*'))


def test_copied_pdf_must_not_be_a_hardlink_to_original(backup):
    import os
    source, old, new, output = backup
    target = next((new / '1').iterdir())
    target.unlink()
    os.link(next((old / '1').iterdir()), target)
    with pytest.raises(RecoveryError):
        relocate_database(*backup, apply=True)
    assert not output.exists()


def test_all_paths_must_be_explicit_absolute_paths(backup):
    source, old, new, output = backup
    with pytest.raises(RecoveryError, match='절대 경로'):
        relocate_database(source, Path('relative-uploads'), new, output, apply=True)
    assert not output.exists()


@pytest.mark.parametrize('apply', [False, True])
def test_clean_closed_wal_backup_does_not_create_any_source_sidecar(backup, apply):
    source, old, new, output = backup
    with closing(sqlite3.connect(source)) as db:
        assert db.execute('PRAGMA journal_mode=WAL').fetchone()[0] == 'wal'
    before = {p.name: digest(p) for p in source.parent.iterdir() if p.is_file()}
    assert set(before) == {'backup.db'}
    relocate_database(*backup, apply=apply)
    assert {p.name: digest(p) for p in source.parent.iterdir() if p.is_file()} == before
    assert output.exists() is apply


def test_source_db_change_during_snapshot_validation_aborts(backup):
    import relocate_restored_uploads as module
    real_plan = module._plan
    def changed(*args):
        result = real_plan(*args)
        with closing(sqlite3.connect(backup[0])) as db:
            db.execute('INSERT INTO projects VALUES(3)')
            db.commit()
        return result
    with patch.object(module, '_plan', changed), pytest.raises(RecoveryError, match='입력 DB가 변경'):
        relocate_database(*backup)
    assert not backup[3].exists()


def test_target_changed_after_validation_aborts_without_output(backup):
    import relocate_restored_uploads as module
    real_plan = module._plan
    calls = 0
    def changed(*args):
        nonlocal calls
        calls += 1
        if calls == 2:
            next((backup[2] / '2').iterdir()).write_bytes(b'changed during run')
        return real_plan(*args)
    with patch.object(module, '_plan', changed), pytest.raises(RecoveryError):
        relocate_database(*backup, apply=True)
    assert not backup[3].exists()
    assert not list(backup[2].parent.glob('.takeoff-recovery-*'))


@pytest.mark.parametrize('old_available', [False, True])
def test_real_api_after_recovery_reads_copied_pdf_and_preserves_measurement(tmp_path, monkeypatch, old_available):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'apps' / 'api'))
    import fitz
    from fastapi.testclient import TestClient
    from openpyxl import load_workbook
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.core.config import settings
    from app.db.init_db import init_db
    from app.db.session import get_db
    from app.main import app
    original = tmp_path / 'original'
    original.mkdir()
    source = original / 'takeoff.db'
    restored = tmp_path / 'restored'
    for name, value in {'data_dir': original, 'uploads_dir': original / 'uploads', 'rendered_pages_dir': original / 'rendered', 'exports_dir': original / 'exports'}.items():
        monkeypatch.setattr(settings, name, value)
    engine = create_engine('sqlite:///' + source.as_posix(), connect_args={'check_same_thread': False})
    init_db(engine)
    def connect_client(selected_engine):
        factory = sessionmaker(bind=selected_engine)
        def db():
            with factory() as session:
                yield session
        app.dependency_overrides[get_db] = db
        return TestClient(app)  # explicit init_db; never run lifespan against the default user DB
    client = connect_client(engine)
    recovered_engine = None
    try:
        with fitz.open() as document:
            for text in ('ZX701 FINISH SCHEDULE\nRM NOS | ROOM NAMES | FLOOR | BASE | INTERIOR WALL | CEILING | HGT\n110 | OFFICE | VCT | RB | GWB | ACST | 2.7m', 'ZX201 FLOOR PLAN\nRoom 110 OFFICE\n4200 2700'):
                page = document.new_page()
                page.insert_text((40, 60), text, fontsize=9)
            pdf = document.tobytes()
        project = client.post('/projects', json={'name': 'Synthetic recovery'}).json()['id']
        uploaded = client.post('/drawing-files/upload', data={'project_id': project}, files={'file': ('synthetic.pdf', pdf, 'application/pdf')})
        assert uploaded.status_code == 201
        file_id = uploaded.json()['id']
        for path in ('pages/process', 'sheets/detect', 'sheets/classify', 'room-finishes/extract'):
            assert client.post(f'/drawing-files/{file_id}/{path}').status_code == 200
        rows = client.post(f'/drawing-files/{file_id}/measurements/generate').json()['measurements']
        measurement = next(row for row in rows if row['measurement_type'] == 'CEILING_AREA')
        mid = measurement['id']
        assert client.post(f'/measurements/{mid}/calculate', json={'calculation_type': 'AREA_RECTANGLE', 'width': '4.2', 'height': '2.7', 'source_sheets': 'ZX701, ZX201'}).status_code == 200
        assert client.patch(f'/measurements/{mid}', json={'status': 'CONFIRMED'}).status_code == 200
        before = client.get(f'/drawing-files/{file_id}/measurements').json()
        client.close()
        engine.dispose()
        shutil.copytree(original, restored)
        old_uploads = original / 'uploads'
        if not old_available:
            offline = tmp_path / 'original-offline'
            assert original.resolve().parent == tmp_path.resolve() == offline.resolve().parent
            original.rename(offline)
            preserved = offline
        else:
            preserved = original
        old_hashes = {p.relative_to(preserved): digest(p) for p in preserved.rglob('*') if p.is_file()}
        for name in ('uploads_dir', 'rendered_pages_dir', 'exports_dir'):
            monkeypatch.setattr(settings, name, restored / {'uploads_dir': 'uploads', 'rendered_pages_dir': 'rendered', 'exports_dir': 'exports'}[name])
        monkeypatch.setattr(settings, 'data_dir', restored)
        # Demonstrate the original failure: settings alone cannot relocate DB paths.
        copied_engine = create_engine('sqlite:///' + (restored / 'takeoff.db').as_posix(), connect_args={'check_same_thread': False})
        client = connect_client(copied_engine)
        if not old_available:
            assert client.post(f'/drawing-files/{file_id}/pages/process').status_code == 404
        client.close()
        copied_engine.dispose()
        output = restored / 'recovered.db'
        relocate_database(restored / 'takeoff.db', old_uploads, restored / 'uploads', output, apply=True)
        with closing(sqlite3.connect(output)) as db:
            path = Path(db.execute('SELECT stored_path FROM drawing_files WHERE id=?', (file_id,)).fetchone()[0])
            assert path.is_relative_to(restored / 'uploads')
        # If the old PDF still exists, make accidental reads fail, without writing it.
        import app.api.routes.drawing_files as drawing_routes
        actual_open = drawing_routes.fitz.open
        opened = []
        def copied_only(filename=None, *args, **kwargs):
            if filename is not None:
                assert Path(filename).resolve().is_relative_to(restored / 'uploads')
                opened.append(Path(filename))
            return actual_open(filename, *args, **kwargs)
        monkeypatch.setattr(drawing_routes.fitz, 'open', copied_only)
        recovered_engine = create_engine('sqlite:///' + output.as_posix(), connect_args={'check_same_thread': False})
        client = connect_client(recovered_engine)
        assert client.post(f'/drawing-files/{file_id}/pages/process').status_code == 200
        assert opened == [path]
        assert client.get(f'/drawing-files/{file_id}/measurements').json() == before
        exported = client.get(f'/drawing-files/{file_id}/measurements/export')
        assert exported.status_code == 200
        workbook = load_workbook(BytesIO(exported.content))
        rows = list(workbook['Details'].values)
        record = next(record for row in rows[1:] if (record := dict(zip(rows[0], row)))['Room No'] == '110' and record['Code'] == 'ACST')
        assert (record['Quantity'], record['Formula'], record['Status'], record['Source Sheets']) == (11.34, '4.2 * 2.7', 'CONFIRMED', 'ZX701, ZX201')
        assert {p.relative_to(preserved): digest(p) for p in preserved.rglob('*') if p.is_file()} == old_hashes
    finally:
        client.close()
        engine.dispose()
        if recovered_engine is not None:
            recovered_engine.dispose()
        app.dependency_overrides.clear()
