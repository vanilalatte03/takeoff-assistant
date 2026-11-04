# SAMPLE_DATA_GUIDE.md

공개 검증에는 [직접 생성하는 합성 PDF 데모](DEMO.md)를 먼저 사용합니다. 실제 도면 없이 추출·계산·Excel 흐름을 확인할 수 있습니다. 프로젝트 소스의 라이선스가 업무 자료의 재배포 권한을 부여하지는 않습니다. [라이선스 정책](LICENSE_POLICY.md)을 참고하세요.

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

## 4차 산출 예시 데이터셋

4차 private dataset은 실제 산출 예시 row를 모으는 workbook입니다.

권장 private 파일명:

```text
data/samples/takeoff_example_dataset_private.xlsx
```

이 파일은 git에 커밋하지 않습니다. 저장소에는 익명화 템플릿만 둡니다.

```text
docs/templates/example_dataset_template.xlsx
```

작성 후 다음 명령으로 구조와 필수 값을 검증합니다.

```powershell
.\apps\api\.venv311\Scripts\python.exe scripts\validate_example_dataset.py data\samples\takeoff_example_dataset_private.xlsx
```

검증 대상:

- `TakeoffRows`에 실제 산출 row 20~50개가 있다.
- 각 row가 source sheet, formula, quantity, unit, status를 가진다.
- `deductions_json`과 `evidence_json`이 비어 있지 않다면 JSON으로 parse된다.
- workbook cell에 로컬 절대 경로나 `data/samples/` 같은 private path가 없다.

작성·재생성 방법과 검증 범위는 [템플릿 안내](templates/README.md)를 참고하세요. 검증 통과가 개인정보 제거·계산 정답·실무 검수를 보증하지 않습니다.
