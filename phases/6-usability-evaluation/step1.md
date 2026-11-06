# 단계 1: 검수된 평가 사례 선택

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
- `docs/templates/README.md`
- `scripts/validate_example_dataset.py`
- `scripts/test_validate_example_dataset.py`
- `docs/EXAMPLE_DATASET_MVP_SPEC.md`
- `docs/AI_ASSIST_EVALUATION.md`

## 작업

기존 workbook과 호환성을 검토하고 검수자·검수 일자·원본 근거·미해결 예외를 관리한다. 평가 로더는 검수 완료와 근거가 확인된 사례만 반환하고 미검수/불완전 사례는 제외 이유를 제공한다. 수량 정답과 관련 도면 정답의 검수 범위를 구분한다. 공개 자료에는 합성 정답과 수량 누락·단위 충돌·다중 시트·공제 오류 실패 사례만 추가한다. 실제 private workbook은 읽기 확인 외 변경하거나 자동 승인하지 않는다.

## 인수 기준과 검증

미검수 행 제외, 검수 정보 누락/예외 미해결 거부, 승인된 합성 사례 로드, 기존 공개 빈 템플릿 호환을 테스트한다. 실제 20~50건 정답 검수는 step7의 외부 게이트로 남긴다. 관련 스크립트 테스트와 공개 템플릿 검증을 실행한다.

공통 검사: `git diff --check`, `python scripts/doctor.py`. 기능 단계는 `docs/COMMANDS.md`의 API·스크립트·웹 테스트와 빌드를 실행한다 (`python scripts/checks.py --stage manual` 또는 표의 개별 명령). Windows에서 저장소 Python 가상환경을 사용한다. 사설 데이터와 실제 API 키 없이 CI가 통과해야 한다.

외부 Codex 읽기 전용 리뷰와 필수 CI를 통과한 뒤 머지한다. PR에 변경 이유·선택한 방식·검증·미검증 항목을 기록하고 해당 step 상태를 갱신한다. 실패/외부 조건은 `issues/6-usability-evaluation/issue-N.md`에 재현과 다음 조치를 기록한다.

## 금지사항

- 미검수 결과를 정답이나 CONFIRMED로 만들지 마라. 이유: 사용자 검수와 실무 정답은 별도 증거가 필요하다.
- 업무 PDF·산출표·DB·환경파일을 Git이나 공개 보고서에 포함하지 마라. 이유: 사설 자료와 비밀을 보존해야 한다.
- 기존 변경을 덮어쓰거나 후속 단계 기능을 함께 구현하지 마라. 이유: PR 범위와 복구 가능성을 유지해야 한다.
