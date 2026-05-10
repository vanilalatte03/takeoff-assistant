# QA_SMOKE_TEST.md

## 목적

샘플 PDF를 기준으로 1차 MVP가 실제 마감 물량 산출 보조 도구로 사용할 수 있는지 확인한다.

검증 목표는 완전 자동 적산이 아니다. 아래 흐름이 가능해야 한다.

```text
Project 선택/생성 -> PDF 업로드 -> 도면 목록/검색 -> 마감표 후보 확인/수정/reject
-> Measurement 후보 생성 -> 직접 치수 입력/계산/reject/merge/count click
-> CONFIRMED 처리 -> Excel Summary/Details/Review 확인
```

## 사전 준비

- 샘플 PDF를 `data/samples/` 아래에 둔다.
- 샘플 PDF, 업로드 파일, Excel 결과물은 공개 저장소에 커밋하지 않는다.
- FastAPI 서버와 React 개발 서버를 실행한다.
- 업로드 화면에서 기존 Project를 선택하거나 새 Project를 생성한다.
- 기존 `Project ID` 직접 입력은 보조 경로로만 사용한다.

## 테스트 기록 양식

```text
검증일:
검증자:
샘플 PDF 파일명:
Project ID:
Project 이름:
Drawing File ID:
RoomFinish reject 대상:
Measurement reject 대상:
Measurement merge target/source:
Count click 대상 Measurement:
Review sheet 확인 결과:
사용한 주요 도면:
  - 평면도:
  - 마감표:
  - 기타:
최종 Excel 파일명:
전체 판정: 통과 / 실패
```

## 1. Project 선택/생성

### 절차

1. 앱에서 `PDF 업로드` 화면을 연다.
2. Project 목록에서 기존 Project를 선택한다.
3. 새 Project가 필요하면 이름과 설명을 입력하고 `Create project`를 누른다.
4. 생성된 Project가 선택되는지 확인한다.
5. 보조 경로로 `Project ID` 직접 입력도 가능한지 확인한다.

### 기대 결과

- Project 목록이 표시된다.
- 새 Project를 화면에서 생성할 수 있다.
- 생성한 Project ID로 PDF 업로드를 시작할 수 있다.

### 체크

- [ ] 기존 Project 선택 가능
- [ ] 새 Project 생성 가능
- [ ] 생성 후 선택 상태 확인
- [ ] Project ID 보조 입력 경로 유지

## 2. PDF 업로드

### 절차

1. 선택된 Project를 확인한다.
2. 샘플 PDF를 선택한다.
3. `PDF 업로드`를 누른다.

### 기대 결과

- 업로드가 성공한다.
- 업로드된 파일명이 표시된다.
- `Drawing File ID`가 표시된다.
- 페이지 수가 표시된다.

### 체크

- [ ] PDF 업로드 성공
- [ ] 파일명 확인
- [ ] Drawing File ID 확인
- [ ] 페이지 수 확인

### 실패 시 확인

- `Project not found.`가 나오면 Project ID가 DB에 존재하는지 확인한다.
- PDF가 아닌 파일이 거부되는 것은 정상이다.
- 손상된 PDF가 거부되는 것은 정상이다.

## 3. 도면 목록 생성

### 절차

1. 업로드 완료 후 아래 순서대로 실행한다.
   - `페이지 처리`
   - `도면 정보 추출`
   - `역할 분류`
2. `도면 검색으로 이동`을 누른다.
3. 검색어를 비워두고 검색한다.

### 기대 결과

- 페이지별 도면 목록이 표시된다.
- 각 결과에 `Page`, `Sheet No`, `Sheet Title`, `Role`, `Confidence`가 표시된다.
- 도면 번호가 특정 번호로 고정되지 않는다.

### 체크

- [ ] 페이지 처리 성공
- [ ] 도면 번호 추출
- [ ] 도면명 추출
- [ ] 도면 역할 분류
- [ ] 여러 장의 도면이 목록에 표시

## 4. AE101 같은 평면도 검색

### 절차

