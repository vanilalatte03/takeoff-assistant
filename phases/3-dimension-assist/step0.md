# 단계 0: docs-and-contracts

## 읽어야 할 파일

- `/AGENTS.md`
- `/docs/PRD.md`
- `/docs/MVP_SPEC.md`
- `/docs/DIMENSION_ASSIST_MVP_SPEC.md`
- `/docs/ARCHITECTURE.md`
- `/docs/ADR.md`
- `/docs/DOMAIN_RULES.md`
- `/docs/COMMANDS.md`
- `/apps/api/app/models/drawing.py`
- `/apps/api/app/models/measurement.py`
- `/apps/api/app/schemas/measurement.py`
- `/apps/web/src/components/ManualMeasurementViewer.tsx`
- `/apps/web/src/components/MeasurementCalculationForm.tsx`
- `/apps/web/src/types/api.ts`

## 작업

3차 도면 위 치수 선택 보조의 API contract와 타입 기대값을 정리하라.

- `docs/DIMENSION_ASSIST_MVP_SPEC.md`를 기준으로 필요한 endpoint, request/response shape, frontend type을 점검한다.
- 자동 치수선 판독이 아니라 사용자 영역 선택 + 후보 표시 + 사용자 선택 흐름으로 설계한다.
- 후보가 없거나 좌표 정합이 불확실한 경우 warning과 직접 입력 fallback을 명시한다.
- 기존 수동 측정 모드(scale/line/rectangle/polygon/count click)를 깨뜨리지 않는 확장 지점을 정한다.
- 결정이 바뀌면 `docs/DIMENSION_ASSIST_MVP_SPEC.md`와 `docs/ACCEPTANCE_CHECKLIST.md`를 함께 갱신한다.

## 인수 기준

```powershell
.\apps\api\.venv311\Scripts\python.exe scripts\checks.py --stage manual
```

## 검증 절차

1. 위 AC 커맨드를 실행한다.
2. contract가 `ARCHITECTURE.md`의 모듈 경계를 따르는지 확인한다.
3. `phases/3-dimension-assist/index.json`의 해당 단계를 업데이트한다.

## 금지사항

- AI API를 추가하지 마라.
- 자동 room boundary recognition을 구현하지 마라.
- 후보를 사용자 확인 없이 확정값으로 저장하지 마라.
