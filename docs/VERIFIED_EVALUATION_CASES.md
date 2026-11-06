# 검수된 평가 사례 선택

`scripts/load_evaluation_cases.py`는 기존 4차 workbook을 읽기만 하고, 별도 JSON에 기록한 검수 범위에 따라 평가 사례를 선택한다. Excel 열과 공개 빈 템플릿은 변경하지 않는다. 구조 검사 통과나 `CONFIRMED`만으로 평가 정답이 되지 않는다.

## 검수 기록

실무자는 원본과 workbook을 대조한 뒤 Git에서 제외된 위치에 검수 JSON을 작성한다. 원본·workbook·검수 JSON은 공개하지 않는다. `workbook_sha256`은 검수한 workbook 파일 전체의 SHA256이다. workbook을 다시 저장하면 hash를 확인하고 근거를 재검수해야 한다. 프로그램은 hash나 검수 정보를 자동 승인하지 않는다.

아래는 합성 형식 예시다. 실무 자료에서는 `origin`을 최상위와 각 검수에 모두 `practitioner`로 명시하고 실제 검수자·일자를 기록한다. `synthetic`은 개발 계약 검증이며 실무자 승인이 아니다.

```json
{
  "schema_version": 1,
  "workbook_sha256": "검수한-workbook의-64자리-SHA256",
  "origin": "synthetic",
  "rows": {
    "SYN-OK": {
      "retrieval": {
        "status": "REVIEWED",
        "reviewer": "synthetic-contract-review",
        "reviewed_on": "2026-11-06",
        "origin": "synthetic",
        "unresolved_exceptions": [],
        "evidence": [{"source_id": "PLAN", "locator": "가상실 S-01: 4200mm × 2700mm"}],
        "expected_source_ids": ["PLAN"]
      }
    }
  }
}
```

- `rows`의 키는 기존 `TakeoffRows.row_id`다. 동일 row에 `retrieval`과 `quantity`를 독립적으로 기록한다. 다른 범위의 검수로 대신하지 않는다.
- 검수 `status`는 명시적인 `REVIEWED`만 인정한다. 검수자, 미래가 아닌 ISO 날짜 `YYYY-MM-DD`, 일치하는 origin, 비어 있지 않은 근거가 필요하다. 이 메타데이터는 기록자의 검수 진술이며 신원 인증이나 자동 정답 판정은 아니다.
- `evidence`는 workbook `Sources.source_id`와 원본에서 확인할 위치·텍스트를 설명하는 `locator` 목록이다. 해당 source에는 고유 ID, 제목, 0부터 시작하는 페이지 인덱스가 있어야 한다. `source_sheets`는 기존처럼 쉼표로 나눈 `Sources.sheet_no` 목록이며 없는 도면은 제외한다. 도면 번호 자체를 제품 규칙으로 고정하지 않는다.
- 검색 정답은 `retrieval.expected_source_ids`로 지정하고 모두 검수 근거에 포함한다. 검색 검수에는 수량·계산식·산출 상태가 필요하지 않다. 관련 도면 정답의 적절성은 사람이 검수한다.
- 수량 정답은 기존 workbook 행을 사용한다. `quantity` 범위 검수와 `CONFIRMED`, 타입과 호환되는 단위, 유한한 음수 아닌 수량, 식·공종·마감 코드, 비어 있지 않은 `evidence_json`, JSON object/array인 `deductions_json`이 필요하다. `[]`는 명시적인 공제 없음이다. 기존 `source_sheets`의 모든 도면을 검수 근거가 포함해야 한다. 계산식이나 공제의 업무상 정답은 자동 계산·판정하지 않는다.
- 각 범위에 `unresolved_exceptions: []`를 명시한다. 미해결 질문이 있거나 이 필드가 없으면 제외한다. 행의 `exception_tags`가 있다면 `exception_resolution`에 해당 범위에서 해결한 판단과 이유를 남긴다. 검색 정답만 확인하고 공제를 해결하지 못했다면 검색 검수에 그 한계를 적고 수량 검수의 미해결 목록은 유지한다.

## 호출과 반환 계약

```powershell
.\apps\api\.venv311\Scripts\python.exe scripts/load_evaluation_cases.py <workbook.xlsx> <reviews.json> --scope retrieval
.\apps\api\.venv311\Scripts\python.exe scripts/load_evaluation_cases.py <workbook.xlsx> <reviews.json> --scope quantity
.\apps\api\.venv311\Scripts\python.exe -m pytest scripts/test_load_evaluation_cases.py scripts/test_validate_example_dataset.py
```

CLI는 선택한 row ID와 제외 이유만 출력한다. 로컬 호출에서도 실제 업무 식별자를 외부 보고서에 그대로 옮기지 않는다. Python 호출은 아래처럼 사용한다.

```python
selection = load_evaluation_cases(Path("workbook.xlsx"), Path("reviews.json"), scope="retrieval")
for case in selection.cases:
    row = case["row"]  # 기존 TakeoffRows 열을 보존한 dict
    expected = case["review"]["expected_source_ids"]  # 검색 정답
    sources = case["sources"]  # 검수 근거의 기존 Sources 행 목록
    origin = case["origin"]  # synthetic 또는 practitioner
for excluded in selection.excluded:
    print(excluded["row_id"], excluded["row_number"], excluded["scope"], excluded["reasons"])
```

반환값 `CaseSelection.cases`가 승인된 사례 목록이다. `quantity` 범위에서는 정답이 `case["row"]["quantity"]`, `formula`, `unit`에 있다. 수량 미검수 사례도 검색 검수만 충족하면 `retrieval` 결과에 들어간다. `excluded`는 제외된 행마다 row ID·Excel 행 번호·범위·이유 코드 목록을 제공한다. 평가 지표 계산이나 모델 호출은 이 단계에 포함하지 않는다.

대표 제외 코드는 `scope_not_reviewed`, `reviewer_missing`, `review_date_invalid`, `evidence_missing`, `evidence_invalid`, `exceptions_unresolved_or_missing`, `row_id_duplicate`, `source_sheet_unknown`, `quantity_not_confirmed`, `quantity_missing_or_invalid`, `quantity_type_or_unit_invalid`, `quantity_sources_not_covered`다. 파일/hash/JSON 중복 키/필수 sheet·header 오류는 평가 전체를 거부한다. 빈 공개 템플릿은 오류 없이 0건을 반환하며 미검수 legacy 행은 이유와 함께 제외한다. 실패 사례의 수량 누락은 기존 20~50행 정상 산출 구조 검사와 별개로 허용된다.

## 합성 검증과 실무 게이트

공개 [합성 fixture](../scripts/fixtures/verified_evaluation_cases.json)는 가상 원본 근거·검수 기록·정상 수량과 수량 누락·단위 충돌·다중 도면·공제 오류·미검수 사례를 포함한다. 테스트가 임시 workbook과 hash에 묶인 sidecar를 만들어 로더의 계약을 확인한다. 테스트의 검수 기록 생성은 합성 자료에만 적용하며 실제 자료 승인 도구가 아니다. 수량 정답은 정상과 다중 도면 2건, 검색 정답은 미검수 1건을 제외한 5건이다.

실제 workbook은 수정하거나 자동 승인하지 않는다. R-04의 실무자 승인 정답 20~50건과 phase 6 step7의 실무 검증은 여전히 외부 게이트다. 합성 로더 테스트 통과를 실무 정확도·시간 단축 결과로 사용하지 않는다.
