# 단계 4: Windows 클릭 실행·종료와 복구

## 의존성과 범위

선행 단계: 3의 인수 기준 충족. 이 단계만 하나의 브랜치와 PR로 처리한다.

## 읽어야 할 파일

- `AGENTS.md`
- `phases/README.md`
- `phases/6-usability-evaluation/README.md`
- `phases/6-usability-evaluation/index.json`
- `docs/ARCHITECTURE.md`
- `docs/ADR.md`
- `docs/COMMANDS.md`
- `scripts/run_api.py`
- `scripts/test_run_api.py`
- `apps/api/app/core/config.py`
- `apps/web/vite.config.ts`
- `docs/COMMANDS.md`
- `README.md`

## 작업

준비된 Windows 환경에서 클릭으로 API와 웹 UI를 시작하고 종료할 수 있는 도구를 제공한다. 기본 바인딩은 loopback이다. 의존성 누락·포트 충돌·서버 시작 실패를 알아볼 수 있게 표시한다. 소유한 프로세스만 종료하며 실행 중복을 처리한다. 사용자 데이터 위치와 안전한 종료/백업/복구를 안내한다. 설치 패키징과 클라우드 배포는 포함하지 않는다.

## 인수 기준과 검증

기존 프로세스 무단 종료 방지, 충돌/누락/부분 시작 실패 정리, 경로 공백, 기본 loopback을 테스트한다. 실제 Windows 시작→브라우저 화면→종료를 확인하고 포트와 프로세스 종료를 검증한다. 업무 데이터 대신 임시 DB/합성 자료를 사용한다. 전체 수동 검사를 실행한다.

공통 검사: `git diff --check`, `python scripts/doctor.py`. 기능 단계는 `docs/COMMANDS.md`의 API·스크립트·웹 테스트와 빌드를 실행한다 (`python scripts/checks.py --stage manual` 또는 표의 개별 명령). Windows에서 저장소 Python 가상환경을 사용한다. 사설 데이터와 실제 API 키 없이 CI가 통과해야 한다.

외부 Codex 읽기 전용 리뷰와 필수 CI를 통과한 뒤 머지한다. PR에 변경 이유·선택한 방식·검증·미검증 항목을 기록하고 해당 step 상태를 갱신한다. 실패/외부 조건은 `issues/6-usability-evaluation/issue-N.md`에 재현과 다음 조치를 기록한다.

## 금지사항

- 미검수 결과를 정답이나 CONFIRMED로 만들지 마라. 이유: 사용자 검수와 실무 정답은 별도 증거가 필요하다.
- 업무 PDF·산출표·DB·환경파일을 Git이나 공개 보고서에 포함하지 마라. 이유: 사설 자료와 비밀을 보존해야 한다.
- 기존 변경을 덮어쓰거나 후속 단계 기능을 함께 구현하지 마라. 이유: PR 범위와 복구 가능성을 유지해야 한다.
