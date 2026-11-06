# 단계 5: Vision 판독 실패 조건 평가

## 의존성과 범위

선행 단계: 1의 인수 기준 충족. 이 단계만 하나의 브랜치와 PR로 처리한다.

## 읽어야 할 파일

- `AGENTS.md`
- `phases/README.md`
- `phases/6-usability-evaluation/README.md`
- `phases/6-usability-evaluation/index.json`
- `docs/ARCHITECTURE.md`
- `docs/ADR.md`
- `docs/COMMANDS.md`
- `apps/api/app/services/assist_vision.py`
- `apps/api/tests/test_assist_vision.py`
- `scripts/evaluate_ai_live.py`
- `docs/AI_ASSIST_EVALUATION.md`
- `docs/AI_ASSIST_LIVE_RESULT.json`

## 작업

회전 문자·흐릿한 치수·숫자/실 번호 혼재·단위 없는 숫자·빈 영역의 고정 합성 이미지를 만든다. 기대 후보·불명확/확인 필요 결과를 명시하고 오탐·누락·값/단위 오류·지연·토큰을 사례별 기록한다. 대체 응답 계약 테스트와 실제 모델 품질 평가를 구분한다. 실제 모델은 별도 선택 명령이며 키/업무 도면은 저장하지 않는다. 판독 후보만으로 계산하거나 확정하지 못하는 계약을 확대 검증한다.

## 인수 기준과 검증

합성 자료와 기대값 생성이 재현 가능하고 잘못된/단위 없는 후보·모델 오류·빈 영역이 자동 계산/확정으로 이어지지 않는다. 평가 결과에는 사례/설정/실행 방식/미실행 항목이 남는다. 관련 API/스크립트 테스트와 전체 수동 검사를 실행한다. 실제 업무 도면 정확도는 step7 전송 권한과 검수 없이 완료하지 않는다.

공통 검사: `git diff --check`, `python scripts/doctor.py`. 기능 단계는 `docs/COMMANDS.md`의 API·스크립트·웹 테스트와 빌드를 실행한다 (`python scripts/checks.py --stage manual` 또는 표의 개별 명령). Windows에서 저장소 Python 가상환경을 사용한다. 사설 데이터와 실제 API 키 없이 CI가 통과해야 한다.

외부 Codex 읽기 전용 리뷰와 필수 CI를 통과한 뒤 머지한다. PR에 변경 이유·선택한 방식·검증·미검증 항목을 기록하고 해당 step 상태를 갱신한다. 실패/외부 조건은 `issues/6-usability-evaluation/issue-N.md`에 재현과 다음 조치를 기록한다.

## 금지사항

- 미검수 결과를 정답이나 CONFIRMED로 만들지 마라. 이유: 사용자 검수와 실무 정답은 별도 증거가 필요하다.
- 업무 PDF·산출표·DB·환경파일을 Git이나 공개 보고서에 포함하지 마라. 이유: 사설 자료와 비밀을 보존해야 한다.
- 기존 변경을 덮어쓰거나 후속 단계 기능을 함께 구현하지 마라. 이유: PR 범위와 복구 가능성을 유지해야 한다.
