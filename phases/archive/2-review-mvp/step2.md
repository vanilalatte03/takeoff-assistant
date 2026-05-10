# 단계 2: room-finish-review

## 읽어야 할 파일

먼저 아래 파일들을 읽고 RoomFinish 추출/수정 흐름을 파악하라:

- `/AGENTS.md`
- `/docs/archive/REVIEW_MVP_SPEC.md`
- `/docs/DOMAIN_RULES.md`
- `/docs/ARCHITECTURE.md`
- `/docs/ADR.md`
- `/docs/COMMANDS.md`
- `/apps/api/app/models/room_finish.py`
- `/apps/api/app/models/measurement.py`
- `/apps/api/app/schemas/room_finish.py`
- `/apps/api/app/api/routes/room_finishes.py`
- `/apps/web/src/pages/RoomFinishesPage.tsx`
- `/apps/web/src/api/client.ts`
- `/apps/web/src/types/api.ts`

## 작업

RoomFinish 검수 속도를 높이고 추출 실패를 명확하게 처리하라.

- RoomFinish extraction response에 `warnings`를 추가한다.
- `FINISH_SCHEDULE` sheet가 없거나 추출 후보가 0건이면 warning을 반환한다.
- RoomFinish 목록 UI에 room no, room name, finish code, status 필터를 추가한다.
- RoomFinish 행 저장 후 현재 필터와 목록 상태를 유지한다.
- RoomFinish reject endpoint를 추가한다. HTTP method는 `DELETE /room-finishes/{id}`를 사용하되 실제 DB row는 삭제하지 않고 `REJECTED`로 변경한다.
- 연결된 Measurement 중 `CONFIRMED`가 있으면 reject를 막고 HTTP 409 또는 400을 반환한다.
- 연결된 미확정 Measurement는 RoomFinish reject와 함께 `REJECTED`로 변경한다.
- backend test와 frontend build를 갱신한다.

## 인수 기준

```powershell
.\apps\api\.venv311\Scripts\python.exe scripts\checks.py --stage manual
```

## 검증 절차

1. 위 AC 커맨드를 실행한다.
2. 아키텍처 체크리스트를 확인한다:
   - RoomFinish reject가 물리 삭제를 하지 않는가?
   - `CONFIRMED` Measurement 보호가 동작하는가?
   - extraction 0건 경로가 warning을 반환하는가?
   - `COMMANDS.md`의 검증 명령을 실행했는가?
3. 결과에 따라 `phases/archive/2-review-mvp/index.json`의 해당 단계를 업데이트한다:
   - 성공 -> `"status": "completed"`, `"summary": "RoomFinish 필터, warning, reject 흐름 추가"`
   - 수정 3회 시도 후에도 실패 -> `"status": "error"`, `"error_message": "구체적 에러 내용"`
   - 사용자 개입 필요 -> `"status": "blocked"`, `"blocked_reason": "구체적 사유"` 후 즉시 중단

검증 또는 리뷰가 통과하지 못하면 `issues/archive/2-review-mvp/issue-N.md`에 재현 명령, 핵심 에러, 수정 방향을 기록하고 fix step을 추가한다.

## 금지사항

- RoomFinish row를 물리 삭제하지 마라. 이유: source traceability와 검수 이력이 필요하다.
- `CONFIRMED` Measurement가 연결된 RoomFinish를 자동 reject하지 마라. 이유: 사용자가 확정한 산출을 보호해야 한다.
- 추출 0건을 성공 메시지만으로 처리하지 마라. 이유: 사용자가 다음 수동 작업을 알 수 있어야 한다.
