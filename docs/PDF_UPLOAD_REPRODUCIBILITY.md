# Python 설치 재현성과 손상 PDF 처리

## 설치와 lock 갱신

`README.md`의 두 단계 설치를 사용한다. `requirements-win-py311.lock`은 Windows x64 / CPython 3.11에서 API runtime, `dev` extra, 루트 `requirements-dev.txt`의 스크립트 테스트 의존성, `requirements-build.in`의 setuptools를 함께 해시 고정한다. 첫 명령은 wheel만 설치하고 두 번째는 이미 설치한 backend로 저장소의 API를 editable 설치한다. editable 프로젝트 자체와 pip는 해시 고정 대상이 아니다. 다른 운영체제/Python의 설치 지원을 의미하지 않는다.

저장소 루트에서 별도 도구 환경으로 갱신한다. uv는 앱 실행에는 필요 없다.

```powershell
py -3.11 -m venv apps/api/.venv-tools
.\apps\api\.venv-tools\Scripts\python.exe -m pip install "uv==0.12.4" "pip-audit==2.9.0"
.\apps\api\.venv-tools\Scripts\uv.exe pip compile apps/api/pyproject.toml requirements-dev.txt apps/api/requirements-build.in --extra dev --python-version 3.11 --python-platform x86_64-pc-windows-msvc --generate-hashes --output-file apps/api/requirements-win-py311.lock
.\apps\api\.venv-tools\Scripts\python.exe -m pip_audit -r apps/api/requirements-win-py311.lock --require-hashes --disable-pip
```

기존 lock의 버전을 유지하며 입력과 맞춘다. 의도적인 전체 갱신에는 compile 명령에 `--upgrade`, 특정 패키지만 갱신할 때는 `--upgrade-package 패키지명`을 추가한다. 갱신한 lock은 새 venv에서 README 설치, `pip check`, API/스크립트 테스트를 다시 실행한다. 설치 metadata를 기준으로 `DEPENDENCY_LICENSES.md`의 Python 표도 갱신한다. 도구 환경의 패키지는 앱 lock과 분리한다.

2026-11-04 첫 audit는 pytest 8.4.2에서 `PYSEC-2026-1845` / `CVE-2025-71176` 한 건을 보고했다. Unix 임시 디렉터리 처리 취약점이며 [pytest 9.0.3 수정 기록](https://docs.pytest.org/en/9.0.x/changelog.html#pytest-9-0-3-2026-04-07)에 따라 pytest 허용 범위를 `>=9.0.3,<10`으로 갱신했다. 최종 lock audit는 알려진 취약점 0건이었다. 이는 해당 시점의 advisory DB 결과이며 안전성 전체를 보증하지 않는다.

## Windows 손상 PDF 재현과 원인

수정 전 main의 `test_upload_rejects_invalid_pdf_content`를 Python 3.11.9 / Windows / PyMuPDF 1.28.2에서 실행하면 `fitz.open(path)`가 `FileDataError`를 던진 뒤 `stored_path.unlink()`에서 `PermissionError: WinError 32`가 발생했다. 원래 HTTP 400이 서버 오류로 덮였다.

설치된 1.28.2의 `Document.__init__`는 `mupdf.fz_open_file(filename)`로 만든 `fz_stream`을 지역 변수에 둔다. 다음 `fz_open_document_with_stream_and_dir`가 실패하면 생성자의 traceback이 그 스트림을 보존한다. 문서 생성이 끝나지 않아 호출부 `with`의 종료 처리에도 도달하지 않는다. 예외를 보유한 상태에서 파일 삭제를 시도하는 비교 실험은 filename 방식에서 WinError 32, memory 방식에서 즉시 삭제 성공을 보였다. 단순 버전 하향이나 GC 타이밍에 의존하지 않는다.

검증 함수는 Python의 `Path.read_bytes()`로 디스크 핸들을 먼저 닫고 [PyMuPDF의 memory stream API](https://pymupdf.readthedocs.io/en/latest/how-to-open-a-file.html)로 PDF를 연다. 정상 생성된 문서는 `with`로 닫는다. 파일 읽기 자체의 I/O 실패를 잘못된 PDF의 400으로 숨기지 않는다.

## 응답·정리 계약과 한계

- 비어 있거나 파싱할 수 없는 PDF는 기존 메시지의 HTTP 400을 반환한다. DrawingFile DB 행은 만들지 않고 저장 파일을 삭제한다. 업로드 spool도 닫는다.
- 복사 중 I/O 실패는 원래 서버 오류를 유지하며 부분 파일 삭제를 시도한다. 성공한 PDF는 원래 저장/DB 계약을 유지한다.
- 파일 삭제가 OS 권한·외부 잠금 등으로 실패해도 원래 오류 응답을 보존한다. ERROR 로그에 `manual removal required`, 생성된 `upload_id`, OS 오류 번호를 남긴다. 사용자 파일명·전체 경로·PDF 내용은 로그에 넣지 않는다.
- 삭제 실패 파일은 디스크에 남을 수 있다. 자동 재시도/정리 작업은 없으므로 서버를 멈추고 `data/uploads/<project_id>/`에서 해당 UUID로 시작하는 파일을 찾아 수동 삭제해야 한다. DB에는 잘못된 PDF 행을 남기지 않는다.
- 검증 시 PDF 전체 크기만큼의 메모리를 추가로 사용한다. 업로드 크기 제한은 현재 없으며 큰 파일의 메모리 사용량은 제한 사항이다. 기존 저장된 PDF의 페이지 처리 전체를 메모리 방식으로 변경한 것은 아니다.
- DB commit 실패 후의 파일 정리/트랜잭션 복구는 이 손상 PDF 수정의 검증 범위 밖이다.

자동 회귀는 정상 PDF 저장, 잘못된 내용/빈 파일/잘린 PDF의 400·DB/파일 무잔류, 삭제 실패 시 400·ERROR 로그·DB 무잔류, 부분 복사 실패 시 파일 삭제와 spool 종료를 확인한다. 실제 PyMuPDF 1.28.2 및 1.27.2.3에서 업로드 회귀를 비교한다. 비공개 실무 PDF 정확도나 브라우저 전체 E2E를 검증한 결과가 아니다.
