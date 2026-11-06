# 산출 예시 Excel 템플릿

[example_dataset_template.xlsx](example_dataset_template.xlsx)은 사람이 검수한 산출 예시를 기록하기 위한 빈 workbook입니다. 실제 업무 데이터, 고객명, 로컬 경로, 외부 링크는 포함하지 않습니다. 앱의 Excel export나 import 형식과는 별개입니다.

## 작성

1. 원본 템플릿을 보존하고 `data/samples/takeoff_example_dataset_private.xlsx` 등 Git에서 제외된 위치에 사본을 만듭니다.
2. `TakeoffRows`에 예시 20~50개를 기록합니다. `row_id`, 공종·마감 코드·산출 타입·출처 도면·계산식·수량·단위·검토 상태가 필요합니다.
3. `Exceptions`에 공제·예외 규칙, `Sources`에 익명화한 도면 정보, `deductions_json`과 `evidence_json`에 근거를 기록합니다. JSON 필드가 비어 있지 않다면 object 또는 array로 작성합니다.
4. 자동 추출·계산 결과는 `DRAFT` 또는 `NEEDS_REVIEW`로 기록하고 사람이 검토한 행만 `CONFIRMED`로 바꿉니다.
5. 고객명, 주소, 도면 원본, 로컬·비공개 파일 경로를 넣은 사본을 공개하지 않습니다. 예시 도면 번호는 고정 규칙이 아닙니다.

열 이름과 허용 값은 [데이터셋 계약](../EXAMPLE_DATASET_MVP_SPEC.md)에 있습니다. 이 도구는 실제 데이터셋을 자동 수집하거나 검수하지 않습니다.

## 생성과 검증

[README 설치](../../README.md)의 Python 의존성을 준비한 뒤 저장소 루트에서 실행합니다.

```powershell
.\apps\api\.venv311\Scripts\python.exe scripts/create_example_dataset_template.py
.\apps\api\.venv311\Scripts\python.exe scripts/validate_example_dataset.py docs/templates/example_dataset_template.xlsx --allow-empty-template
.\apps\api\.venv311\Scripts\python.exe scripts/validate_example_dataset.py data/samples/takeoff_example_dataset_private.xlsx
```

첫 명령은 공개 템플릿 경로를 다시 생성하므로 작성 중인 workbook을 그 경로에 저장하지 않습니다. 빈 템플릿은 `--allow-empty-template`으로만 검증을 통과합니다. 일반 검증은 20~50행, 필수 sheet/header, 필수 값, 타입·단위·상태, JSON 형식과 일부 로컬 경로 패턴을 확인합니다.

검증은 계산식의 정답, 공제의 적절성, 개인정보·기밀 정보 전체를 판정하지 않습니다. 구조 검증을 통과해도 공개 가능한 자료라는 뜻이 아니므로, 사본은 비공개로 유지하고 사람이 검토합니다.

평가 정답으로 사용할 때는 [별도 검수 기록과 평가 로더](../VERIFIED_EVALUATION_CASES.md)를 사용합니다. 기존 열은 그대로 두고, 검색/수량 범위별 검수자·일자·근거·미해결 예외를 workbook hash에 묶습니다. 미검수 행은 원본에 보존하면서 평가에서 제외합니다.
