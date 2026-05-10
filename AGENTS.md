# AGENTS.md

## 프로젝트 정체성

이 저장소는 개인용 **PDF 도면 기반 마감 물량 산출 보조 도구**를 구현합니다.
전문 산출/견적 제품을 대체하려는 목적이 아닙니다. 목표는 건축 마감 산출 작업에서 수동 페이지 이동, 반복적인 스프레드시트 입력, 산술 오류를 줄이는 것입니다.

제품 원칙은 다음과 같습니다.

> 도면 PDF에서 자동 초안을 생성한 뒤, 사용자가 검토하고 수정하고 측정하고 export한다.

사용자 검토 없이 시스템이 완전히 정확한 산출 결과를 만들 수 있다고 가정하지 마세요.

## MVP 범위

MVP는 다음 순서로 구현합니다.

1. PDF 업로드와 로컬 저장
2. PDF 페이지를 보기용 이미지로 렌더링
3. 각 페이지의 텍스트 추출
4. 도면 번호와 도면명 감지
5. `FINISH_SCHEDULE`, `FLOOR_PLAN`, `ENLARGED_FLOOR_PLAN`, `PARTITION_PLAN`, `PARTITION_DETAIL`, `DOOR_SCHEDULE`, `WINDOW_SCHEDULE`, `UNKNOWN` 같은 도면 역할 분류
6. 마감표 페이지 감지 및 수정 가능한 Room Finish 후보 추출
7. Room Finish 데이터에서 Measurement 후보 생성
8. 사용자 직접 입력 및 PDF 페이지 이미지 위 수동 측정 지원
9. 수량과 계산식 계산
10. Summary와 Details 시트를 Excel로 export

## MVP 명시적 제외 범위

나중에 명시적으로 요청받기 전까지 첫 MVP에서는 다음을 구현하지 않습니다.

- PDF 업로드만으로 완전 자동 산출
- 자동 room boundary 인식
- 자동 dimension-line 판독
- 자동 door/window 공제
- 모든 공종 자동 지원
- XCost 연동
- 스캔 PDF용 production-grade OCR

## 도메인 규칙

사용자 조사에서 확인한 워크플로우:

- 일반적인 산출 한 줄은 약 세 장의 도면을 사용합니다.
- Room 번호는 마감표에서 확인합니다.
- Room 치수는 보통 AE101 같은 평면도에서 가져옵니다.
- Room 치수가 표시되지 않으면 사용자가 scale 기준으로 측정할 수 있습니다.
- 최종 출력은 room 중심보다 finish code 중심으로 정리되어야 합니다.
- 출력에는 계산식과 도면 source sheet가 남아야 합니다.
- 수량은 소수점 둘째 자리로 반올림합니다.

알려진 계산 패턴:

- 바닥 면적 = width * height_or_depth 또는 polygon area
- 천장 면적 = width * height_or_depth 또는 polygon area
- 둘레 길이 = 선택한 boundary length 또는 (width + depth) * 2
- 벽 마감 면적 = wall length * wall height - deductions
- 파티션 면적 = wall length * wall height * side multiplier - deductions
- 개수 수량 = 클릭한 개수

알려진 예외 패턴:

- 천장 면적에는 기둥, 벽, opening 공제가 필요할 수 있습니다.
- 바닥 면적에는 고정 가구, 장비, 벽 두께 공제가 필요할 수 있습니다.
- 벽 마감 면적에는 door/window 공제가 필요할 수 있습니다.
- GWB 파티션은 양면으로 산출될 수 있고, 다른 항목은 별도 설정이 없으면 보통 한쪽 면만 산출합니다.
- 벽 높이는 room마다 다를 수 있습니다.
- 화장실 벽 타일은 전체 벽 높이가 아니라 부분 높이를 사용할 수 있습니다.

## 기술 방향

MVP 권장 스택:

- Backend: Python FastAPI
- Database: MVP용 SQLite
- PDF processing: PyMuPDF
- Table/text extraction: PyMuPDF text block으로 시작하고, 필요하면 pdfplumber 사용
- Excel export: openpyxl
- Frontend: React + TypeScript
- PDF page viewer: 백엔드가 렌더링한 페이지 이미지 + 측정용 canvas/SVG overlay

복잡한 클라우드 인프라보다 단순하고 테스트 가능한 local-first 아키텍처를 선호합니다.

## 데이터 모델 원칙

모든 계산된 수량은 다음을 저장해야 합니다.

- project_id
- 해당되는 경우 room_no
- 해당되는 경우 room_name
- category
- finish_code
- measurement_type
- formula
- quantity
- unit
- source_sheets
- status: DRAFT, NEEDS_REVIEW, CONFIRMED
- memo
- 도면 위에서 측정한 경우 coordinates_json
- 공제를 적용한 경우 deductions_json

## 품질 기준

모든 기능에 대해:

- 테스트를 추가하거나 갱신합니다.
- 가능한 한 작고 결정적인 함수로 유지합니다.
- 추출 실패를 조용히 버리지 않습니다. confidence와 status를 반환합니다.
- AI/OCR/extraction 결과는 사용자가 수정할 수 있어야 합니다.
- 숨은 가정보다 `NEEDS_REVIEW` 같은 명시적 상태를 선호합니다.
- AE601만 하드코딩하지 않습니다. 마감표는 AE401, AE402, AE601 또는 다른 도면 번호일 수 있습니다. 도면 번호만 보지 말고 sheet title/role로 감지합니다.

## Codex 운영 템플릿

- 제품 요구사항은 `docs/PRD.md`에 두고, 기존 MVP 상세 내용은 `docs/MVP_SPEC.md`에 유지합니다.
- 아키텍처와 데이터 흐름 결정은 `docs/ARCHITECTURE.md`와 `docs/ADR.md`에 둡니다.
- 실행 가능한 명령은 `docs/COMMANDS.md`와 `.codex/project-profile.json`에 둡니다.
- 큰 작업은 Harness skill을 사용해 `phases/{phase}/index.json`, `phases/{phase}/stepN.md` 단위로 나눌 수 있습니다.
- 반복 실패 또는 blocked phase 작업은 `issues/{phase}/issue-N.md`에 기록합니다.
- 운영 템플릿 연결 상태는 `python scripts/doctor.py`로 확인합니다.
- 로컬 Python/Node 환경이 설치되어 있으면 `python scripts/checks.py --stage manual`로 설정된 프로젝트 검사를 실행합니다.

## 인수 테스트 철학

MVP는 다음 특성을 가진 샘플 건축 도면 PDF에서 동작해야 합니다.

- Index sheet가 도면 번호와 도면명을 나열합니다.
- Finish schedule sheet에는 `RM NOS`, `ROOM NAMES`, `FLOOR`, `BASE`, `INTERIOR WALL`, `CEILING`, `HGT`, `REMARKS` 같은 열이 있습니다.
- Floor plan sheet에는 room number와 room name이 있습니다.
- Enlarged floor plan에는 더 상세한 치수가 있습니다.

## Excel 출력 구조

최소 두 개의 worksheet를 생성합니다.

1. Summary
   - category
   - finish_code
   - description
   - unit
   - total_quantity
   - source_sheets

2. Details
   - no
   - room_no
   - room_name
   - category
   - finish_code
   - measurement_type
   - formula
   - quantity
   - unit
   - source_sheets
   - status
   - memo
