# ACCEPTANCE_CHECKLIST.md

F01~F07의 추가 저장 계약과 회귀 시나리오는 `docs/INTEGRITY_FIXES.md`를 기준으로 검증합니다. 아래 기존 체크는 실무 정답 정확도나 브라우저 전체 E2E 통과를 의미하지 않습니다.

체크 기준: 2026-05-10 코드 점검, backend pytest, frontend build 기준입니다. 실제 아버님 업무 샘플 PDF로 끝까지 눌러보는 수동 검증은 `docs/QA_SMOKE_TEST.md`에 따라 별도로 진행해야 합니다.

## 제품 인수 기준

- [x] 사용자가 PDF를 업로드할 수 있다.
- [x] 사용자가 page count를 볼 수 있다.
- [x] 사용자가 렌더링된 page image를 볼 수 있다.
- [x] 사용자가 sheet number로 sheet를 검색할 수 있다.
- [x] 사용자가 keyword로 sheet를 검색할 수 있다.
- [x] 시스템이 일반적인 건축 page에서 sheet number와 sheet title을 추출한다.
- [x] 시스템이 finish schedule page를 분류한다.
- [x] 시스템이 finish schedule detection을 AE601에만 의존하지 않는다.
- [x] 시스템이 수정 가능한 room finish candidate를 추출한다.
- [x] 사용자가 room finish row를 수동 수정할 수 있다.
- [x] 시스템이 draft measurement candidate를 생성한다.
- [x] 사용자가 치수를 직접 입력할 수 있다.
- [x] 사용자가 scale을 설정하고 page image 위에서 length/area를 측정할 수 있다.
- [x] Calculation engine이 formula, quantity, unit, source_sheets, status를 저장한다.
- [x] 수량이 소수점 둘째 자리로 반올림된다.
- [x] 사용자가 deduction을 적용할 수 있다.
- [x] 사용자가 partition/wall 작업의 side multiplier를 설정할 수 있다.
- [x] 사용자가 Excel을 export할 수 있다.
- [x] Excel에 Summary sheet가 있다.
- [x] Excel에 Details sheet가 있다.
- [x] Summary가 finish code와 category 기준으로 그룹화된다.
- [x] Details가 room, formula, quantity, status, source sheet를 유지한다.

## 기술 인수 기준

- [x] Backend test가 통과한다.
- [x] Frontend가 build된다.
- [x] 기밀 sample PDF가 공개 저장소에 커밋되지 않는다.
- [x] Extraction failure가 silent success가 아니라 `NEEDS_REVIEW` 또는 warning으로 드러난다.
- [ ] 모든 추출 데이터가 수정 가능하다. RoomFinish와 Measurement는 수정 가능하지만, sheet metadata 수정 UI/API는 아직 없다.
- [x] 모든 계산 수량을 source sheet로 추적할 수 있다.

## 샘플 검증 케이스

- [x] 직접 floor/ceiling area: 4.2 * 2.7 = 11.34 m2
- [x] Perimeter: (4.2 + 2.7) * 2 = 13.80 m
- [x] Wall/partition area: 4.2 * 4.6 = 19.32 m2
- [x] Deduction: 20.00 - 1.89 = 18.11 m2
- [x] GWB two-sided partition: 4.2 * 4.6 * 2 = 38.64 m2

## 2차 검수형 MVP 인수 기준