1. `도면 목록/검색` 화면에서 `Drawing File ID`를 입력한다.
2. 검색어에 `AE101`을 입력한다.
3. 검색 결과가 없으면 `FLOOR PLAN` 또는 `NEW FLOOR PLAN`으로 다시 검색한다.
4. 역할 필터에서 `FLOOR_PLAN`도 확인한다.

### 기대 결과

- AE101 또는 평면도에 해당하는 도면이 검색된다.
- 샘플마다 도면 번호가 다를 수 있으므로, 번호 검색 실패 시 도면명/역할 검색으로 찾을 수 있어야 한다.

### 체크

- [ ] `AE101` 검색 가능
- [ ] 평면도 제목 키워드 검색 가능
- [ ] `FLOOR_PLAN` 역할 필터 가능
- [ ] 상세 화면에서 페이지 이미지 확인 가능

## 5. AE401 또는 AE402 같은 마감표 검색

### 절차

1. 검색어에 `AE401`을 입력한다.
2. 결과가 없으면 `AE402`, `FINISH SCHEDULE`, `INTR / EXT FINISH SCHEDULE`로 검색한다.
3. 역할 필터에서 `FINISH_SCHEDULE`을 선택한다.

### 기대 결과

- 마감표 도면이 검색된다.
- 마감표가 반드시 `AE601`이라고 가정하지 않는다.
- 샘플에 따라 `AE401`, `AE402`, `AE601` 또는 다른 번호도 허용된다.

### 체크

- [ ] `AE401` 또는 `AE402` 검색 가능
- [ ] 마감표 제목 키워드 검색 가능
- [ ] `FINISH_SCHEDULE` 역할 필터 가능
- [ ] 마감표가 AE601로 하드코딩되지 않음

## 6. FINISH_SCHEDULE에서 RoomFinish 후보 확인

### 절차

1. `Room Finish` 화면으로 이동한다.
2. `Drawing File ID`를 입력한다.
3. `후보 추출`을 누른다.
4. 추출 결과를 확인한다.

### 기대 결과

- `FINISH_SCHEDULE`로 분류된 페이지에서 Room Finish 후보가 생성된다.
- 결과에는 가능한 경우 아래 값이 채워진다.
  - Room No
  - Room Name
  - Floor
  - Base
  - Wall
  - Ceiling
  - Height
  - Source
- 추출 결과는 확정값이 아니며 `NEEDS_REVIEW` 또는 검수 가능한 상태여야 한다.

### 체크

- [ ] RoomFinish 후보 생성
- [ ] Room No 확인
- [ ] Room Name 확인
- [ ] Floor/Base/Wall/Ceiling 후보 확인
- [ ] Source sheet 확인
- [ ] 검수 필요 상태 확인

### 실패 시 허용 기준

- 샘플 PDF의 마감표 구조가 복잡하면 일부 열이 비거나 잘못 추출될 수 있다.
- 자동 추출이 완벽하지 않아도, 사용자가 수정할 수 있으면 MVP 기준에 부합한다.
- 스캔 PDF는 OCR이 MVP 범위가 아니므로 텍스트 추출 실패가 발생할 수 있다.

## 7. RoomFinish 수정/필터/reject

### 절차

1. RoomFinish 테이블에서 한 Room을 선택한다.
2. 아래 값을 샘플 도면과 대조해 수정한다.
   - Room No
   - Room Name
   - Floor
   - Base
   - Wall
   - Ceiling
   - Height
3. `저장`을 누른다.
4. Room No, Room Name, finish code, status 필터를 각각 적용한다.
5. 불필요한 미확정 RoomFinish를 하나 골라 `Reject`를 누른다.
6. 연결된 `CONFIRMED` Measurement가 있는 RoomFinish reject가 차단되는지 확인한다.

### 기대 결과

- 수정한 값이 저장된다.
- 목록을 다시 조회해도 수정값이 유지된다.
- 필터를 적용해도 저장 후 목록 상태가 유지된다.
- Reject는 row를 삭제하지 않고 `REJECTED` 상태로 남긴다.
- 연결된 미확정 Measurement는 함께 `REJECTED`가 된다.
- 연결된 `CONFIRMED` Measurement가 있으면 reject가 실패한다.

### 체크

