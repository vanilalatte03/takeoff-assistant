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
