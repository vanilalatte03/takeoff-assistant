# 아키텍처

## 시스템 개요
- Backend: FastAPI, SQLAlchemy, SQLite, PyMuPDF, openpyxl
- Frontend: React, TypeScript, Vite, canvas overlay가 있는 렌더링된 PDF 페이지 이미지
- Storage: 로컬 SQLite database와 업로드 PDF, 렌더링 페이지, Excel export 파일을 위한 로컬 파일 시스템 디렉터리
- 주요 책임: 도면 PDF를 추적 가능한 수량이 포함된 수정 가능한 takeoff draft로 변환합니다.

## 디렉터리 구조
```text
apps/
  api/
    app/
      api/routes/       FastAPI endpoint
      core/             설정
      db/               SQLAlchemy session 및 database init
      models/           persistence model
      schemas/          API schema
      services/         PDF, sheet, extraction, calculation, export logic
    tests/              backend test
  web/
    src/
      api/              API client
      components/       공통 UI 및 measurement widget
      pages/            route-level view
      types/            API TypeScript type
data/
  uploads/              업로드 PDF, .gitkeep 외에는 git 제외
  rendered/             렌더링된 page PNG, .gitkeep 외에는 git 제외
docs/                   제품, 아키텍처, 인수 기준, 운영 문서
exports/                생성된 Excel workbook, .gitkeep 외에는 git 제외
scripts/                Codex template check, guard, doctor, phase runner
```

## 모듈 경계
- `apps/api/app/api/routes`: HTTP 경계입니다. 요청 형태를 검증하고 DB row를 로드한 뒤 service를 호출하고 schema 또는 file을 반환합니다.
- `apps/api/app/models`: project, drawing file, drawing sheet, room finish, measurement의 persistence 경계입니다.
- `apps/api/app/services`: sheet detection/classification, finish schedule extraction, candidate generation, quantity calculation, Excel export를 위한 결정적 domain logic입니다.
- 3차에서는 dimension text candidate extraction 같은 치수 후보 탐색 helper도 `apps/api/app/services` 아래에 둡니다.
- `apps/web/src/api`: frontend API 경계입니다.
- `apps/web/src/pages`: upload, sheet search, room finish correction, drawing page measurement, measurement export 워크플로우 화면입니다.
- `apps/web/src/components/ManualMeasurementViewer.tsx`: 사용자가 주도하는 measurement geometry와 scale calibration UI입니다.

## 데이터 흐름
```text
PDF upload
  -> DrawingFile row + local PDF file
  -> page text extraction + page PNG rendering
  -> DrawingSheet metadata detection/classification
  -> RoomFinish 추출 또는 수동 생성
  -> Measurement candidate 생성
  -> 직접 계산 또는 manual canvas measurement
  -> 3차에서는 사용자가 선택한 region 주변 dimension candidate를 계산 입력 보조로 사용
  -> formula/quantity/source/status가 있는 Measurement row
  -> Excel Summary, Details, Review export
```

## 상태와 저장소
- Persistent database state: project, drawing file, drawing sheet, room finish candidate, measurement
- Persistent file state: uploaded PDF, rendered PNG, generated Excel file
- Measurement geometry: `Measurement.coordinates_json`에 JSON으로 저장
- Dimension assist region과 선택한 후보 근거도 `Measurement.coordinates_json`에 JSON으로 저장
- Deductions: `Measurement.deductions_json`에 JSON으로 저장
- Review state: `DRAFT`, `NEEDS_REVIEW`, `CONFIRMED`, `REJECTED`
- Migration: SQLite의 RoomFinish 소속 컬럼은 기존 데이터를 보존하는 추가 방식으로 적용합니다. 명확한 sheet 소속만 채우며, 미배정 legacy 행을 임의의 PDF에 연결하지 않습니다. 세부 결정은 `docs/adr/0004-measurement-integrity.md`를 따릅니다.

## Measurement 저장 계약
모든 계산된 수량은 다음 정보를 추적 가능하게 저장해야 합니다.

- project_id
- room_no, room_name
- category
- finish_code
- measurement_type
- formula
- quantity
- unit
- source_sheets
- status
- memo
- coordinates_json, 도면 위에서 측정한 경우
- deductions_json, 공제를 적용한 경우

계산 API의 원본 입력은 `coordinates_json.calculation_inputs`에 저장합니다. 화면 재선택 시 계산 방식, 치수, 공제를 복원하며 직접 수량/수식/타입을 변경하면 오래된 입력은 무효화합니다. 확정 행의 수정에는 명시적인 확정 취소가 필요하고, 거절 행은 계산으로 되살리지 않습니다. 파일 소속과 병합 근거를 포함한 상세 계약은 `docs/INTEGRITY_FIXES.md`를 따릅니다.

