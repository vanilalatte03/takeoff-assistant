# AGENTS.md

## 읽는 순서

작업을 시작할 때 필요한 문서만 골라 읽습니다.

- 제품 방향: `docs/PRD.md`
- 현재 MVP 범위와 제외 범위: `docs/MVP_SPEC.md`
- 현재 phase 상세 스펙: 필요 시 `docs/DIMENSION_ASSIST_MVP_SPEC.md`
- 도메인 규칙, sheet role, 계산식: `docs/DOMAIN_RULES.md`
- 아키텍처, 데이터 흐름, 저장 계약: `docs/ARCHITECTURE.md`, `docs/ADR.md`
- 실행 명령과 로컬 환경: `docs/COMMANDS.md`, `.codex/project-profile.json`
- 인수 기준과 수동 검증: `docs/ACCEPTANCE_CHECKLIST.md`, `docs/QA_SMOKE_TEST.md`
- 샘플 PDF 준비 기준: `docs/SAMPLE_DATA_GUIDE.md`

## 핵심 제품 원칙

이 저장소는 개인용 **PDF 도면 기반 마감 물량 산출 보조 도구**입니다. 전문 산출/견적 제품을 대체하지 않습니다.

제품 원칙:

> 도면 PDF에서 자동 초안을 생성한 뒤, 사용자가 검토하고 수정하고 측정하고 export한다.

사용자 검토 없이 extraction, OCR, AI, 계산 결과를 최종 확정값으로 취급하지 마세요.

## 반드시 지킬 규칙

- Sheet number를 하드코딩하지 않습니다. AE401, AE402, AE601, AE101 등은 예시일 뿐이며 sheet title/role로 판단합니다.
- Extraction 결과는 수정 가능해야 하며 confidence 또는 status를 통해 불확실성을 드러냅니다.
- 자동 생성 row는 기본적으로 `DRAFT` 또는 `NEEDS_REVIEW`입니다. 사용자가 확인하기 전 `CONFIRMED`로 만들지 않습니다.
- 모든 계산 수량은 formula, quantity, unit, source_sheets, status를 보존합니다.
- 도면 위 측정값은 coordinates_json, 공제값은 deductions_json에 추적 가능하게 남깁니다.
- 복잡한 cloud, multi-user, 외부 견적 시스템 연동은 명시 요청 전까지 추가하지 않습니다.
- 기능 변경 시 테스트를 추가하거나 갱신하고, 관련 문서도 같이 갱신합니다.
- 가능한 한 작고 결정적인 service/helper로 구현하고, extraction failure를 조용히 성공처럼 처리하지 않습니다.

## 운영 규칙

- 운영 템플릿 상태는 `python scripts/doctor.py`로 확인합니다.
- 설정된 검사 명령은 `python scripts/checks.py --stage manual` 또는 `docs/COMMANDS.md`를 기준으로 실행합니다.
- Pull 요청을 만들거나 갱신할 때는 Codex 앱의 내장 Pull 요청 지침을 따르되, 제목/본문/리뷰 대응 댓글은 한국어로 작성합니다.
- 큰 작업은 필요할 때 `phases/{phase}/index.json`, `phases/{phase}/stepN.md` 단위로 나눕니다.
- 반복 실패나 blocked phase는 `issues/{phase}/issue-N.md`에 기록합니다.
