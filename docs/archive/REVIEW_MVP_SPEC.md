# REVIEW_MVP_SPEC.md

## 2차 MVP 범위

이 문서는 PRD의 **2차: 실제 업무 검수형 MVP** 상세 범위를 정의합니다. 1차 MVP가 PDF 업로드부터 Excel export까지 동작하는 흐름을 만들었다면, 2차 MVP는 실제 샘플 도면으로 반복 검수할 때 생기는 마찰을 줄이는 데 집중합니다.

## 목표

- 사용자가 `Project ID`를 외워 입력하지 않고 업로드를 시작할 수 있습니다.
- RoomFinish와 Measurement 후보를 빠르게 찾고, 고치고, 제외하고, 확정할 수 있습니다.
- 데이터 삭제는 추적성을 위해 기본적으로 물리 삭제가 아니라 `REJECTED` 상태 처리로 남깁니다.
- 방별로 산출 진행 상태를 확인할 수 있습니다.
- Excel export는 기존 Summary/Details를 유지하면서 실제 검수에 바로 쓰기 쉬운 Review sheet를 포함합니다.

## 포함 범위

### 1. Project 선택/생성

- Backend에 Project 목록 조회와 생성 API를 추가합니다.
- Frontend 업로드 화면은 기존 `Project ID` 직접 입력을 보조 경로로 남기되, 기본 흐름은 프로젝트 선택/생성을 사용합니다.
- 프로젝트가 하나도 없으면 사용자가 화면에서 기본 프로젝트를 만들 수 있어야 합니다.

### 2. RoomFinish 검수 개선

- RoomFinish 목록에 room no, room name, finish code, status 기준 필터를 추가합니다.
- 행 저장은 현재 행만 빠르게 저장하며, 저장 후 목록 상태가 유지되어야 합니다.
- RoomFinish 삭제 동작은 물리 삭제가 아니라 `REJECTED` 상태 처리입니다.
- RoomFinish를 `REJECTED` 처리하면 연결된 미확정 Measurement도 `REJECTED` 처리합니다.
- 이미 `CONFIRMED`된 연결 Measurement가 있으면 RoomFinish reject를 막고 명확한 오류를 반환합니다.
- Finish schedule extraction이 0건을 반환하면 성공 메시지만 표시하지 않고, 수동 입력이 필요하다는 warning과 관련 drawing file/sheet 정보를 보여줍니다.

### 3. Measurement 검수 개선

- Measurement 후보는 category, code, type, status, room no 기준으로 찾을 수 있어야 합니다.
- 삭제 버튼은 미확정 row를 `REJECTED` 처리합니다.
- `CONFIRMED` row는 삭제 또는 병합 source/target으로 사용할 수 없습니다. 사용자가 먼저 상태를 되돌려야 합니다.
- 병합은 같은 `room_no`, `category`, `finish_code`, `measurement_type`, `unit`인 row끼리만 허용합니다.
- 병합 target은 quantity와 formula를 보존하거나 합산 가능한 형태로 업데이트하고, source row는 `REJECTED` 처리합니다.
- source sheet와 memo는 병합 후 추적 가능하게 합칩니다.

### 4. 방별 계산 상태

- Drawing file 기준으로 방별 상태를 조회하는 API를 추가합니다.
- 각 room은 전체 후보 수, quantity가 있는 후보 수, `CONFIRMED` 수, `NEEDS_REVIEW` 수, quantity 누락 수를 표시합니다.
- Frontend Measurement 화면은 이 상태를 요약 패널로 보여줍니다.

### 5. Count click 측정

- 도면 상세 화면의 manual measurement viewer에 count click 모드를 추가합니다.
- 사용자가 클릭한 점 개수를 `COUNT` measurement의 quantity로 저장합니다.
- 클릭 좌표, page index, scale/view metadata는 `coordinates_json`에 남깁니다.
- count 결과의 unit은 `EA`를 사용합니다.

### 6. Excel Review sheet

- 기존 Summary와 Details sheet는 유지합니다.
- Review sheet를 새로 추가합니다.
- Review sheet는 `REJECTED` row를 제외합니다.
- Review sheet는 검수자가 읽기 쉬운 순서로 `Drawing No`, `Room No`, `Room Name`, `Category`, `Code`, `Formula`, `Quantity`, `Unit`, `Status`, `Memo`를 표시합니다.
- 저장 단위는 `m2`를 유지하되, Excel 표시에서는 `m²`를 허용합니다.

## 제외 범위

- OpenAI API 또는 다른 AI API 연동
- AI 기반 완성 산출표 생성
- 자동 room boundary recognition
- 자동 dimension-line reading
- 자동 deduction detection
- 스캔 PDF용 full OCR pipeline
- XCost import/export
- cloud deployment

## 성공 기준

1. 사용자가 화면에서 Project를 선택하거나 생성한 뒤 PDF 업로드를 시작할 수 있습니다.
2. RoomFinish 후보를 필터링하고 빠르게 저장하며, 불필요한 후보를 `REJECTED` 처리할 수 있습니다.
3. 추출 0건 상황에서 사용자가 다음 수동 작업을 알 수 있습니다.
4. Measurement 후보를 수정, `REJECTED` 처리, 병합할 수 있습니다.
5. `CONFIRMED` row는 실수로 reject/merge되지 않습니다.
6. 방별 산출 진행 상태가 화면에 표시됩니다.
7. 도면 위에서 count click을 저장할 수 있습니다.
8. Excel export에 Summary, Details, Review sheet가 모두 포함됩니다.
9. Review sheet는 실제 검수에 필요한 room, formula, quantity, status, source 정보를 유지합니다.
