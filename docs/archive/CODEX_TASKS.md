# CODEX_TASKS.md

한 번에 하나의 작업만 사용하세요. Codex에게 한 prompt로 전체 제품을 구현하라고 요청하지 마세요.

## 현재 구현 상태

2026-05-10 기준 코드 점검 결과입니다.

| 작업 | 상태 | 확인 내용 |
| --- | --- | --- |
| 작업 0: 계획과 저장소 설정 | 완료 | `README.md`, `docs/`, `apps/api`, `apps/web` 구조가 생성되어 있습니다. |
| 작업 1: FastAPI 백엔드 골격 | 완료 | FastAPI app, SQLite/SQLAlchemy model, schema, health check, DB init이 있습니다. |
| 작업 2: PDF 업로드와 저장 | 완료 | `/drawing-files/upload`가 PDF 저장, page count 계산, non-PDF/invalid PDF 거부를 처리합니다. |
| 작업 3: 페이지 렌더링과 텍스트 추출 | 완료 | `/pages/process`가 text 추출과 PNG 렌더링을 수행하고 page image endpoint가 있습니다. |
| 작업 4: Sheet number와 title 감지 | 완료 | `sheet_detector`와 detect API가 있고 index/title-block 기반 테스트가 있습니다. |
| 작업 5: Sheet role 분류 | 완료 | `FINISH_SCHEDULE`, `FLOOR_PLAN`, `PARTITION_PLAN` 등 role enum과 classifier가 있습니다. |
| 작업 6: Drawing sheet 검색 API | 완료 | sheet no, title/keyword, role 기준 검색 API와 프론트 검색 화면이 있습니다. |
| 작업 7: Finish schedule candidate 추출 | 부분 완료 | 후보 추출, 목록, 생성, 수정 API/UI는 있습니다. delete API/UI는 아직 없습니다. |
| 작업 8: Measurement candidate 생성 | 완료 | RoomFinish 기반 measurement 후보 생성과 중복 방지 로직이 있습니다. |
| 작업 9: Calculation engine | 완료 | 면적, 둘레, 벽체, 파티션, count, custom, deduction, side multiplier를 지원합니다. |
| 작업 10: React frontend 골격 | 완료 | Upload, Sheets, Drawing detail, Room Finish, Measurement 화면이 있고 `npm.cmd run build`가 통과했습니다. |
| 작업 11: PDF page viewer와 manual measurement UI | 부분 완료 | 페이지 이미지 위 scale, line, rectangle, polygon 측정과 coordinates 저장은 있습니다. count click은 아직 없습니다. |
| 작업 12: Excel export | 완료 | Summary/Details workbook export API와 프론트 다운로드가 있습니다. |
| 작업 13: 종단 간 MVP smoke test | 부분 완료 | `docs/QA_SMOKE_TEST.md`가 있습니다. 자동 E2E는 없지만, backend pytest는 `.venv311` 환경에서 110개 통과했습니다. |

요약하면 현재 레포는 **1차 MVP 기능 구현은 거의 끝났고**, 2차에서 필요한 검수형 UI 중 RoomFinish/Measurement 수정과 상태 관리는 일부 들어와 있습니다. 다음 보강 대상은 delete/merge, count click, 실제 샘플 PDF 수동 smoke test입니다.

## 작업 0: 계획과 저장소 설정

Prompt:

```text
AGENTS.md, README.md, docs/MVP_SPEC.md, docs/DOMAIN_RULES.md, docs/ACCEPTANCE_CHECKLIST.md를 읽어라.
아직 application code를 작성하지 마라.
MVP를 위한 간결한 구현 계획을 만들고, risk를 식별하고, backend/frontend folder structure를 제안하라.
그다음 시작에 필요한 최소 project skeleton file만 생성하라.
```

Acceptance:

- Codex가 scope를 올바르게 요약합니다.
- 완전 자동화를 시도하지 않습니다.
- 깔끔한 backend/frontend skeleton을 생성합니다.

---

## 작업 1: FastAPI 백엔드 골격

Prompt:

