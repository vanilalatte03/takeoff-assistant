# Takeoff Assistant MVP

PDF 도면 세트에서 건축 마감 물량을 산출하기 위한 개인용 웹 애플리케이션입니다.

이 애플리케이션은 사용자가 다음 작업을 더 빠르게 처리하도록 돕습니다.

1. 도면 PDF 업로드
2. 도면 번호와 도면명 추출 및 검색
3. 마감표 페이지 감지
4. Room Finish 후보 추출
5. 산출 후보 행 생성
6. 도면 이미지 위에서 치수 직접 입력 또는 수동 측정
7. 면적, 길이, 벽체 면적, 파티션 면적, 개수 산출
8. Summary와 Details 시트가 포함된 Excel 워크북 export

## 제품 원칙

시스템은 **자동 초안**을 생성합니다. 사용자가 export 전에 이를 검토하고 수정합니다.

MVP를 완전 자동 견적 시스템으로 설계하지 마세요.

## 권장 스택

- Backend: FastAPI, SQLite, PyMuPDF, openpyxl
- Frontend: React, TypeScript, canvas/SVG overlay
- Storage: PDF와 렌더링된 페이지 이미지를 위한 로컬 파일 시스템

## 저장소 구조

```text
apps/
  api/        FastAPI 백엔드
  web/        React 프론트엔드
docs/
  MVP_SPEC.md
  DOMAIN_RULES.md
  CODEX_TASKS.md
  ACCEPTANCE_CHECKLIST.md
  SAMPLE_DATA_GUIDE.md
  PRD.md
  ARCHITECTURE.md
  ADR.md
  COMMANDS.md
data/
  samples/   샘플 PDF를 여기에 둡니다. 공개 저장소에는 기밀 파일을 커밋하지 마세요.
exports/      생성된 Excel 파일 위치이며 git에서 제외됩니다.
```

## 첫 번째 샘플 목표

사용자가 제공한 도면 PDF를 첫 번째 검증 샘플로 사용합니다. 첫 목표는 완벽한 추출이 아닙니다. 첫 목표는 추출 데이터를 수정할 수 있는 사용 가능한 워크플로우입니다.

## Codex로 작업하는 방법

1. 이 파일들을 private GitHub 저장소 또는 로컬 저장소에 둡니다.
2. 샘플 PDF를 `data/samples/`에 복사합니다.
3. Codex에서 저장소를 엽니다.
4. Codex에게 먼저 `AGENTS.md`, `docs/MVP_SPEC.md`, `docs/CODEX_TASKS.md`를 읽으라고 요청합니다.
5. `docs/CODEX_TASKS.md`의 작업을 하나씩 제공합니다.
6. 각 작업 후 테스트와 짧은 diff 요약을 요청합니다.

## Codex 운영 템플릿

이 프로젝트에는 Codex 설정 템플릿이 포함되어 있습니다.

- `.codex/` hook 및 project profile 파일
- `.agents/skills/` Harness 및 review 스킬
- 선택적 로컬 Git 검사용 `.githooks/pre-commit`
- `scripts/doctor.py`, `scripts/checks.py`, `scripts/guard.py`, `scripts/execute.py`

로컬에서 Git pre-commit hook을 활성화하려면 다음을 실행합니다.

```bash
git config core.hooksPath .githooks
```

Python 3.11+ 환경을 설치한 뒤 `python scripts/doctor.py`를 실행해 설정 상태를 점검합니다.
