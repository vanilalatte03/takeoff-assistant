# 단계 5: excel-review-export

## 읽어야 할 파일

먼저 아래 파일들을 읽고 현재 Excel export 구조와 검수 스펙을 파악하라:

- `/AGENTS.md`
- `/docs/REVIEW_MVP_SPEC.md`
- `/docs/DOMAIN_RULES.md`
- `/docs/ARCHITECTURE.md`
- `/docs/ADR.md`
- `/docs/COMMANDS.md`
- `/apps/api/app/services/measurement_excel_exporter.py`
- `/apps/api/app/api/routes/measurements.py`
- `/apps/api/tests/test_measurement_excel_export.py`
- `/apps/api/tests/test_measurement_update_api.py`
- `/data/samples/manual_flow_export_latest.xlsx`
- `/data/samples/면적구하기.xlsx`

## 작업

기존 Summary/Details export를 유지하면서 검수용 Review sheet를 추가하라.

- Workbook sheet 순서는 `Summary`, `Details`, `Review`로 한다.
- Summary와 Details의 기존 header와 계산 결과는 기존 테스트 의도를 유지한다.
- Review sheet는 `REJECTED` Measurement를 제외한다.
- Review sheet header는 `Drawing No`, `Room No`, `Room Name`, `Category`, `Code`, `Formula`, `Quantity`, `Unit`, `Status`, `Memo`로 한다.
- Review sheet는 room no, category, code 기준으로 검수하기 쉬운 순서로 정렬한다.
- 저장 unit은 `m2`를 유지하되, Review sheet 표시에서는 `m²`를 허용한다.
- quantity numeric format은 `0.00`을 유지한다.
- openpyxl 기반 workbook test를 추가하거나 갱신한다.

## 인수 기준

```powershell
.\apps\api\.venv311\Scripts\python.exe scripts\checks.py --stage manual
```

## 검증 절차

1. 위 AC 커맨드를 실행한다.
2. 아키텍처 체크리스트를 확인한다:
   - Summary/Details 기존 구조가 불필요하게 깨지지 않았는가?
   - Review sheet가 `REJECTED` row를 제외하는가?
   - formula, source, status, memo 추적성이 유지되는가?
   - `COMMANDS.md`의 검증 명령을 실행했는가?
3. 결과에 따라 `phases/2-review-mvp/index.json`의 해당 단계를 업데이트한다:
   - 성공 -> `"status": "completed"`, `"summary": "Excel export에 검수용 Review sheet 추가"`
   - 수정 3회 시도 후에도 실패 -> `"status": "error"`, `"error_message": "구체적 에러 내용"`
   - 사용자 개입 필요 -> `"status": "blocked"`, `"blocked_reason": "구체적 사유"` 후 즉시 중단

검증 또는 리뷰가 통과하지 못하면 `issues/2-review-mvp/issue-N.md`에 재현 명령, 핵심 에러, 수정 방향을 기록하고 fix step을 추가한다.

## 금지사항

- Summary/Details sheet를 제거하지 마라. 이유: 1차 MVP export contract다.
- `REJECTED` row를 Review sheet에 포함하지 마라. 이유: Review sheet는 실제 검수/사용 후보만 보여야 한다.
- Excel export를 외부 서비스에 의존하게 만들지 마라. 이유: ADR-001은 local-first 파일 export를 채택한다.