```text
apps/api 아래에 FastAPI backend skeleton을 구현하라.
Persistence에는 SQLite를 사용하라.
Project, DrawingFile, DrawingSheet, RoomFinish, Measurement를 위한 model 또는 schema를 생성하라.
기본 health check와 database initialization을 추가하라.
Health check와 model/schema creation에 대한 pytest test를 추가하라.
아직 PDF processing은 구현하지 마라.
```

Acceptance:

- Test가 통과합니다.
- Backend가 로컬에서 시작됩니다.
- Data structure에 formula, quantity, unit, source_sheets, status가 포함됩니다.

---

## 작업 2: PDF 업로드와 저장

Prompt:

```text
FastAPI backend에 PDF upload 지원을 추가하라.
업로드된 PDF는 local data/uploads directory 아래에 저장하라.
original filename, stored path, page_count, created_at이 있는 DrawingFile record를 생성하라.
PyMuPDF로 page count를 계산하라.
작은 sample PDF fixture를 사용해 test를 추가하라.
```

Acceptance:

- Upload API가 drawing_file_id와 page_count를 반환합니다.
- 유효하지 않은 non-PDF upload를 거부합니다.
- Test가 통과합니다.

---

## 작업 3: 페이지 렌더링과 텍스트 추출

Prompt:

```text
업로드된 PDF의 각 page에서 text를 추출하고 각 page를 PNG image로 렌더링하라.
page_index와 text_content가 있는 DrawingSheet record를 생성하라.
Page image를 가져오는 endpoint를 추가하라.
Text extraction과 image file creation을 검증하는 test를 추가하라.
```

Acceptance:

- Page text가 저장됩니다.
- Page image endpoint가 동작합니다.
- Test가 통과합니다.

---

## 작업 4: Sheet number와 title 감지

Prompt:

```text
Sheet detection을 구현하라.
Page text를 사용해 sheet_no와 sheet_title을 감지하라.
먼저 INDEX OF DRAWINGS / SCHEDULE OF DRAWINGS page가 있으면 이를 시도하라.
그다음 각 page의 title block text로 fallback하라.
AE601만 하드코딩하지 마라.
AE101, AE401, AE402, AE601, AE405용 sample text fixture로 test를 추가하라.
```

Acceptance:

- AE101, AE401, AE402 같은 sheet number를 감지합니다.
- `sheet_title`을 저장합니다.
- Unknown page를 안전하게 처리합니다.

---

## 작업 5: Sheet role 분류

Prompt:

```text
docs/DOMAIN_RULES.md를 사용해 sheet role classification을 구현하라.
FINISH_SCHEDULE, FLOOR_PLAN, ENLARGED_FLOOR_PLAN, CEILING_PLAN, PARTITION_PLAN, PARTITION_DETAIL, DOOR_SCHEDULE, WINDOW_SCHEDULE, DOOR_WINDOW_NUMBERING_PLAN, UNKNOWN role을 추가하라.
Title keyword classification에 대한 unit test를 추가하라.
```

Acceptance:

- AE401 INTR / EXT FINISH SCHEDULE -> FINISH_SCHEDULE
- AE101 NEW FLOOR PLAN -> FLOOR_PLAN
- AE106 ENLARGED FLOOR PLAN -> ENLARGED_FLOOR_PLAN
- AE103 PARTITION WALL PLAN -> PARTITION_PLAN

---

## 작업 6: Drawing sheet 검색 API

Prompt:

```text
Drawing sheet를 list/search하는 API를 추가하라.
Search는 sheet number, sheet title, role, page text keyword와 match되어야 한다.
page_index, sheet_no, sheet_title, role, confidence/status field를 반환하라.
Test를 추가하라.
```

Acceptance:

- 사용자가 AE101, FINISH SCHEDULE, PARTITION, DOOR를 검색할 수 있습니다.
- Test가 통과합니다.

---

## 작업 7: Finish schedule candidate 추출

Prompt:

