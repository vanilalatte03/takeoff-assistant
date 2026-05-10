# 단계 4: count-measurement

## 읽어야 할 파일

먼저 아래 파일들을 읽고 manual measurement viewer와 계산 저장 흐름을 파악하라:

- `/AGENTS.md`
- `/docs/REVIEW_MVP_SPEC.md`
- `/docs/DOMAIN_RULES.md`
- `/docs/ARCHITECTURE.md`
- `/docs/ADR.md`
- `/docs/COMMANDS.md`
- `/apps/api/app/models/enums.py`
- `/apps/api/app/api/routes/measurements.py`
- `/apps/api/app/services/calculation_engine.py`
- `/apps/web/src/components/ManualMeasurementViewer.tsx`
- `/apps/web/src/components/MeasurementCalculationForm.tsx`
- `/apps/web/src/api/client.ts`
- `/apps/web/src/types/api.ts`

## 작업

도면 위 count click 측정을 구현하라.

- `ManualMeasurementViewer`에 `COUNT_CLICK` 모드를 추가한다.
- count mode에서는 사용자가 클릭한 모든 점을 유지하고, 현재 점 개수를 결과로 표시한다.
- count 결과는 `COUNT` Measurement에 저장할 수 있어야 한다.
- 저장 시 formula는 클릭 개수를 사람이 읽을 수 있게 남기고, quantity는 클릭 수, unit은 `EA`로 저장한다.
- `coordinates_json`에는 `measurement_mode`, `drawing_file_id`, `page_index`, image size, view transform, clicked points, result를 남긴다.
- `COUNT`가 아닌 Measurement에 저장하려는 경우 UI에서 명확히 막거나 경고한다.
- backend 계산 API가 이미 `COUNT`를 지원하므로, 필요한 경우 frontend 저장 경로만 보강한다.
- 관련 test 또는 manual smoke 문서 기대값을 갱신한다.

## 인수 기준

```powershell
.\apps\api\.venv311\Scripts\python.exe scripts\checks.py --stage manual
```

## 검증 절차

1. 위 AC 커맨드를 실행한다.
2. 아키텍처 체크리스트를 확인한다:
   - count 결과가 `EA` 단위로 저장되는가?
   - 클릭 좌표가 `coordinates_json`에 남는가?
   - 기존 line/rectangle/polygon 측정이 깨지지 않았는가?
   - `COMMANDS.md`의 검증 명령을 실행했는가?
3. 결과에 따라 `phases/2-review-mvp/index.json`의 해당 단계를 업데이트한다:
   - 성공 -> `"status": "completed"`, `"summary": "도면 위 count click 측정 저장 추가"`
   - 수정 3회 시도 후에도 실패 -> `"status": "error"`, `"error_message": "구체적 에러 내용"`
   - 사용자 개입 필요 -> `"status": "blocked"`, `"blocked_reason": "구체적 사유"` 후 즉시 중단

검증 또는 리뷰가 통과하지 못하면 `issues/2-review-mvp/issue-N.md`에 재현 명령, 핵심 에러, 수정 방향을 기록하고 fix step을 추가한다.

## 금지사항

- count click을 자동 객체 인식으로 확장하지 마라. 이유: 2차 범위는 사용자가 찍는 반수동 측정이다.
- 기존 scale/line/area 모드를 제거하지 마라. 이유: 1차 MVP의 주요 측정 흐름이다.
- `COUNT` 결과를 `m2`나 `m` 단위로 저장하지 마라. 이유: 개수 산출 단위는 `EA`다.