## 오류 처리
- 유효하지 않은 PDF upload는 HTTP 400을 반환합니다.
- 누락된 record 또는 rendered file은 HTTP 404를 반환합니다.
- Extraction failure는 false-confirmed data를 만들지 않아야 하며, 모호한 row는 수정 가능하고 `NEEDS_REVIEW` 상태로 남아야 합니다.
- Calculation validation error는 누락되었거나 호환되지 않는 input과 함께 HTTP 400을 반환합니다.
- Frontend page는 reusable error component를 통해 API failure를 표시합니다.

## 테스트 전략
- Backend unit/API test는 model/schema 생성, upload, page processing, sheet detection/classification/search, room finish extraction, measurement generation/update/calculation, Excel export를 다룹니다.
- Frontend는 계산 재진입, 페이지 전환, 단위·상태·측정 근거 저장을 컴포넌트 회귀로 검증하고 TypeScript build와 함께 실행합니다.
- 수동 검증은 `docs/QA_SMOKE_TEST.md`와 `docs/ACCEPTANCE_CHECKLIST.md`를 따릅니다.

## 산출 탐색 보조

`services/assist_search.py`는 선택한 PDF의 원문을 검색하는 읽기 전용 도구다. 로컬 모드는 규칙으로 검색어를 만들고, AI 모드는 OpenAI Responses API의 단일 `search_sheets` function call로 검색어를 만든다. 모델이 파일·프로젝트 ID나 저장 상태를 지정할 수 없다. 모델 호출은 최대 1회, 출력 한도 500토큰, 요청 문장 최대 500자, 네트워크 timeout 25초로 제한한다.

AI API에는 요청 문장만 전송하며 PDF 원문은 보내지 않는다. 근거는 서버가 조회한 시트의 원문·시트 ID·페이지 인덱스로 구성한다. API 오류와 근거 없음은 각각 FAILED/NOT_FOUND로 표시한다. `assist_runs`는 기존 DB 테이블을 변경하지 않고 startup의 create_all로 추가되며 요청·도구·결과·사용량·소요시간을 로컬에 기록한다. API 키는 기록하지 않는다.

`GET /projects/{project_id}/drawing-files`와 공통 DrawingFilePicker로 이름 기반 도면 선택을 제공한다. 선택은 같은 브라우저 탭의 sessionStorage에 유지되며 PDF를 바꾸면 화면의 이전 결과를 초기화한다.

`services/assist_drafts.py`는 검색 실행에 묶인 마감·치수 근거로 계산 초안을 만든다. 숫자 후보의 추정 단위는 자동 적용하지 않는다. 사용자는 치수 단위·출처·검수 메모, 공제 여부와 파티션 면 수를 확인해야 한다. 서버가 원문 fingerprint·도면 소속·실 번호·마감 코드·상태·입력 범위를 검증한 뒤 기존 calculation_engine을 호출한다. 저장은 상태 조건부 UPDATE로 수행하며 CONFIRMED/REJECTED 행을 덮어쓰지 않는다. 모델에는 이 저장 API나 확정 권한을 노출하지 않는다.

입력·원문·단위·좌표·실행 ID는 `coordinates_json.assist`, 공제는 `deductions_json`에 저장한다. 같은 입력을 재시도해도 기존 Measurement 한 행만 갱신한다. 사용자가 수동 수정·확정하면 실행 기록의 review 결과를 갱신한다.

새 초안은 계산 엔진에 전달한 Decimal 입력을 `normalized_inputs`, 당시 결과를 `calculated_result`로 함께 보존한다. `GET /measurements/{id}/evidence`는 이 저장 기록과 소유 PDF 안의 출처만 읽어 대조 화면에 제공한다. 현재 원본이 바뀌었거나 결과가 수동 변경됐으면 경고한다. 이전 버전 행에 없는 정규화값은 추정하지 않는다. 이 읽기 API는 산출 행을 변경하거나 모델을 호출하지 않는다.

`services/assist_vision.py`는 기존 텍스트 추출이 부족한 경우의 선택 영역 이미지 보완이다. 서버가 DB 소유 원본 PDF에서 사용자가 선택한 사각형만 PNG로 만든다. 미리보기는 로컬 응답이며, 모델 전송은 실패 유형·메모·권한 확인과 미리보기 SHA256 일치 검사를 요구한다. 모델이 반환한 치수·실 번호·마감 코드는 vision 후보로 구분하며 자동 확정·자동 단위 정규화를 하지 않는다. 입력 좌표는 원본 페이지 이미지 좌표, 모델 bbox는 crop 상대 좌표로 해석해 저장한다. 이미지 근거를 이용해 초안을 저장할 때 crop hash를 다시 검사한다.

`evaluation_trials`는 같은 과제의 수동/보조 작업을 비교하는 사용자 관찰 기록이다. 전체 작업시간·수정/개입/오류 수·검수 결과·실행 ID·PDF 파일 hash를 저장한다. 프로그램이 판정한 정확도나 실무 성과로 취급하지 않는다. 기존 테이블을 바꾸지 않고 startup에서 새 테이블을 추가한다.