```text
First-pass finish schedule extractor를 구현하라.
FINISH_SCHEDULE로 분류된 page에서 다음 field를 가진 room finish candidate를 parse하라:
room_no, room_name, floor_code, base_code, wall_code, ceiling_code, height, source_sheet_no, confidence, status.
Text-block과 regex 기반 parsing으로 시작하라. 완벽할 필요는 없다.
추출된 row를 API로 노출하고 create/update/delete를 허용하라.
Finish schedule page의 sample text를 사용해 test를 추가하라.
```

Acceptance:

- 수정 가능한 `RoomFinish` row를 생성합니다.
- 불완전한 결과는 `NEEDS_REVIEW`로 표시합니다.
- Test가 통과합니다.

---

## 작업 8: Measurement candidate 생성

Prompt:

```text
RoomFinish row에서 takeoff measurement candidate를 생성하라.
Floor code -> FLOOR_AREA.
Ceiling code -> CEILING_AREA.
Base code -> PERIMETER_LENGTH.
Wall code -> WALL_AREA.
각 candidate는 DRAFT이고 수정 가능하며 source_sheets를 포함해야 한다.
Test를 추가하라.
```

Acceptance:

- Candidate가 생성되지만 자동으로 confirmed 처리되지 않습니다.
- 중복 생성을 피합니다.

---

## 작업 9: Calculation engine

Prompt:

```text
FLOOR_AREA, CEILING_AREA, PERIMETER_LENGTH, WALL_AREA, PARTITION_AREA, COUNT용 calculation engine을 구현하라.
Direct numeric input, deductions, side_multiplier를 지원하라.
사람이 읽을 수 있는 formula string을 생성하라.
수량을 소수점 둘째 자리로 반올림하라.
포괄적인 unit test를 추가하라.
```

Acceptance:

- 4.2 * 2.7 -> 11.34 m2
- (4.2 + 2.7) * 2 -> 13.80 m
- 4.2 * 4.6 -> 19.32 m2
- Deductions와 side_multiplier가 동작합니다.

---

## 작업 10: React frontend 골격

Prompt:

```text
apps/web 아래에 React + TypeScript frontend를 생성하라.
Project list, PDF upload, sheet list/search, finish schedule table, measurement list page를 구현하라.
Backend integration이 아직 준비되지 않은 곳은 placeholder UI를 사용하라.
```

Acceptance:

- Frontend가 build됩니다.
- 기본 navigation이 동작합니다.

---

## 작업 11: PDF page viewer와 manual measurement UI

Prompt:

```text
Canvas 또는 SVG overlay가 있는 page image viewer를 구현하라.
Scale calibration, line measurement, rectangle area measurement, polygon area measurement, count click을 지원하라.
Measurement geometry를 JSON으로 저장하라.
Measurement result를 backend calculation engine과 연결하라.
```

Acceptance:

- 사용자가 scale을 설정할 수 있습니다.
- 사용자가 length와 area를 측정할 수 있습니다.
- Measurement가 `coordinates_json`과 함께 저장됩니다.

---

## 작업 12: Excel export

Prompt:

```text
openpyxl로 Excel export를 구현하라.
Summary와 Details 두 worksheet를 생성하라.
Summary는 confirmed와 draft measurement를 category, finish_code, unit 기준으로 그룹화한다.
Details에는 room_no, room_name, category, finish_code, measurement_type, formula, quantity, unit, source_sheets, status, memo를 포함한다.
생성된 workbook을 inspect하는 test를 추가하라.
```

Acceptance:

- Excel file을 download할 수 있습니다.
- Summary total이 정확합니다.
- Details가 formula와 source sheet를 유지합니다.

---

## 작업 13: 종단 간 MVP smoke test

Prompt:

```text
End-to-end smoke test 또는 문서화된 manual test script를 추가하라:
1. Sample PDF를 업로드한다.
2. Sheet list와 search를 검증한다.
3. Finish schedule extraction 또는 manual correction을 검증한다.
4. Measurement candidate를 생성한다.
5. Dimension 4.2와 2.7을 입력한다.
6. Formula 4.2 × 2.7과 quantity 11.34를 검증한다.
7. Excel을 export하고 Summary와 Details를 검증한다.
```

Acceptance:

- Developer가 test 또는 manual script를 따라 실행할 수 있습니다.
- MVP workflow를 시연할 수 있습니다.
