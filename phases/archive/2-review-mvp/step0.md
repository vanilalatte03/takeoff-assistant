# 단계 0: docs-and-contracts

## 읽어야 할 파일

먼저 아래 파일들을 읽고 2차 MVP의 범위와 프로젝트 규칙을 파악하라:

- `/AGENTS.md`
- `/docs/PRD.md`
- `/docs/MVP_SPEC.md`
- `/docs/archive/REVIEW_MVP_SPEC.md`
- `/docs/ACCEPTANCE_CHECKLIST.md`
- `/docs/ARCHITECTURE.md`
- `/docs/ADR.md`
- `/docs/COMMANDS.md`
- `/apps/api/app/models/project.py`
- `/apps/api/app/models/room_finish.py`
- `/apps/api/app/models/measurement.py`
- `/apps/api/app/schemas/room_finish.py`
- `/apps/api/app/schemas/measurement.py`
- `/apps/web/src/types/api.ts`

## 작업

2차 검수형 MVP 구현 전에 API contract와 타입 기대값을 정리하라.

- `docs/archive/REVIEW_MVP_SPEC.md`를 기준으로 필요한 backend endpoint, request/response shape, 상태 정책을 점검한다.
- Project 목록/생성, RoomFinish reject, Measurement reject/merge, room status, count click, Review sheet export에 필요한 schema 변경을 최소 범위로 설계한다.
- 구현 중 결정이 바뀌면 `docs/archive/REVIEW_MVP_SPEC.md`와 `docs/ACCEPTANCE_CHECKLIST.md`를 함께 갱신한다.
- 기존 `DRAFT`, `NEEDS_REVIEW`, `CONFIRMED`, `REJECTED` 상태 의미를 유지한다.

## 인수 기준

```powershell
.\apps\api\.venv311\Scripts\python.exe scripts\checks.py --stage manual
```

## 검증 절차

1. 위 AC 커맨드를 실행한다.
2. 아키텍처 체크리스트를 확인한다:
   - `ARCHITECTURE.md`의 디렉터리 구조를 따르는가?
   - `ADR.md`의 local-first, draft-first 결정을 벗어나지 않았는가?
   - `AGENTS.md`의 검수 없는 자동 확정 금지를 위반하지 않았는가?
   - `COMMANDS.md`의 검증 명령을 실행했는가?
3. 결과에 따라 `phases/archive/2-review-mvp/index.json`의 해당 단계를 업데이트한다:
   - 성공 -> `"status": "completed"`, `"summary": "2차 MVP API contract와 문서 기준 정리"`
   - 수정 3회 시도 후에도 실패 -> `"status": "error"`, `"error_message": "구체적 에러 내용"`
   - 사용자 개입 필요 -> `"status": "blocked"`, `"blocked_reason": "구체적 사유"` 후 즉시 중단

검증 또는 리뷰가 통과하지 못하면 `issues/archive/2-review-mvp/issue-N.md`에 재현 명령, 핵심 에러, 수정 방향을 기록하고 fix step을 추가한다.

## 금지사항

- AI API 연동을 추가하지 마라. 이유: PRD상 AI 보조 자동화는 5차 범위다.
- 물리 삭제를 기본 정책으로 설계하지 마라. 이유: 2차 MVP는 추적성을 위해 `REJECTED` 상태 처리를 사용한다.
- 기존 테스트 기대값을 임의로 낮추지 마라. 이유: 1차 MVP 흐름이 2차의 기반이다.
