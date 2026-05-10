# DOMAIN_RULES.md

## 도면 워크플로우 가정

일반적인 흐름:

```text
finish schedule -> floor plan / reflected ceiling plan -> partition plan/details -> quantity table
```

알려진 예:

```text
Ceiling area: finish schedule + reflected ceiling plan 또는 floor plan
Floor area: finish schedule + floor plan
Wall finish: finish schedule + floor plan 또는 partition plan
Partition: partition plan + partition detail
Door/window count: numbering plan + schedule
```

역할 판단에 특정 sheet number를 하드코딩하지 않습니다. 예:

- Finish schedule은 AE401, AE402, AE601 또는 다른 sheet일 수 있습니다.
- Floor plan은 AE101 또는 다른 sheet일 수 있습니다.
- Partition plan/details는 AE102, AE103, AE405, AE406, AE407 등일 수 있습니다.

## Sheet role 분류

Title keyword 기반 role detection 제안:

```text
FINISH_SCHEDULE:
  FINISH SCHEDULE, INTR / EXT FINISH SCHEDULE, INTERIOR FINISH SCHEDULE, EXTERIOR & INTERIOR FINISH SCHEDULE 포함

FLOOR_PLAN:
  FLOOR PLAN 포함, REMOVAL/DEMOLITION/ENLARGED/PARTITION 미포함

ENLARGED_FLOOR_PLAN:
  ENLARGED FLOOR PLAN 포함

CEILING_PLAN:
  REFLECTED CEILING PLAN 또는 CEILING PLAN 포함

PARTITION_PLAN:
  PARTITION과 PLAN 포함

PARTITION_DETAIL:
  PARTITION과 DETAIL 포함

DOOR_SCHEDULE:
  DOOR SCHEDULE 포함

WINDOW_SCHEDULE:
  WINDOW SCHEDULE 또는 LOUVER SCHEDULE 포함

DOOR_WINDOW_NUMBERING_PLAN:
  DOOR/WINDOW와 NUMBERING PLAN 포함
```

## Measurement category

```text
FLOOR_AREA
CEILING_AREA
PERIMETER_LENGTH
WALL_AREA
PARTITION_AREA
COUNT
```

## Calculation formula

### FLOOR_AREA

입력:

- width와 depth 또는 polygon area
- deduction은 선택

Formula:

```text
quantity = base_area - sum(deductions)
unit = m2
```

### CEILING_AREA

입력:

- width와 depth 또는 polygon area
- deduction은 선택

Formula:

```text
quantity = base_area - sum(deductions)
unit = m2
```

### PERIMETER_LENGTH

입력:

- width와 depth 또는 선택한 polyline length
- deduction은 선택

Formula:

```text
quantity = base_perimeter - sum(deductions)
unit = m
```

### WALL_AREA

입력:

- wall_length
- wall_height
- deduction은 선택

Formula:

```text
quantity = wall_length * wall_height - sum(deductions)
unit = m2
```

### PARTITION_AREA

입력:

- wall_length
- wall_height
- side_multiplier
- deduction은 선택

Formula:

```text
quantity = wall_length * wall_height * side_multiplier - sum(deductions)
unit = m2
```

알려진 관례:

- GWB는 양면을 사용하는 경우가 많습니다: `side_multiplier = 2`
- 다른 항목은 보통 한쪽 면을 사용합니다: `side_multiplier = 1`
- 이 값은 수정 가능해야 합니다.

### COUNT

입력:

- count

Formula:

```text
quantity = count
unit = EA
```

## 반올림

수량은 소수점 둘째 자리로 반올림합니다.

## Review status

다음 status를 사용합니다.

```text
DRAFT
NEEDS_REVIEW
CONFIRMED
REJECTED
```

기본 extraction result는 `CONFIRMED`가 아니라 `DRAFT` 또는 `NEEDS_REVIEW`여야 합니다.

## Source traceability

모든 measurement는 source sheet를 저장해야 합니다. 예:

```text
AE401, AE101
AE601, AE103
AE405, AE406
```

## Data extraction confidence

추출된 모든 field는 수정 가능해야 하며 confidence metadata를 포함할 수 있습니다.

권장 confidence field:

- sheet_detection_confidence
- room_finish_confidence
- measurement_confidence

## 단위

Metric output을 사용합니다.

- 면적: m2
- 길이: m
- 개수: EA

가능하면 UI와 Excel에서는 square meter를 `m²`로 표시하되, 저장 값은 normalized unit인 `m2`로 유지합니다.
