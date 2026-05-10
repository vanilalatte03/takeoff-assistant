# 단계 1: project-workflow

## 읽어야 할 파일

먼저 아래 파일들을 읽고 현재 Project와 업로드 흐름을 파악하라:

- `/AGENTS.md`
- `/docs/REVIEW_MVP_SPEC.md`
- `/docs/ARCHITECTURE.md`
- `/docs/ADR.md`
- `/docs/COMMANDS.md`
- `/apps/api/app/models/project.py`
- `/apps/api/app/schemas/project.py`
- `/apps/api/app/api/routes/drawing_files.py`
- `/apps/api/app/main.py`
- `/apps/web/src/pages/UploadPage.tsx`
- `/apps/web/src/api/client.ts`
- `/apps/web/src/types/api.ts`

## 작업

업로드 전에 `Project ID`를 외워 입력해야 하는 흐름을 Project 선택/생성 흐름으로 보강하라.

- Backend에 Project 목록 조회와 생성 API를 추가한다.
- Project create payload는 최소 `name`을 받는다.
- Frontend API client와 TypeScript type을 추가한다.
- Upload 화면에서 Project 목록을 불러오고 선택할 수 있게 한다.
- Project가 없거나 새 프로젝트가 필요하면 같은 화면에서 생성할 수 있게 한다.
- 기존 `Project ID` 직접 입력은 debugging 보조 경로로 남겨도 되지만, 기본 CTA는 선택된 Project를 사용해야 한다.
- 관련 backend test와 frontend build 통과를 보장한다.

## 인수 기준

```powershell
.\apps\api\.venv311\Scripts\python.exe scripts\checks.py --stage manual
```

## 검증 절차

1. 위 AC 커맨드를 실행한다.
2. 아키텍처 체크리스트를 확인한다:
   - route는 `apps/api/app/api/routes` 아래에 있는가?
   - schema는 `apps/api/app/schemas` 아래에 있는가?
   - frontend API 호출은 `apps/web/src/api/client.ts`에 모였는가?
   - `COMMANDS.md`의 검증 명령을 실행했는가?
3. 결과에 따라 `phases/2-review-mvp/index.json`의 해당 단계를 업데이트한다:
   - 성공 -> `"status": "completed"`, `"summary": "업로드 화면 Project 선택/생성 흐름 추가"`
   - 수정 3회 시도 후에도 실패 -> `"status": "error"`, `"error_message": "구체적 에러 내용"`
   - 사용자 개입 필요 -> `"status": "blocked"`, `"blocked_reason": "구체적 사유"` 후 즉시 중단

검증 또는 리뷰가 통과하지 못하면 `issues/2-review-mvp/issue-N.md`에 재현 명령, 핵심 에러, 수정 방향을 기록하고 fix step을 추가한다.

## 금지사항

- cloud project storage를 추가하지 마라. 이유: ADR-001은 local-first SQLite 저장 방식을 채택한다.
- 기존 PDF upload API를 제거하지 마라. 이유: 기존 테스트와 수동 흐름이 이 endpoint에 의존한다.
- Project 생성 실패를 조용히 무시하지 마라. 이유: 업로드가 잘못된 Project에 연결되면 추적성이 깨진다.
