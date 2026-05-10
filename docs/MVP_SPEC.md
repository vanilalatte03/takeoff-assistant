# MVP_SPEC.md

## 현재 MVP 범위

이 문서는 현재 코드가 제공하는 **1차 기능 동작 MVP + 2차 실제 업무 검수형 MVP**의 범위를 정의합니다. 큰 제품 방향과 단계별 확장은 `docs/PRD.md`를 기준으로 봅니다.

현재 MVP의 목표는 PDF 도면 세트를 업로드한 뒤, 도면 검색과 마감 산출 후보 생성, 직접 치수 입력/수동 측정, 계산, Excel export까지 이어지는 검수 가능한 흐름을 제공하는 것입니다.

완료된 2차 상세 스펙은 `docs/archive/REVIEW_MVP_SPEC.md`에 보관합니다. 다음 작업 단위는 `docs/DIMENSION_ASSIST_MVP_SPEC.md`의 **3차 도면 위 치수 선택 보조**입니다.

## 사용자

PDF 도면 세트와 Excel로 건축 마감 산출을 수행하는 단일 개인 사용자입니다.

## 핵심 사용자 흐름

```text
PDF 업로드
-> 페이지 처리
-> 도면 번호/도면명/역할 감지
-> 도면 검색
-> Finish schedule 후보 추출
-> RoomFinish 검수/수정
-> Measurement 후보 생성
-> 치수 입력 또는 페이지 이미지 위 수동 측정
-> 계산 저장 및 상태 관리
-> Summary/Details/Review Excel export
```

## 포함 기능

### 1. PDF 업로드와 처리

- PDF 파일 업로드
- 원본 파일 로컬 저장
- page count 계산
- 각 페이지 텍스트 추출
- 각 페이지 PNG 이미지 렌더링
- 렌더링된 페이지 이미지 조회

### 2. Sheet index와 검색

- 페이지별 `sheet_no`, `sheet_title`, `role`, confidence 저장
- index page와 title block 기반 sheet metadata 감지
- 도면명 keyword 기반 role 분류
- sheet number, title/keyword, role 기준 검색
- page detail 화면에서 metadata와 렌더링 이미지 확인

### 3. Finish schedule extraction

`FINISH_SCHEDULE`로 분류된 페이지에서 수정 가능한 RoomFinish 후보를 만듭니다.

저장 대상:

- room_no
- room_name
- floor_material / floor_finish
- base_material / base_finish
- wall_material / wall_finish
- ceiling_material / ceiling_finish
- height
- remarks
- source_sheet_no
- confidence
- status

자동 추출 후보는 기본적으로 검수 대상이며, 불완전한 값은 사용자가 수정합니다.

### 4. Measurement candidate generation

RoomFinish row에서 draft Measurement 후보를 생성합니다.

- Floor finish -> `FLOOR_AREA`
- Ceiling finish -> `CEILING_AREA`
- Base finish -> `PERIMETER_LENGTH`
- Wall finish -> `WALL_AREA`
- Partition code -> `PARTITION_AREA`

후보는 자동 확정되지 않으며, 사용자가 수정/계산/확정합니다.

### 5. Measurement와 계산

지원하는 입력 방식:

- 숫자 직접 입력
- 렌더링된 페이지 이미지 위 scale 설정
- line length 측정
- rectangle area 측정
- polygon area 측정
- count click 측정

지원하는 계산:

- `AREA_RECTANGLE`
- `PERIMETER_RECTANGLE`
- `WALL_AREA`
- `PARTITION_AREA`
- `COUNT`
- `CUSTOM`

계산 결과는 다음을 보존합니다.

- formula
- quantity
- unit
- source_sheets
- status
- deductions_json
- coordinates_json
- memo

수량은 소수점 둘째 자리로 반올림합니다.

### 6. Excel export

Excel export는 세 worksheet를 만듭니다.

- `Summary`: category, finish_code, description, unit, total_quantity, source_sheets
- `Details`: no, room_no, room_name, category, finish_code, measurement_type, formula, quantity, unit, source_sheets, status, memo
- `Review`: rejected row를 제외한 검수용 room/category/code/formula/quantity/status/memo 목록

## 2차 검수형 MVP 완료 항목

- 업로드 전 Project 선택/생성
- RoomFinish 필터, 빠른 저장, `REJECTED` 처리
- Measurement 수정, `REJECTED` 처리, 제한된 병합
- `CONFIRMED` row 보호
- 방별 계산 상태 표시
- 도면 위 count click 측정
- 기존 Summary/Details에 검수용 Review sheet 추가

## 현재 구현상 남은 보강점

아래 항목은 다음 phase의 보강 대상으로 남아 있습니다.

- Sheet metadata 수정 UI/API
- Room No 기반 도면 상세 이동
- 도면 위 영역 선택 기반 치수 후보 표시
- 선택한 치수 후보를 계산 입력값으로 반영
- 실제 아버님 샘플 PDF 기준 end-to-end 수동 smoke test 반복

## 다음 MVP: 3차 도면 위 치수 선택 보조

3차 MVP는 자동 치수선 판독이 아니라 사용자가 선택한 방 주변 치수 후보를 고르는 반자동 흐름입니다. 상세 스펙은 `docs/DIMENSION_ASSIST_MVP_SPEC.md`를 기준으로 합니다.

- Room No 검색 후 관련 페이지 이동
- 사용자가 방 영역 드래그
- 주변 숫자 치수 후보 표시
- 사용자가 가로/세로/높이 후보 선택
- 선택값으로 면적/둘레/벽체 계산 입력 보조

3차 MVP에서도 AI API, 자동 치수선 판독, 자동 방 경계 인식은 제외합니다.

## MVP 제외 범위

현재 MVP에서는 다음을 구현하지 않습니다.

- 자동 room boundary recognition
- 자동 dimension-line reading
- 자동 deduction detection
- 스캔 PDF용 full OCR pipeline
- XCost import/export
- multi-user permission
- cloud deployment
- AI 기반 완성 산출표 자동 생성

## 성공 기준

현재 MVP는 다음을 만족하면 성공으로 봅니다.

1. 샘플 drawing PDF를 업로드하고 페이지 처리를 완료할 수 있습니다.
2. Sheet list를 추출하고 번호/키워드/역할로 검색할 수 있습니다.
3. Finish schedule page가 감지됩니다.
4. RoomFinish 후보가 표시되고 수정 가능합니다.
5. Measurement 후보를 만들고 사용자가 계산값을 저장할 수 있습니다.
6. `4.2 * 2.7 = 11.34 m2`, `(4.2 + 2.7) * 2 = 13.80 m`, `4.2 * 4.6 * 2 = 38.64 m2` 같은 기준 계산이 통과합니다.
7. Summary와 Details Excel workbook을 export할 수 있습니다.
8. Review sheet가 rejected row를 제외한 검수용 목록을 제공합니다.
9. 모든 계산 수량이 source sheet number를 유지합니다.
