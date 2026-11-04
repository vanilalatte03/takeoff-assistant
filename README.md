# Takeoff Assistant

PDF 건축 도면에서 마감표·치수 후보를 찾고, 사용자가 측정·계산·검수한 결과를 Excel로 내보내는 **단일 사용자용 로컬 웹 MVP**입니다.

텍스트 추출과 규칙 기반 후보 생성을 사용합니다. 자동 치수선 판독이나 AI 모델/API 연동은 구현하지 않았으며, 실무 산출 정확도와 작업 시간 절감 효과는 아직 검증하지 않았습니다.

## 할 수 있는 일

1. PDF 업로드, 페이지 텍스트 추출과 이미지 렌더링
2. 도면 번호·제목·역할 검색 및 마감표 후보 감지
3. 방별 마감 후보 검수·수정과 산출 후보 생성
4. 기준 길이로 축척 설정 후 선·사각형·다각형·개수 수동 측정
5. 도면 영역의 치수 텍스트 후보를 선택해 계산 입력에 반영
6. 면적·둘레·벽체·파티션·공제를 계산하고, 사용자가 확정한 상태와 출처 보존
7. `Summary`, `Details`, `Review` 시트가 있는 Excel 다운로드

추출 후보는 사용자가 확인해야 합니다. 거절한 행은 합계에서 제외하며, 확정한 행은 **재검토 시작**으로 확정을 취소한 뒤 수정합니다. 저장 계약과 회귀 사례는 [산출 무결성 문서](docs/INTEGRITY_FIXES.md)에 있습니다.

## 구성

| 영역 | 기술 |
| --- | --- |
| API·저장 | FastAPI, SQLAlchemy, SQLite, 로컬 파일 |
| PDF·Excel | PyMuPDF, openpyxl |
| 화면·테스트 | React, TypeScript, Vite, Vitest, React Testing Library |

## 빠른 시작 — Windows PowerShell

Git, Python 3.11, Node.js 24를 설치합니다. `py -3.11 --version`, `node --version`, `npm.cmd --version`이 실행되는 환경을 전제로 합니다. PowerShell 가상환경 활성화 없이 Python 실행 파일을 직접 사용합니다.

```powershell
git clone https://github.com/vanilalatte03/takeoff-assistant.git
cd takeoff-assistant
py -3.11 -m venv apps/api/.venv311
.\apps\api\.venv311\Scripts\python.exe -m pip install --require-hashes --only-binary=:all: -r apps/api/requirements-win-py311.lock
.\apps\api\.venv311\Scripts\python.exe -m pip install --no-deps --no-build-isolation -e "./apps/api[dev]"
npm.cmd --prefix apps/web ci
```

Python lock은 Windows x64 / Python 3.11용이며 API·개발·스크립트 테스트 의존성과 editable 빌드 backend를 고정합니다. PyMuPDF 1.28.2에서 손상 PDF 정리 오류를 재현해 수정했습니다. 다른 플랫폼/버전의 전체 실행은 검증하지 않았습니다. [설치 재현·보안 검사·PDF 오류 계약](docs/PDF_UPLOAD_REPRODUCIBILITY.md)을 참고하세요.

첫 번째 터미널에서 API를 시작합니다.

```powershell
.\apps\api\.venv311\Scripts\python.exe -m uvicorn app.main:app --app-dir apps/api --host 127.0.0.1 --port 8000
```

두 번째 터미널도 저장소 루트에서 실행합니다.

```powershell
npm.cmd --prefix apps/web run dev -- --host 127.0.0.1 --port 5173 --strictPort
```

- 화면: <http://127.0.0.1:5173>
- API 상태: <http://127.0.0.1:8000/health>
- API 문서: <http://127.0.0.1:8000/docs>

Vite 개발 서버가 `/api` 요청을 API로 전달합니다. 별도 DB 서버, Docker, AI API key는 필요하지 않습니다. 인증 없는 개인용 개발 서버이므로 로컬에서 사용합니다. 이 절차는 운영 배포 안내가 아닙니다.

`py`가 없다면 Python 설치/launcher를 확인하거나, Python 3.11을 가리키는 `python -m venv apps/api/.venv311`로 가상환경을 만듭니다. 나머지 명령은 동일합니다.

## 외부 도면 없이 데모 실행

[합성 도면 데모](docs/DEMO.md)는 직접 생성한 PDF로 업로드 → 마감 후보 → 계산 → Excel 흐름을 확인합니다. 고객 도면이나 비공개 업무 파일은 필요하지 않습니다.

