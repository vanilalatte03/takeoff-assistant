"""Validate a stopped SQLite backup and create a new DB pointing at copied PDFs.

The source DB and PDFs are read-only inputs. No application settings are read.
"""
from argparse import ArgumentParser
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import tempfile


class RecoveryError(ValueError):
    pass


def _within(path, root):
    return path == root or root in path.parents


def _digest(path):
    with path.open('rb') as source:
        return hashlib.file_digest(source, 'sha256').hexdigest()


def _no_sidecars(path):
    if any(Path(str(path) + suffix).exists() for suffix in ('-wal', '-shm', '-journal')):
        raise RecoveryError('DB sidecar가 남아 있습니다. 모든 서버를 정상 종료한 일관된 백업을 사용하세요. sidecar를 임의 삭제하지 마세요.')


def _unchanged_source(path, digest):
    _no_sidecars(path)
    if _digest(path) != digest:
        raise RecoveryError('검증 중 입력 DB가 변경됐습니다. 모든 서버를 종료한 백업을 사용하세요.')


def _plan(connection, old, new):
    projects = {row[0] for row in connection.execute('SELECT id FROM projects')}
    rows = connection.execute('SELECT id, project_id, stored_path FROM drawing_files ORDER BY id').fetchall()
    changes, seen = [], set()
    available = 0
    for identifier, project, stored in rows:
        label = f'drawing_file {identifier}'
        if not isinstance(stored, str) or not stored:
            raise RecoveryError(f'{label}: 원본 경로가 유효하지 않습니다.')
        source = Path(stored)
        if project not in projects or not isinstance(project, int) or project <= 0:
            raise RecoveryError(f'{label}: 프로젝트 소속이 유효하지 않습니다.')
        if not source.is_absolute() or '..' in source.parts:
            raise RecoveryError(f'{label}: 절대 원본 경로가 필요합니다.')
        source = source.resolve()
        if not _within(source, old):
            raise RecoveryError(f'{label}: 지정한 기존 uploads 경로 밖입니다.')
        relative = source.relative_to(old)
        if len(relative.parts) != 2 or relative.parts[0] != str(project):
            raise RecoveryError(f'{label}: 프로젝트별 uploads 구조와 일치하지 않습니다.')
        if relative.suffix.lower() != '.pdf':
            raise RecoveryError(f'{label}: PDF 경로가 아닙니다.')
        target = new / relative
        if not target.is_file() or target.resolve() != target:
            raise RecoveryError(f'{label}: 복구 PDF가 없거나 연결 경로가 모호합니다.')
        key = os.path.normcase(str(target))
        if key in seen:
            raise RecoveryError(f'{label}: 여러 행이 같은 PDF 경로를 가리킵니다.')
        seen.add(key)
        digest = _digest(target)
        if source.exists():
            if not source.is_file() or source.samefile(target) or _digest(source) != digest:
                raise RecoveryError(f'{label}: 원본과 복구 PDF가 독립된 동일 복사본이 아닙니다.')
            available += 1
        changes.append((str(target), identifier, digest))
    return changes, available


def relocate_database(source_db, old_uploads, new_uploads, output_db, *, apply=False):
    """Default dry-run; publish one new standalone DB after complete validation.

    Publication uses an exclusive hard link in the destination directory, then
    removes only our temporary link. An existing output is never replaced.
    """
    if not all(Path(value).is_absolute() for value in (source_db, old_uploads, new_uploads, output_db)):
        raise RecoveryError('모든 경로를 절대 경로로 지정하세요.')
    source = Path(source_db).resolve(strict=True)
    old = Path(old_uploads).resolve()
    new = Path(new_uploads).resolve(strict=True)
    output = Path(output_db).absolute()
    if not source.is_file() or not new.is_dir():
        raise RecoveryError('DB 파일과 절대 uploads 폴더 경로를 확인하세요.')
    if _within(old, new) or _within(new, old):
        raise RecoveryError('기존/복구 uploads 경로는 서로 분리돼야 합니다.')
    # A sibling of the copied uploads keeps every new write in the recovery root.
    if output.parent.resolve(strict=True) != new.parent or output.parent != new.parent:
        raise RecoveryError('출력 DB는 복구 uploads 폴더와 같은 상위 폴더의 새 파일이어야 합니다.')
    if output.exists() or output.is_symlink() or output.resolve() == source:
        raise RecoveryError('출력 DB가 이미 있거나 입력 DB와 같습니다. 새 이름을 사용하세요.')
    _no_sidecars(source)
    _no_sidecars(output)
    source_digest = _digest(source)
    temporary = None
    try:
        # A stopped standalone snapshot only. Plain mode=ro may create WAL/SHM
        # files even for a clean, closed WAL-mode DB. Never open a live DB here.
        with closing(sqlite3.connect(source.as_uri() + '?mode=ro&immutable=1', uri=True, timeout=1)) as src:
            src.execute('PRAGMA query_only=ON')
            src.execute('BEGIN')
            if src.execute('PRAGMA integrity_check').fetchall() != [('ok',)]:
                raise RecoveryError('백업 DB 무결성 검사에 실패했습니다.')
            changes, available = _plan(src, old, new)
            report = {'status': 'DRY_RUN', 'drawing_file_count': len(changes),
                      'originals_hash_checked': available,
                      'originals_unavailable': len(changes) - available}
            if not apply:
                _unchanged_source(source, source_digest)
                return report
            handle, name = tempfile.mkstemp(prefix='.takeoff-recovery-', suffix='.db', dir=new.parent)
            os.close(handle)
            temporary = Path(name)
            with closing(sqlite3.connect(temporary)) as dst:
                src.backup(dst)
                dst.execute('PRAGMA journal_mode=DELETE')
                with dst:
                    dst.executemany('UPDATE drawing_files SET stored_path=? WHERE id=?',
                                    [(target, identifier) for target, identifier, _ in changes])
                if dst.execute('PRAGMA integrity_check').fetchall() != [('ok',)]:
                    raise RecoveryError('출력 DB 무결성 검사에 실패했습니다.')
            # Detect changed/replaced PDFs before publishing any usable output.
            if changes != _plan(src, old, new)[0]:
                raise RecoveryError('검증 중 PDF가 변경됐습니다. 서버 종료와 복사본을 확인하세요.')
            _unchanged_source(source, source_digest)
            _no_sidecars(output)
            # link is exclusive even on Windows; never overwrite a racing file.
            os.link(temporary, output)
            return report | {'status': 'CREATED'}
    except (OSError, sqlite3.Error) as error:
        raise RecoveryError('복구 검증/새 DB 생성에 실패했습니다. 기존 파일은 덮어쓰지 않았습니다. 경로·권한·디스크·로컬 파일시스템을 확인하세요.') from error
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def main(argv=None):
    parser = ArgumentParser(description=__doc__)
    for option in ('source-db', 'old-uploads', 'new-uploads', 'output-db'):
        parser.add_argument('--' + option, type=Path, required=True)
    parser.add_argument('--apply', action='store_true', help='검증 후 기존 파일을 덮어쓰지 않고 새 DB 생성')
    args = parser.parse_args(argv)
    try:
        report = relocate_database(args.source_db, args.old_uploads, args.new_uploads, args.output_db, apply=args.apply)
    except (RecoveryError, OSError) as error:
        parser.exit(1, f'복구 중단: {error}\n')
    print(json.dumps(report, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