- [ ] Room No 수정 가능
- [ ] Room Name 수정 가능
- [ ] Floor/Base/Wall/Ceiling 수정 가능
- [ ] Height 수정 가능
- [ ] 저장 후 수정값 유지
- [ ] RoomFinish 필터 가능
- [ ] RoomFinish reject 시 물리 삭제 없음
- [ ] 미확정 Measurement cascade reject 확인
- [ ] CONFIRMED 연결 row 보호 확인

## 8. Measurement 후보 생성

### 절차

1. `Measurement` 화면으로 이동한다.
2. `Drawing File ID`를 입력한다.
3. `후보 생성`을 누른다.
4. Measurement 목록을 확인한다.

### 기대 결과

- RoomFinish 기준으로 마감 코드별 Measurement 후보가 생성된다.
- Floor code가 있으면 `FLOOR_AREA` 후보가 생성된다.
- Ceiling code가 있으면 `CEILING_AREA` 후보가 생성된다.
- Wall code가 있으면 `WALL_AREA` 후보가 생성된다.
- Base code가 있으면 `PERIMETER_LENGTH` 후보가 생성된다.
- 후보의 수량은 아직 비어 있거나 검수 전 상태여야 한다.

### 체크

- [ ] FLOOR_AREA 후보 생성
- [ ] CEILING_AREA 후보 생성
- [ ] WALL_AREA 후보 생성
- [ ] PERIMETER_LENGTH 후보 생성
- [ ] Room별 후보가 남아 있음
- [ ] source_sheets에 마감표 도면 번호가 남아 있음

## 9. Measurement 필터/reject/merge/방별 상태

### 절차

1. `Measurement` 화면에서 Drawing File ID를 입력하고 목록을 조회한다.
2. Room Status 패널에서 방별 `Total`, `Qty`, `Confirmed`, `Review`, `Missing` 값을 확인한다.
3. Room No, Category, Code, Type, Status 필터를 각각 적용한다.
4. 미확정 Measurement 하나를 선택해 `Reject`를 누른다.
5. `CONFIRMED` Measurement reject가 차단되는지 확인한다.
6. 같은 `room_no`, `category`, `finish_code`, `measurement_type`, `unit`인 두 후보를 골라 target/source로 병합한다.
7. 다른 room 또는 다른 code 후보 병합이 실패하는지 확인한다.

### 기대 결과

- 방별 산출 진행 상태가 표시된다.
- Measurement reject는 물리 삭제가 아니라 `REJECTED` 상태 변경이다.
- `CONFIRMED` row는 reject와 merge에서 보호된다.
- 병합 target은 quantity, formula, source sheet, memo 추적성을 유지한다.
- 병합 source는 `REJECTED` 상태로 남는다.

### 체크

- [ ] Room Status 패널 표시
- [ ] Measurement 필터 가능
- [ ] Measurement reject 시 물리 삭제 없음
- [ ] CONFIRMED reject 차단
- [ ] 동일 조건 Measurement 병합 가능
- [ ] 다른 조건 Measurement 병합 차단
- [ ] 병합 source가 REJECTED로 남음

## 10. 직접 치수 입력으로 면적 계산

### 절차

1. Measurement 목록에서 바닥 또는 천장 후보를 선택한다.
2. Calculation Type을 `사각형 면적`으로 둔다.
3. 아래 값을 입력한다.

```text
width: 4.2
height: 2.7
```

4. 미리보기를 확인한다.
5. `계산 저장`을 누른다.

### 기대 결과

```text
계산식: 4.2 * 2.7
수량: 11.34
단위: m2
```

### 체크

- [ ] Measurement 선택 가능
- [ ] 면적 입력 필드 표시
- [ ] 미리보기 수량 11.34 확인
- [ ] 저장 후 formula 저장
- [ ] 저장 후 quantity 저장
- [ ] 저장 후 unit 저장

## 11. 직접 치수 입력으로 둘레 계산 및 공제값 입력

### 절차

1. Base 또는 둘레 후보를 선택한다.
2. Calculation Type을 `사각형 둘레`로 선택한다.
3. 아래 값을 입력한다.

```text
width: 4.2
height: 2.7
deduction amount: 0.8
deduction label: opening
```

4. 미리보기를 확인한다.
5. `계산 저장`을 누른다.

