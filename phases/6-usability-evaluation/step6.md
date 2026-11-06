# 단계 6: 파일럿 절차와 세 방식 비교 준비

## 의존성과 범위

선행 단계: 2, 3, 4, 5의 인수 기준 충족. 이 단계만 하나의 브랜치와 PR로 처리한다.

## 읽어야 할 파일

- `AGENTS.md`
- `phases/README.md`
- `phases/6-usability-evaluation/README.md`
- `phases/6-usability-evaluation/index.json`
- `docs/ARCHITECTURE.md`
- `docs/ADR.md`
- `docs/COMMANDS.md`
- `apps/web/src/components/ComparisonPanel.tsx`
- `apps/api/app/api/routes/assist.py`
- `apps/api/app/models/evaluation_trial.py`
- `apps/api/tests/test_evaluation_trials.py`
- `docs/AI_ASSIST_EVALUATION.md`
- `docs/QA_SMOKE_TEST.md`

## 작업

기존 수작업/manual, 로컬 보조/local, AI 보조/ai(필요 시 vision)의 과제 기록·내보내기·분석을 준비한다. 원본 파일 버전과 동등한 과제 묶음, 실행 순서·학습 효과, 재검토/수정/Excel 확인 포함 시간, 잘못된 근거 선택·개입·오류·최종 검수·채택 이유를 남긴다. 초기 한 과제 관찰 후 장애를 먼저 고치고 본 비교를 진행하는 절차를 문서화한다. 관찰 누락/미검수/서로 다른 파일 버전은 성과 비교에서 제외하고 이유를 표시한다.

## 인수 기준과 검증

합성 관찰 기록으로 동일 조건 묶음, 세 방식 구분, 누락/불일치 제외와 비교 수치를 테스트한다. 임의의 시간/정답을 실사용 결과로 저장하지 않는다. 준비 상태와 실제 미실행 항목을 명확히 보고한다. 전체 수동 검사를 실행한다.

공통 검사: `git diff --check`, `python scripts/doctor.py`. 기능 단계는 `docs/COMMANDS.md`의 API·스크립트·웹 테스트와 빌드를 실행한다 (`python scripts/checks.py --stage manual` 또는 표의 개별 명령). Windows에서 저장소 Python 가상환경을 사용한다. 사설 데이터와 실제 API 키 없이 CI가 통과해야 한다.

외부 Codex 읽기 전용 리뷰와 필수 CI를 통과한 뒤 머지한다. PR에 변경 이유·선택한 방식·검증·미검증 항목을 기록하고 해당 step 상태를 갱신한다. 실패/외부 조건은 `issues/6-usability-evaluation/issue-N.md`에 재현과 다음 조치를 기록한다.

## 금지사항

- 미검수 결과를 정답이나 CONFIRMED로 만들지 마라. 이유: 사용자 검수와 실무 정답은 별도 증거가 필요하다.
- 업무 PDF·산출표·DB·환경파일을 Git이나 공개 보고서에 포함하지 마라. 이유: 사설 자료와 비밀을 보존해야 한다.
- 기존 변경을 덮어쓰거나 후속 단계 기능을 함께 구현하지 마라. 이유: PR 범위와 복구 가능성을 유지해야 한다.
