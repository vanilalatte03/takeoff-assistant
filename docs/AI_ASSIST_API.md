# 근거 기반 산출 보조 API

선택한 PDF 안에서 텍스트 근거와 치수 후보를 찾고, 사용자가 확인한 입력으로 기존 Decimal 엔진을 호출해 DRAFT를 저장한다. AI는 검색 인자와 선택 영역의 판독 후보만 제안하며 수량·확정 상태를 지정하지 않는다.

- `GET /assist/config`: 선택적 AI/Vision 설정 여부
- `POST /drawing-files/{id}/assist/search`: 로컬 또는 AI 검색
- `GET /drawing-files/{id}/assist/runs`: 최근 실행과 사용자 검수 기록
- `POST /drawing-files/{id}/assist/drafts`: 출처·단위·공제·면 수 확인 후 계산 초안
- `POST /drawing-files/{id}/pages/{page}/assist/vision-preview`: 로컬 선택 영역 PNG
- `POST /drawing-files/{id}/pages/{page}/assist/vision`: 미리보기 hash·전송 동의 확인 후 판독
- `GET/POST /drawing-files/{id}/assist/trials`: PDF 버전과 사용자 관찰 비교 기록
- `GET /measurements/{id}/evidence`: 저장 입력·단위 변환·출처의 읽기 전용 대조

새 assist_runs/evaluation_trials 테이블은 기존 init_db의 create_all로 추가한다. 기존 DB를 지우지 않는다. 적용 전 서버를 종료하고 DB를 백업한다. 사용자 CONFIRMED는 명시적으로 DRAFT로만 해제하며 REJECTED는 수정·복구하지 않는다. 계산 재진입 입력, 공제, 병합 근거 이력을 보존한다.

키가 없으면 로컬 검색을 사용할 수 있다. AI 검색은 요청 문장만 외부 전송하고, Vision은 사용자가 확인한 crop만 전송한다. 실패는 FAILED, 근거 없음은 NOT_FOUND이며 실제 정답 정확도와 구분한다. 외부 API 키·업무 샘플은 포함하지 않는다.