### 기대 결과

```text
계산식: (4.2 + 2.7) * 2 - 0.8
수량: 13.00
단위: m
```

### 체크

- [ ] 둘레 입력 필드 표시
- [ ] 공제 입력 가능
- [ ] 미리보기 수량 13.00 확인
- [ ] 저장 후 공제가 반영된 formula 저장

## 12. 직접 치수 입력으로 벽체면적 계산 및 공제값 입력

### 절차

1. Wall 후보를 선택한다.
2. Calculation Type을 `벽체 면적`으로 선택한다.
3. 아래 값을 입력한다.

```text
length: 4.2
height: 4.6
deduction amount: 1.89
deduction formula: 0.9 * 2.1
deduction label: door
```

4. 미리보기를 확인한다.
5. `계산 저장`을 누른다.

### 기대 결과

```text
계산식: 4.2 * 4.6 - 0.9 * 2.1
수량: 17.43
단위: m2
```

### 체크

- [ ] 벽체 길이/높이 입력 가능
- [ ] 문/창문 공제값 입력 가능
- [ ] 미리보기 수량 17.43 확인
- [ ] 저장 후 formula/quantity/unit 확인

## 13. 파티션 양면 계산 확인

### 절차

1. 파티션 또는 GWB 관련 후보를 선택한다.
2. Calculation Type을 `파티션 면적`으로 선택한다.
3. 아래 값을 입력한다.

```text
length: 4.2
height: 4.6
side_count: 2
```

4. 미리보기를 확인한다.
5. `계산 저장`을 누른다.

### 기대 결과

```text
계산식: 4.2 * 4.6 * 2
수량: 38.64
단위: m2
```

### 체크

- [ ] side_count 입력 가능
- [ ] 양면 계산 가능
- [ ] 미리보기 수량 38.64 확인
- [ ] 저장 후 formula/quantity/unit 확인

## 14. Count click 측정

### 절차

1. `Drawing Detail` 화면에서 평면도 페이지를 연다.
2. Measurement 후보 목록에 `COUNT` 타입 후보가 있는지 확인한다.
3. 측정 모드를 `개수 클릭`으로 선택한다.
4. 도면 위 대상 위치를 여러 번 클릭한다.
5. 결과 수량이 클릭 수와 같은지 확인한다.
6. `Measurement에 저장`을 누른다.

### 기대 결과

- 클릭 개수가 quantity로 저장된다.
- unit은 `EA`로 저장된다.
- formula는 클릭 개수를 읽을 수 있는 형태로 저장된다.
- `coordinates_json`에 drawing file, page index, image size, view transform, clicked points, result가 남는다.
- `COUNT`가 아닌 Measurement에는 count click 결과를 저장할 수 없다.

### 체크

- [ ] Count click 모드 표시
- [ ] 클릭 수량 표시
- [ ] COUNT Measurement에 저장 가능
- [ ] unit `EA` 저장
- [ ] coordinates_json에 클릭 좌표 저장
- [ ] COUNT가 아닌 후보 저장 차단

## 15. 계산 결과 CONFIRMED 처리

### 절차

1. 계산 입력 패널에서 값을 검토한다.
2. `저장 후 CONFIRMED로 확정`을 체크한다.
3. `계산 저장`을 누른다.
4. 목록에서 상태를 확인한다.

### 기대 결과

- 사용자가 검토하고 체크한 Measurement만 `CONFIRMED`가 된다.
- 검수하지 않은 후보는 `DRAFT` 또는 `NEEDS_REVIEW` 상태로 남는다.

### 체크

- [ ] CONFIRMED 체크 가능
- [ ] 저장 후 상태가 CONFIRMED로 변경
- [ ] 다른 미검수 후보는 CONFIRMED가 아님

## 16. Excel Summary/Details/Review 다운로드

### 절차

1. `Measurement` 화면에서 `Excel 다운로드`를 누른다.
2. 다운로드된 `.xlsx` 파일을 연다.
3. `Summary` 시트를 확인한다.
4. `Details` 시트를 확인한다.
5. `Review` 시트를 확인한다.

### Summary 기대 결과

