# 단계 0: 구현 현황과 실행 계획 동기화

## 의존성과 범위

선행 단계 없음. 이 단계만 하나의 브랜치와 PR로 처리한다.

## 읽어야 할 파일

- `AGENTS.md`
- `phases/README.md`
- `phases/6-usability-evaluation/README.md`
- `phases/6-usability-evaluation/index.json`
- `docs/ARCHITECTURE.md`
- `docs/ADR.md`
- `docs/COMMANDS.md`
- `README.md`
- `docs/AI_ASSIST_PRD.md`
- `docs/AI_ASSIST_AUDIT.md`
- `docs/AI_ASSIST_PROGRESS.md`
- `docs/AI_ASSIST_HANDOFF.md`
- `docs/DEMO.md`
- `apps/api/app/services/assist_search.py`
- `apps/api/app/services/assist_drafts.py`
- `apps/web/src/pages/UploadPage.tsx`
- `apps/web/src/components/DrawingFilePicker.tsx`

## 작업

README의 AI 미구현/내부 ID 입력 설명과 PRD의 개발 착수 전 표현을 실제 구현에 맞춘다. 로컬 기능·선택적 검색 조건 추출·영역 Vision·사용자 검수 계산을 구분한다. 과거 설계와 평가 기록은 보존한다. phase의 PR별 계약과 실제 실무 게이트를 작성한다.

## 인수 기준과 검증

문서만 변경한다. 상대 링크와 명령/화면 문구를 실제 파일과 대조하고 doctor, git diff --check를 실행한다. 실무 검증이나 모델 평가를 이번에 재실행한 것처럼 기록하지 않는다.

공통 검사: `git diff --check`, `python scripts/doctor.py`. 기능 단계는 `docs/COMMANDS.md`의 API·스크립트·웹 테스트와 빌드를 실행한다 (`python scripts/checks.py --stage manual` 또는 표의 개별 명령). Windows에서 저장소 Python 가상환경을 사용한다. 사설 데이터와 실제 API 키 없이 CI가 통과해야 한다.

외부 Codex 읽기 전용 리뷰와 필수 CI를 통과한 뒤 머지한다. PR에 변경 이유·선택한 방식·검증·미검증 항목을 기록하고 해당 step 상태를 갱신한다. 실패/외부 조건은 `issues/6-usability-evaluation/issue-N.md`에 재현과 다음 조치를 기록한다.

## 금지사항

- 미검수 결과를 정답이나 CONFIRMED로 만들지 마라. 이유: 사용자 검수와 실무 정답은 별도 증거가 필요하다.
- 업무 PDF·산출표·DB·환경파일을 Git이나 공개 보고서에 포함하지 마라. 이유: 사설 자료와 비밀을 보존해야 한다.
- 기존 변경을 덮어쓰거나 후속 단계 기능을 함께 구현하지 마라. 이유: PR 범위와 복구 가능성을 유지해야 한다.