완료 시 확인할 값은 `4.2 * 2.7 = 11.34 m2`입니다. 이는 합성 입력의 기능 동작 확인이며, 실제 도면 정확도 검증 결과가 아닙니다.

## 테스트

저장소 루트에서 실행합니다.

```powershell
.\apps\api\.venv311\Scripts\python.exe -m pytest apps/api/tests
.\apps\api\.venv311\Scripts\python.exe -m pytest scripts
npm.cmd --prefix apps/web test
npm.cmd --prefix apps/web run build
```

F01~F07 수정 당시 기록은 API 158개 통과·비공개 PDF 테스트 2개 생략, 운영 스크립트 71개 통과, UI 26개 통과입니다. 비공개 샘플이 없으면 관련 테스트는 생략됩니다. UI 회귀는 테스트 DOM을 사용하며 실제 브라우저 전체 E2E와 구분합니다. 최신 검증은 각 환경에서 위 명령으로 확인할 수 있습니다.

## 지원 제한과 남은 과제

- 텍스트가 있는 PDF와 영어 도면명·마감표 중심의 휴리스틱입니다. 스캔 PDF OCR, 한글 방 이름 검색, 모든 마감표 형식을 지원하지 않습니다.
- 자동 방 경계·치수선·문/창문 공제 인식은 없습니다. 숫자 후보의 단위와 방·벽의 대응은 사람이 확인해야 합니다.
- 회전 PDF의 영역/텍스트 좌표 정합과 벽 방향별 서로 다른 마감의 분리 산출은 미완료입니다.
- Excel 텍스트의 수식 해석 방지와 npm 개발 의존성 보안 갱신은 별도 보강 대상입니다. Python 의존성은 Windows/Python 3.11 lock으로 설치합니다. 출처를 신뢰할 수 있는 합성·본인 자료로 검증합니다.
- 다중 사용자, 클라우드 배포, 견적 시스템 연동을 제공하지 않습니다.

기능 구현·자동 테스트 통과와 실무 정답 검수는 별개입니다. 최종 물량은 원본 도면 및 도메인 전문가의 검토가 필요합니다.

## 데이터와 공개 범위

실행하면 원본 PDF·렌더링 이미지는 `data/`, SQLite는 `data/takeoff_assistant.db`에 저장됩니다. 업로드 자료, DB, 산출 Excel, 환경파일은 공개하지 않습니다. 로컬 폴더 전체를 압축하면 Git에서 제외한 자료도 포함될 수 있습니다.

기존 SQLite를 사용한다면 서버를 종료하고 DB와 업로드 자료를 백업합니다. 명확한 sheet 소속이 있는 행만 PDF 소속을 채우며, 소속 불명확한 옛 수동 행은 보존하되 파일별 결과에서 제외합니다. [데이터 준비 기준](docs/SAMPLE_DATA_GUIDE.md)을 참고하세요.

## 라이선스

별도 고지가 없는 이 프로젝트의 원본 코드·문서는 **AGPL-3.0-only**로 제공합니다. [LICENSE](LICENSE)에 전문이 있으며, 적용 범위와 소스 제공 원칙은 [라이선스 정책](docs/LICENSE_POLICY.md)에 정리했습니다.

외부 라이브러리는 각자의 라이선스를 따릅니다. PyMuPDF의 AGPL/상용 이중 라이선스는 해당 공급자의 선택지이며, 이 프로젝트가 상용 라이선스를 제공하거나 구매했다는 뜻이 아닙니다. [의존성 고지](THIRD_PARTY_NOTICES.md)와 [버전별 라이선스 목록](docs/DEPENDENCY_LICENSES.md)을 확인하세요. 실제 도면·고객 자료의 이용·배포 권한은 별도입니다.

## 문서와 소스

- [실행·검사 명령](docs/COMMANDS.md)
- [MVP 범위](docs/MVP_SPEC.md), [도메인 규칙](docs/DOMAIN_RULES.md)
- [아키텍처](docs/ARCHITECTURE.md), [설계 결정](docs/ADR.md)
- [인수 기준](docs/ACCEPTANCE_CHECKLIST.md), [수동 검증](docs/QA_SMOKE_TEST.md)
- API: `apps/api/app` · 화면: `apps/web/src` · API 테스트: `apps/api/tests`

기여자용 Codex 작업 지침은 [AGENTS.md](AGENTS.md)에 있습니다. 앱 실행에는 Codex나 저장소 hook 활성화가 필요하지 않습니다.