- 마감 코드별 합계가 표시된다.
- 같은 `Category`, `Code`, `Unit`은 합산된다.
- 아래 열이 있다.

```text
Category
Code
Unit
Total Quantity
Source Sheets
```

### Details 기대 결과

- Room별 상세 계산 근거가 남는다.
- 아래 열이 있다.

```text
Drawing No
Room No
Room Name
Category
Code
Formula
Quantity
Unit
Source Sheets
Status
Memo
```

### Review 기대 결과

- `REJECTED` Measurement는 포함되지 않는다.
- 아래 열이 있다.

```text
Drawing No
Room No
Room Name
Category
Code
Formula
Quantity
Unit
Status
Memo
```

### 체크

- [ ] Excel 다운로드 성공
- [ ] Summary 시트 존재
- [ ] Details 시트 존재
- [ ] Review 시트 존재
- [ ] Summary가 Category/Code/Unit 기준으로 합산
- [ ] Details에 Room No가 남음
- [ ] Details에 Formula가 남음
- [ ] Details에 Quantity가 소수점 둘째 자리로 표시
- [ ] Details에 Source Sheets가 남음
- [ ] CONFIRMED 상태가 Details에 남음
- [ ] Review에 REJECTED row가 없음
- [ ] Review에 Formula/Quantity/Status/Memo가 남음

## 최종 판정 기준

통과로 볼 수 있는 기준:

- 샘플 PDF 업로드부터 Excel 다운로드까지 중단 없이 진행된다.
- 마감표 후보가 완벽하지 않아도 사용자가 수정할 수 있다.
- Measurement 후보를 Room별로 만들 수 있다.
- 사용자가 직접 숫자를 입력해 면적, 둘레, 벽체면적을 계산할 수 있다.
- 공제값이 formula와 quantity에 반영된다.
- 사용자가 검토한 항목만 `CONFIRMED`로 바꿀 수 있다.
- Excel Summary에서 마감 코드별 합계를 볼 수 있다.
- Excel Details에서 Room별 계산식과 도면 출처를 추적할 수 있다.
- Excel Review에서 검수 대상 row만 확인할 수 있다.

실패로 봐야 하는 기준:

- PDF 업로드가 되지 않는다.
- 도면 이미지 또는 텍스트 처리가 전혀 되지 않는다.
- 마감표를 도면 번호 하드코딩에 의존해서만 찾는다.
- RoomFinish를 사용자가 수정할 수 없다.
- Measurement 후보가 생성되지 않는다.
- 계산 결과에 formula, quantity, unit, source_sheets 중 하나가 저장되지 않는다.
- Excel에 Summary 또는 Details 시트가 없다.
- Excel에 Review 시트가 없다.
- Excel Review에 `REJECTED` row가 포함된다.
- `CONFIRMED` row가 reject 또는 merge로 자동 변경된다.
- reject 동작이 DB row를 물리 삭제한다.
- Excel Details에서 계산식이나 도면 출처를 확인할 수 없다.

## 17. 3차 준비: 도면 위 치수 선택 보조

3차 구현 후 이 섹션을 실제 UI 기준으로 확장한다. 현재 기준 목표 흐름은 `docs/DIMENSION_ASSIST_MVP_SPEC.md`를 따른다.

### 예정 절차

1. Room No 또는 Room Name으로 관련 도면/page 후보를 검색한다.
2. 후보를 선택해 도면 상세 화면으로 이동한다.
3. 치수 후보 탐색 영역을 도면 위에서 선택한다.
4. 표시된 치수 후보의 raw text, normalized value, unit guess, source sheet를 확인한다.
5. 후보를 width/height/length/wall_height 입력에 반영한다.
6. 계산 저장 후 `coordinates_json`에 region과 후보 근거가 남았는지 확인한다.

### 예정 실패 기준

- Room No 검색 결과가 조용히 빈 성공으로만 끝난다.
- 후보가 없는 경우 warning 또는 직접 입력 fallback이 없다.
- 후보 선택만으로 Measurement가 자동 `CONFIRMED`된다.
- 선택 영역이나 후보 raw text가 저장 근거에 남지 않는다.
- 기존 scale/line/rectangle/polygon/count click 측정이 깨진다.
