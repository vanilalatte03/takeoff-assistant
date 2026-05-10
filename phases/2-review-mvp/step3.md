# 단계 3: measurement-review

## 읽어야 할 파일

먼저 아래 파일들을 읽고 Measurement 후보/계산/상태 흐름을 파악하라:

- `/AGENTS.md`
- `/docs/REVIEW_MVP_SPEC.md`
- `/docs/DOMAIN_RULES.md`
- `/docs/ARCHITECTURE.md`
- `/docs/ADR.md`
- `/docs/COMMANDS.md`
- `/apps/api/app/models/measurement.py`
- `/apps/api/app/schemas/measurement.py`
- `/apps/api/app/api/routes/measurements.py`
- `/apps/api/app/services/measurement_candidate_generator.py`
- `/apps/web/src/pages/MeasurementsPage.tsx`
- `/apps/web/src/components/MeasurementCalculationForm.tsx`
- `/apps/web/src/api/client.ts`
- `/apps/web/src/types/api.ts`

## 작업

Measurement 후보 검수, reject-delete, 병합, 방별 상태 표시를 구현하라.

- `DELETE /measurements/{id}`를 추가하되 물리 삭제가 아니라 `REJECTED` 상태 변경으로 구현한다.
- `CONFIRMED` Measurement는 reject-delete할 수 없게 막는다.
- `POST /measurements/merge`를 추가한다.
- merge request shape는 `{ "target_id": number, "source_ids": number[] }`로 한다.
- 병합은 같은 `room_no`, `category`, `finish_code`, `measurement_type`, `unit`인 row끼리만 허용한다.
- `CONFIRMED` row는 target/source 모두 병합 불가로 처리한다.
- 병합 target은 quantity 합산이 가능한 경우 합산하고, formula/source_sheets/memo는 source 추적성을 잃지 않게 합친다.
- 병합 source row는 `REJECTED`로 변경한다.
- `GET /drawing-files/{id}/room-status`를 추가해 방별 전체 후보 수, quantity 있음, confirmed, needs review, missing quantity 수를 반환한다.
- Frontend Measurement 화면에 reject, merge, room status UI를 추가한다.
- backend test와 frontend build를 갱신한다.

## 인수 기준

```powershell
.\apps\api\.venv311\Scripts\python.exe scripts\checks.py --stage manual
```

## 검증 절차

1. 위 AC 커맨드를 실행한다.
2. 아키텍처 체크리스트를 확인한다:
   - Measurement reject가 물리 삭제를 하지 않는가?
   - 병합 조건이 API와 UI에서 일관되는가?
   - `CONFIRMED` row 보호가 동작하는가?
   - room status 집계가 `drawing_file_id` 범위에 묶이는가?
   - `COMMANDS.md`의 검증 명령을 실행했는가?
3. 결과에 따라 `phases/2-review-mvp/index.json`의 해당 단계를 업데이트한다:
   - 성공 -> `"status": "completed"`, `"summary": "Measurement reject/merge와 방별 상태 UI 추가"`
   - 수정 3회 시도 후에도 실패 -> `"status": "error"`, `"error_message": "구체적 에러 내용"`
   - 사용자 개입 필요 -> `"status": "blocked"`, `"blocked_reason": "구체적 사유"` 후 즉시 중단

검증 또는 리뷰가 통과하지 못하면 `issues/2-review-mvp/issue-N.md`에 재현 명령, 핵심 에러, 수정 방향을 기록하고 fix step을 추가한다.

## 금지사항

- Measurement row를 물리 삭제하지 마라. 이유: Details/Review 추적성과 검수 이력이 필요하다.
- 다른 room/category/code/type/unit의 Measurement를 병합하지 마라. 이유: Summary 합계와 산출 의미가 깨진다.
- `CONFIRMED` row를 자동 변경하지 마라. 이유: 확정은 사용자 의사로만 변경되어야 한다.
