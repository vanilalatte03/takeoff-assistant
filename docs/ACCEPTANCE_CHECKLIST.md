# ACCEPTANCE_CHECKLIST.md

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
- [ ] Extraction failure가 silent success가 아니라 `NEEDS_REVIEW`를 만든다. 생성된 RoomFinish 후보는 `NEEDS_REVIEW`지만, 추출 실패가 빈 결과로 끝나는 경로는 추가 UX 처리가 필요하다.
- [ ] 모든 추출 데이터가 수정 가능하다. RoomFinish와 Measurement는 수정 가능하지만, sheet metadata 수정 UI/API는 아직 없다.
- [x] 모든 계산 수량을 source sheet로 추적할 수 있다.

## 샘플 검증 케이스

- [x] 직접 floor/ceiling area: 4.2 * 2.7 = 11.34 m2
- [x] Perimeter: (4.2 + 2.7) * 2 = 13.80 m
- [x] Wall/partition area: 4.2 * 4.6 = 19.32 m2
- [x] Deduction: 20.00 - 1.89 = 18.11 m2
- [x] GWB two-sided partition: 4.2 * 4.6 * 2 = 38.64 m2
