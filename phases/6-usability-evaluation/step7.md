# 단계 7: 실무자 정답 검수와 실제 비교

## 의존성과 범위

선행 단계: 6의 인수 기준 충족. 이 단계만 하나의 브랜치와 PR로 처리한다.

## 읽어야 할 파일

- `AGENTS.md`
- `phases/README.md`
- `phases/6-usability-evaluation/README.md`
- `phases/6-usability-evaluation/index.json`
- `docs/ARCHITECTURE.md`
- `docs/ADR.md`
- `docs/COMMANDS.md`
- `docs/AI_ASSIST_AUDIT.md`
- `docs/AI_ASSIST_EVALUATION.md`
- `docs/SAMPLE_DATA_GUIDE.md`
- `docs/TAKEOFF_RULES.md`

## 작업

이용 권한이 확인된 실제 도면에서 바닥·천장·파티션 등의 정답과 공제/면 수를 실무자가 검수한다. 최소 과제 관찰 후 결함 수정 PR을 처리하고 동등 과제를 수작업/로컬/AI 보조 순서를 바꾸어 비교한다. 수작업·로컬 보조 파일럿은 도면 이용 권한과 실무자 참여가 확인되면 진행할 수 있다. AI/Vision에 실제 도면을 외부 전송하는 비교만 별도 전송 권한 확인 후 수행한다. 전송이 허용되지 않으면 해당 비교와 실제 판독 품질은 미검증으로 남기되 수작업/로컬 결과는 별도로 기록한다. 사용·수정 사례·전체 시간·최종 오류·채택 여부를 근거와 함께 기록한다. 승인 없는 사설 내용은 공개 보고서에서 제외한다.

## 인수 기준과 검증

실무자가 승인한 정답 20~50건, 실제 관찰 기록과 검수 결과·비교 가능한 시간, 실제 판독 품질/비용 또는 전송 불가에 따른 미검증 사유를 확인한다. 외부 게이트가 없으면 blocked를 유지하고 이전 요구사항의 완료를 선언하지 않는다. R-04/11/12 상태는 얻은 실제 증거 범위만 갱신한다.

공통 검사: `git diff --check`, `python scripts/doctor.py`. 기능 단계는 `docs/COMMANDS.md`의 API·스크립트·웹 테스트와 빌드를 실행한다 (`python scripts/checks.py --stage manual` 또는 표의 개별 명령). Windows에서 저장소 Python 가상환경을 사용한다. 사설 데이터와 실제 API 키 없이 CI가 통과해야 한다.

외부 Codex 읽기 전용 리뷰와 필수 CI를 통과한 뒤 머지한다. PR에 변경 이유·선택한 방식·검증·미검증 항목을 기록하고 해당 step 상태를 갱신한다. 실패/외부 조건은 `issues/6-usability-evaluation/issue-N.md`에 재현과 다음 조치를 기록한다.

## 금지사항

- 미검수 결과를 정답이나 CONFIRMED로 만들지 마라. 이유: 사용자 검수와 실무 정답은 별도 증거가 필요하다.
- 업무 PDF·산출표·DB·환경파일을 Git이나 공개 보고서에 포함하지 마라. 이유: 사설 자료와 비밀을 보존해야 한다.
- 기존 변경을 덮어쓰거나 후속 단계 기능을 함께 구현하지 마라. 이유: PR 범위와 복구 가능성을 유지해야 한다.
