# 단계 4: vision-and-field-validation

## 읽어야 할 파일

- /AGENTS.md
- /docs/AI_ASSIST_PRD.md
- /docs/AI_ASSIST_PROGRESS.md
- /docs/TAKEOFF_RULES.md
- /docs/ARCHITECTURE.md
- /docs/ADR.md
- /docs/COMMANDS.md

## 작업

실제 실패 영역 Vision 보완 및 승인된 실무 도면 비교 평가

기존 변경을 보존하고 결정적인 service/helper와 API/UI 경계로 구현한다. 현재 상태와 검증 결과는 AI_ASSIST_PROGRESS.md에 기록한다.

## 인수 기준

`.\apps\api\.venv311\Scripts\python.exe scripts\checks.py --stage manual`

기능별 API 테스트와 실제 브라우저 검증을 수행한다. 실모델·실제 도면 검증이 없으면 합성 테스트로 대신 완료 처리하지 않는다. E-01~E-06의 대응 증거를 남긴다.

## 금지사항

- AI가 CONFIRMED를 저장하지 마라. 이유: 사용자 검수 전 자동 확정은 허용되지 않는다.
- 모델이 프로젝트 범위나 로컬 파일 경로를 고르게 하지 마라. 이유: 선택한 도면 범위를 서버가 보장해야 한다.
- 실제 고객 도면을 허가 없이 외부 전송하지 마라. 이유: 도면 사용 권한과 기밀 여부를 확인해야 한다.
