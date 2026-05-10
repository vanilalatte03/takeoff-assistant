# 단계 6: smoke-test-docs

## 읽어야 할 파일

먼저 아래 파일들을 읽고 기존 수동 검증 절차와 2차 인수 기준을 파악하라:

- `/AGENTS.md`
- `/docs/REVIEW_MVP_SPEC.md`
- `/docs/ACCEPTANCE_CHECKLIST.md`
- `/docs/QA_SMOKE_TEST.md`
- `/docs/SAMPLE_DATA_GUIDE.md`
- `/docs/COMMANDS.md`
- `/apps/web/README.md`
- `/apps/api/README.md`

## 작업

실제 샘플 PDF 기준 2차 수동 smoke test 문서를 갱신하라.

- `docs/QA_SMOKE_TEST.md`에 2차 검수형 MVP 절차를 추가한다.
- Project 선택/생성, RoomFinish reject, Measurement reject/merge, room status, count click, Review sheet 확인 절차를 포함한다.
- 테스트 기록 양식에 검증한 Project, reject/merge 대상, Review sheet 결과를 기록할 수 있게 한다.
- 실패 기준에 `CONFIRMED` 보호 실패, 물리 삭제, Review sheet 누락, `REJECTED` row 포함을 추가한다.
- `docs/ACCEPTANCE_CHECKLIST.md`의 2차 항목과 문서 절차가 서로 맞는지 확인한다.
- 자동 E2E를 새로 만들지 않아도 되지만, 수동 검증자가 그대로 따라 할 수 있게 단계와 기대 결과를 구체적으로 쓴다.

## 인수 기준

```powershell
.\apps\api\.venv311\Scripts\python.exe scripts\checks.py --stage manual
```

## 검증 절차

1. 위 AC 커맨드를 실행한다.
2. 아키텍처 체크리스트를 확인한다:
   - smoke 문서가 실제 UI/API 흐름과 맞는가?
   - 2차 acceptance checklist와 누락 없이 대응하는가?
   - 기밀 sample PDF를 새로 커밋하도록 지시하지 않는가?
   - `COMMANDS.md`의 검증 명령을 실행했는가?
3. 결과에 따라 `phases/2-review-mvp/index.json`의 해당 단계를 업데이트한다:
   - 성공 -> `"status": "completed"`, `"summary": "2차 수동 smoke test 문서 갱신"`
   - 수정 3회 시도 후에도 실패 -> `"status": "error"`, `"error_message": "구체적 에러 내용"`
   - 사용자 개입 필요 -> `"status": "blocked"`, `"blocked_reason": "구체적 사유"` 후 즉시 중단

검증 또는 리뷰가 통과하지 못하면 `issues/2-review-mvp/issue-N.md`에 재현 명령, 핵심 에러, 수정 방향을 기록하고 fix step을 추가한다.

## 금지사항

- 기밀 샘플 PDF를 공개 저장소에 추가하라고 지시하지 마라. 이유: sample data는 로컬 검증용이다.
- 2차 smoke test에서 AI API 사용을 요구하지 마라. 이유: AI 보조 자동화는 5차 범위다.
- 수동 검증 실패를 성공 기준으로 완화하지 마라. 이유: 2차 목표는 실제 사용 가능한 검수 흐름이다.
