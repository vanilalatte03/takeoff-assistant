# 실행·검사 명령

저장소 루트의 Windows PowerShell에서 실행한다. API는 `apps/api/.venv311`, 프론트엔드는 Node 24 환경을 사용한다. 가상환경 활성화나 개발자 PC의 고정 경로가 필요하지 않다. 다른 운영체제의 전체 실행은 검증하지 않았다.

## 활성 명령

| 이름 | 명령 | 필수 | 설명 |
| --- | --- | --- | --- |
| dev-api | `.\apps\api\.venv311\Scripts\python.exe -m uvicorn app.main:app --app-dir apps/api --host 127.0.0.1 --port 8000` | no | 로컬 API 실행 |
| dev-web | `npm.cmd --prefix apps/web run dev -- --host 127.0.0.1 --port 5173 --strictPort` | no | 로컬 Vite 실행 |
| setup-api-venv | `py -3.11 -m venv apps/api/.venv311` | no | Python 3.11 가상환경 생성 |
| install-api-deps | `.\apps\api\.venv311\Scripts\python.exe -m pip install --require-hashes --only-binary=:all: -r apps/api/requirements-win-py311.lock` | no | Windows x64/Python 3.11의 해시 고정 의존성 설치 |
| install-api | `.\apps\api\.venv311\Scripts\python.exe -m pip install --no-deps --no-build-isolation -e "./apps/api[dev]"` | no | 고정 의존성·backend로 로컬 API 설치 |
| install-web | `npm.cmd --prefix apps/web ci` | no | lockfile 기반 frontend 설치 |
| test | `.\apps\api\.venv311\Scripts\python.exe -m pytest apps/api/tests` | yes | API 회귀 테스트 |
| test-harness | `.\apps\api\.venv311\Scripts\python.exe -m pytest scripts` | yes | 운영 스크립트 테스트 |
| test-web | `npm.cmd --prefix apps/web test` | yes | DOM 컴포넌트 회귀 테스트 |
| build | `npm.cmd --prefix apps/web run build` | yes | TypeScript 검사·Vite build |
| review | `.\apps\api\.venv311\Scripts\python.exe scripts/doctor.py` | no | 저장소 운영 설정 확인 |
| check | `.\apps\api\.venv311\Scripts\python.exe scripts/checks.py --stage manual` | no | profile에 등록한 검사 전체 실행 |
| phase | `.\apps\api\.venv311\Scripts\python.exe scripts/execute.py <phase-name>` | no | 기여자용 phase 실행 |
| create-dataset-template | `.\apps\api\.venv311\Scripts\python.exe scripts/create_example_dataset_template.py` | no | 공개용 빈 Excel 템플릿 재생성 |
| check-dataset-template | `.\apps\api\.venv311\Scripts\python.exe scripts/validate_example_dataset.py docs/templates/example_dataset_template.xlsx --allow-empty-template` | no | 공개 템플릿 구조 확인 |
| validate-dataset | `.\apps\api\.venv311\Scripts\python.exe scripts/validate_example_dataset.py data/samples/takeoff_example_dataset_private.xlsx` | no | 비공개 산출 예시 workbook 구조·필수 값 확인 |

`.codex/project-profile.json`과 이 표의 test/build 명령을 동기화한다. `checks.py`는 profile의 검사 명령을 우선 사용한다. `doctor.py`는 설정 점검이며 앱의 실무 정확도를 검증하는 명령이 아니다.

## 준비와 사용

- [README 빠른 시작](../README.md): Python/Node 준비, 의존성 설치, 두 터미널 실행
- [합성 PDF 데모](DEMO.md): 비공개 도면 없이 후보·계산·Excel 확인
- [산출 무결성](INTEGRITY_FIXES.md): F01~F07 계약과 기존 DB 처리

`py`가 없다면 Python launcher를 설치하거나 Python 3.11을 가리키는 `python -m venv apps/api/.venv311`을 사용한다. 시스템의 `python`이 다른 버전이면 먼저 버전을 확인한다.

Python 의존성은 `apps/api/requirements-win-py311.lock`으로 설치한다. PyMuPDF 1.28.2의 Windows 손상 PDF 정리 회귀를 수정했으며 기존 1.27.2.3도 업로드 회귀로 비교했다. lock 재생성·보안 검사와 정리 실패 한계는 [설치/PDF 오류 계약](PDF_UPLOAD_REPRODUCIBILITY.md)을 따른다. 다른 플랫폼은 별도 lock 생성과 검증이 필요하다.

기존 DB에 적용하기 전 서버를 종료하고 SQLite DB와 업로드 자료를 백업한다. 문서와 데모 검증은 실제 업무 데이터 대신 별도 DB·합성 PDF를 사용한다.