- [x] 사용자가 업로드 화면에서 Project를 선택할 수 있다.
- [x] 사용자가 업로드 화면에서 Project를 생성할 수 있다.
- [x] 기존 `Project ID` 직접 입력 경로가 필요한 경우 보조 경로로 남아 있다.
- [x] RoomFinish 목록을 room no, room name, finish code, status로 필터링할 수 있다.
- [x] RoomFinish 행을 빠르게 저장할 수 있고 저장 후 필터/목록 상태가 유지된다.
- [x] RoomFinish 삭제 동작은 물리 삭제가 아니라 `REJECTED` 처리다.
- [x] RoomFinish를 `REJECTED` 처리하면 연결된 미확정 Measurement도 `REJECTED` 처리된다.
- [x] `CONFIRMED` Measurement가 연결된 RoomFinish는 실수로 reject되지 않는다.
- [x] Finish schedule 추출 결과가 0건이면 수동 입력이 필요하다는 warning이 표시된다.
- [x] Measurement 후보를 category, code, type, status, room no 기준으로 찾을 수 있다.
- [x] Measurement 삭제 동작은 물리 삭제가 아니라 `REJECTED` 처리다.
- [x] `CONFIRMED` Measurement는 reject-delete되지 않는다.
- [x] 같은 room/category/code/type/unit 조건을 만족하는 Measurement만 병합할 수 있다.
- [x] 병합 후 target Measurement는 quantity, formula, source sheet, memo 추적성을 유지한다.
- [x] 병합 source Measurement는 `REJECTED`로 남는다.
- [x] 방별로 전체 후보 수, 계산 완료 수, 확정 수, 검수 필요 수, 수량 누락 수를 볼 수 있다.
- [x] 도면 위 count click으로 `COUNT` Measurement를 저장할 수 있다.
- [x] Count click 결과는 unit `EA`와 클릭 좌표 `coordinates_json`을 저장한다.
- [x] Excel export에 기존 Summary sheet가 유지된다.
- [x] Excel export에 기존 Details sheet가 유지된다.
- [x] Excel export에 검수용 Review sheet가 추가된다.
- [x] Review sheet는 `REJECTED` row를 제외한다.
- [x] Review sheet는 room, category, code, formula, quantity, unit, status, memo를 포함한다.

## 3차 도면 위 치수 선택 보조 인수 기준

- [x] 사용자가 Room No 또는 Room Name으로 관련 도면/page 후보를 찾을 수 있다.
- [x] 사용자가 후보를 선택해 도면 상세 화면으로 이동할 수 있다.
- [x] 사용자가 도면 위에서 치수 후보 탐색 영역을 선택할 수 있다.
- [x] 선택 영역 또는 sheet text 기준 치수 후보가 표시된다.
- [x] 후보 raw text, normalized value, unit guess, source sheet가 표시된다.
- [x] 후보가 없거나 불확실하면 warning과 직접 입력 fallback이 표시된다.
- [x] 사용자가 후보를 width/height/length/wall_height 등 계산 입력값에 반영할 수 있다.
- [x] 후보 선택만으로 Measurement가 자동 `CONFIRMED`되지 않는다.
- [x] 저장된 Measurement가 선택 영역과 후보 근거를 `coordinates_json`에 유지한다.
- [x] 기존 scale/line/rectangle/polygon/count click 측정 흐름이 유지된다.

## AI 보조 발전 PRD 구현 확인 (2026-11-05)

- [x] 프로젝트/PDF 이름 선택과 화면 간 선택 유지
- [x] 텍스트 근거·마감·치수 후보와 원본 페이지 연결
- [x] 사용자 확인 단위·출처·공제·면 수에 의한 DRAFT 저장
- [x] 확정 행 보호, 잘못된 근거·단위·과다 공제·오래된 원본 거부
- [x] 선택 영역 미리보기·전송 권한·hash 확인과 Vision 후보 계약 검증
- [x] 사용자 관찰 비교 기록과 PDF 버전 보존
- [x] 실제 130페이지 private PDF의 예제 두 건 개발자 재현 및 Excel 대조
- [x] 기능별 API·스크립트 회귀·웹 테스트·빌드 통과 (최신 수치는 진행 기록 참조)
- [ ] 실제 검색/Vision 모델로 품질·오류·비용·지연시간 확인
- [x] 사용자 제공 설정으로 합성 E-01~E-06/V-01~V-03 실제 모델 평가 9항목 통과 (실무 도면 품질 검증과 구분)
- [ ] 실무자가 실제 정답과 현장 공제·면 수 기준을 승인
- [ ] 동일 과제 수동/보조 실사용 비교 완료

상세 판단은 `AI_ASSIST_AUDIT.md`를 참조한다.
