# SAMPLE_DATA_GUIDE.md

## 샘플 파일 위치

샘플 PDF는 다음 위치에 둡니다.

```text
data/samples/
```

기밀, client-owned, government, proprietary drawing을 공개 저장소에 커밋하지 마세요.
Private repository를 사용하거나 sample PDF를 git 밖에 두세요.

권장 `.gitignore` 항목:

```text
data/samples/*.pdf
data/uploads/
exports/
```

## 첫 샘플 목표

첫 번째 architectural PDF sample에서는 다음을 확인합니다.

1. Index/schedule of drawings가 감지된다.
2. Sheet number와 sheet title이 감지된다.
3. 특히 floor plan, partition plan/detail, finish schedule page 같은 architectural page를 찾을 수 있다.
4. Finish schedule text가 수정 가능한 `RoomFinish` row를 만든다.
5. Extraction이 불완전해도 사용자가 measurement row를 만들 수 있다.

## 예상 architectural sheet 예시

샘플 drawing set에는 다음과 유사한 sheet가 있을 수 있습니다.

```text
AE101 NEW FLOOR PLAN
AE102 PARTITION WALL DETAILS - 1
AE103 PARTITION WALL PLAN - 1
AE106 ENLARGED FLOOR PLAN - 1
AE107 ENLARGED FLOOR PLAN - 2
AE401 INTR / EXT FINISH SCHEDULE
AE402 INTR / EXT FINISH SCHEDULE
AE405 DOOR / WINDOW SCHEDULE
```

다른 PDF는 다음을 사용할 수 있습니다.

```text
AE101 FLOOR PLAN
AE103 REFLECTED CEILING PLAN
AE405 FLOOR PARTITION TYPE KEY PLAN
AE406 PARTITION TYPE DETAILS-1
AE601 EXTERIOR & INTERIOR FINISH SCHEDULE
AE605 DOOR/WINDOW AND LOUVER NUMBERING PLAN
AE606 DOOR SCHEDULE
```

프로그램은 고정 sheet number가 아니라 role/title로 감지해야 합니다.

## 수동 검증 예시

Measurement row를 생성합니다.

```text
room_no: 110
category: Ceiling
finish_code: ACST or GWB
measurement_type: CEILING_AREA
source_sheets: AE401, AE101 or AE601, AE103
formula: 4.2 × 2.7
quantity: 11.34
unit: m2
status: CONFIRMED
```
