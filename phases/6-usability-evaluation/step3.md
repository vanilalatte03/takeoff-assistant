# 단계 3: 업로드부터 검수·Excel까지 안내

## 의존성과 범위

선행 단계: 0의 인수 기준 충족. 이 단계만 하나의 브랜치와 PR로 처리한다.

## 읽어야 할 파일

- `AGENTS.md`
- `phases/README.md`
- `phases/6-usability-evaluation/README.md`
- `phases/6-usability-evaluation/index.json`
- `docs/ARCHITECTURE.md`
- `docs/ADR.md`
- `docs/COMMANDS.md`
- `apps/web/src/pages/UploadPage.tsx`
- `apps/web/src/pages/AssistPage.tsx`
- `apps/web/src/components/AssistDraftForm.tsx`
- `apps/web/src/pages/RoomFinishesPage.tsx`
- `apps/web/src/pages/MeasurementsPage.tsx`
- `docs/AI_ASSIST_HANDOFF.md`
- `apps/api/tests/test_known_takeoff_workflow.py`

## 작업

기존 프로젝트/PDF 이름 선택을 재사용하고, 처리·감지·분류·마감/산출 후보·탐색·계산/검수·Excel을 화면에서 이어준다. 현재 단계와 다음 동작, 실패 원인과 재시도를 표시한다. 성공한 단계와 실패한 단계를 구분하고 기존 도면 재개를 지원한다. 110호 천장 합성 과제를 기준으로 문서 없이 안내를 따라갈 수 있도록 한다. 재처리 전에 데이터 보호 계약을 확인하고 필요 시 최소 API를 보완한다.

## 인수 기준과 검증

UI 테스트에 정상 진행, 실패 후 재시도, PDF 전환, 재개와 중복 클릭을 포함한다. 확정/제외 행 보호와 수량/출처 보존을 API 회귀로 확인한다. 합성 PDF 업로드→110호 천장 DRAFT→원본 검토→Excel 다운로드를 실제 브라우저에서 확인한다. 전체 수동 검사를 실행한다. 개발자 브라우저 확인은 실무 사용자 사용성 검증과 구분한다.

공통 검사: `git diff --check`, `python scripts/doctor.py`. 기능 단계는 `docs/COMMANDS.md`의 API·스크립트·웹 테스트와 빌드를 실행한다 (`python scripts/checks.py --stage manual` 또는 표의 개별 명령). Windows에서 저장소 Python 가상환경을 사용한다. 사설 데이터와 실제 API 키 없이 CI가 통과해야 한다.

외부 Codex 읽기 전용 리뷰와 필수 CI를 통과한 뒤 머지한다. PR에 변경 이유·선택한 방식·검증·미검증 항목을 기록하고 해당 step 상태를 갱신한다. 실패/외부 조건은 `issues/6-usability-evaluation/issue-N.md`에 재현과 다음 조치를 기록한다.

## 금지사항

- 미검수 결과를 정답이나 CONFIRMED로 만들지 마라. 이유: 사용자 검수와 실무 정답은 별도 증거가 필요하다.
- 업무 PDF·산출표·DB·환경파일을 Git이나 공개 보고서에 포함하지 마라. 이유: 사설 자료와 비밀을 보존해야 한다.
- 기존 변경을 덮어쓰거나 후속 단계 기능을 함께 구현하지 마라. 이유: PR 범위와 복구 가능성을 유지해야 한다.
