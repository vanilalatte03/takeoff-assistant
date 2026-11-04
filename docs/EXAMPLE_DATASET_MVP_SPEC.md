# EXAMPLE_DATASET_MVP_SPEC.md

## 4차 MVP 범위

이 문서는 PRD의 **4차: 산출 예시 데이터셋 확장** 상세 범위를 정의합니다. 4차는 API/UI 확장이 아니라, 실제 산출 판단을 반복 가능한 예시 데이터로 축적해 이후 자동화와 AI 보조 단계의 기준 데이터를 만드는 작업입니다.

## 목표

- 실제 산출 행 20~50개를 같은 형식으로 수집합니다.
- 각 행은 참고 도면, 가져온 치수, 계산식, 공제, 예외 규칙, 검수 메모를 남깁니다.
- 데이터셋은 Excel workbook으로 작성하되, 저장소에는 익명화 템플릿과 검증 도구만 커밋합니다.
- 실제 샘플 PDF/XLSX와 업무 데이터는 `data/samples/` 아래 private 파일로 유지하고 git에 포함하지 않습니다.

## 포함 범위

### 1. Excel workbook contract

4차 데이터셋 workbook은 다음 sheet를 가져야 합니다.

- `README`: 작성 목적, private data 정책, 작성 절차
- `TakeoffRows`: 산출 예시 row의 source of truth
- `Exceptions`: 방별/마감코드별 예외 규칙 목록
- `Sources`: 참고한 sheet metadata와 출처 메모
- `Validation`: workbook 작성자가 사용할 허용 값 목록

`TakeoffRows`의 필수 header는 다음과 같습니다.

```text
row_id
room_no
room_name
category
finish_code
measurement_type
source_sheets
dimension_source
width_m
depth_m
wall_length_m
wall_height_m
side_multiplier
count
deductions_json
formula
quantity
unit
status
exception_tags
evidence_json
review_notes
```

`Exceptions`의 필수 header는 다음과 같습니다.

```text
exception_tag
description
applies_to
default_rule
example_row_id
notes
```

`Sources`의 필수 header는 다음과 같습니다.

```text
source_id
sheet_no
sheet_title
sheet_role
page_index
notes
```

### 2. 데이터 작성 규칙

- `TakeoffRows`에는 실제 검수 가능한 산출 row를 20~50개 작성합니다.
- `row_id`는 workbook 안에서 고유해야 합니다.
- `measurement_type`은 기존 domain enum인 `FLOOR_AREA`, `CEILING_AREA`, `PERIMETER_LENGTH`, `WALL_AREA`, `PARTITION_AREA`, `COUNT` 중 하나입니다.
- `unit`은 `m2`, `m`, `EA` 중 하나입니다.
- `status`는 `DRAFT`, `NEEDS_REVIEW`, `CONFIRMED` 중 하나입니다.
- `source_sheets`, `formula`, `quantity`, `unit`, `status`는 모든 row에 필요합니다.
- `deductions_json`과 `evidence_json`은 비어 있지 않다면 JSON object 또는 array여야 합니다.
- workbook cell에는 로컬 절대 경로, `data/samples/`, `data/uploads/` 같은 private path를 적지 않습니다.

### 3. 검증 도구

`scripts/validate_example_dataset.py`는 private workbook을 읽고 다음을 검증합니다.

- 필수 sheet와 header가 존재합니다.
- row 수가 20~50개입니다.
- enum 값과 unit/status가 허용 값 안에 있습니다.
- 필수 traceability field가 비어 있지 않습니다.
- JSON field가 parse 가능합니다.
- workbook cell에 private path가 없습니다.

템플릿 검증은 `--allow-empty-template` 옵션으로 수행하며, 빈 `TakeoffRows`를 허용합니다.

## 제외 범위

- Public API 또는 frontend UI 추가
- 실제 샘플 PDF/XLSX 커밋
- AI API 기반 자동 보정
- XCost import/export
- 데이터셋 row를 사용자 확인 없이 `CONFIRMED` 처리하는 자동화

## 성공 기준

1. 커밋 가능한 익명화 Excel 템플릿이 존재합니다.
2. private dataset workbook의 구조와 row 품질을 검증하는 CLI가 있습니다.
3. validator test가 정상/실패 케이스를 모두 다룹니다.
4. 20~50개 실제 산출 row를 private workbook에 입력할 수 있는 절차가 문서화되어 있습니다.
5. 4차 phase가 Harness 스킬 규칙에 맞는 자기완결 step들로 나뉘어 있습니다.
