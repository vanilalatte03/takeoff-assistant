# QA_SMOKE_TEST.md

F01~F07 수정 후 재계산·페이지 전환·병합·확정 취소를 확인할 때는 `docs/INTEGRITY_FIXES.md`의 회귀 검증을 함께 수행합니다. 예전 DB에 소속이 불명확한 수동 행이 있으면 파일별 목록에서 제외될 수 있으며, 임의로 도면에 배정하지 않습니다.

화면의 현재 한글 라벨, 자동 조회와 접기 영역은 [도면·산출 검수 화면](REVIEW_WORKSPACE.md)을 참고한다. 아래 데이터/API 필드명과 Excel 열 이름은 그대로 유지한다.

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

1. **실별 마감표** 화면으로 이동한다.
2. 프로젝트와 도면 PDF를 이름으로 선택해 기존 내역이 자동 조회되는지 확인한다.
3. **마감표 후보 추출**을 누른다.
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
5. 불필요한 미확정 RoomFinish를 하나 골라 `거절`을 누른다.
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

1. **산출 내역** 화면으로 이동한다.
2. 프로젝트와 도면 PDF를 이름으로 선택해 기존 내역이 자동 조회되는지 확인한다.
3. **산출 후보 생성**을 누른다.
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

1. **산출 내역** 화면에서 프로젝트와 PDF를 선택하고 자동 조회된 목록을 확인한다.
2. **실별 검수 현황**을 열어 방별 전체·수량 있음·확정·검토 필요·수량 누락을 확인한다.
3. **실 번호**, **검수 상태**와 **상세 필터** 안의 **분류**, **마감 코드**, **산출 종류**를 각각 적용한다.
4. 미확정 산출의 **검토**를 누르고 오른쪽 패널의 **산출 거절**을 누른다.
5. `CONFIRMED` Measurement reject가 차단되는지 확인한다.
6. 같은 `room_no`, `category`, `finish_code`, `measurement_type`, `unit`인 후보의 **병합** 원본 체크박스를 선택한다. 나타난 **병합 대상**을 확인하고 **선택한 산출 병합**을 누른다.
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
2. **계산 방식**을 `사각형 면적`으로 둔다.
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
2. **계산 방식**을 `사각형 둘레`로 선택한다.
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
2. **계산 방식**을 `벽체 면적`으로 선택한다.
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
2. **계산 방식**을 `파티션 면적`으로 선택한다.
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

1. **도면 측정** 화면에서 평면도 페이지를 연다.
2. Measurement 후보 목록에 `COUNT` 타입 후보가 있는지 확인한다.
3. 측정 모드를 `개수 클릭`으로 선택한다.
4. 도면 위 대상 위치를 여러 번 클릭한다.
5. 결과 수량이 클릭 수와 같은지 확인한다.
6. `산출에 저장`을 누른다.

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

1. **산출 내역** 화면에서 **Excel 내보내기**를 누른다.
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

### 구현 후 확인 절차

- 도면 목록의 Room page candidates에서 실 번호·이름으로 검색하고 관련 도면을 연다.
- **도면 측정**에서 **치수 영역 선택**으로 두 모서리를 지정하고 원문·정규화값·출처·경고와 후보가 없을 때의 안내를 확인한다.
- 후보를 Width, Height, Length, Wall height, Side count에 배정한 뒤 **계산 근거 저장**을 누른다.
- **산출 내역**에서 PDF를 선택하고 자동 조회된 해당 행의 **검토**를 누른다. 계산 입력이 `coordinates_json.dimension_assist.selected_candidates`에서 채워지는지 확인한다.
- 확정 체크박스를 명시적으로 선택하지 않았다면 계산 저장 후에도 `CONFIRMED`가 아니어야 한다.

## 검수 작업 화면 smoke

1. PDF 선택만으로 마감표와 산출 내역이 조회되며 후보 생성·저장 API가 실행되지 않는지 확인한다.
2. 다른 PDF로 전환하면 이전 결과가 사라지고 늦게 도착한 이전 응답이 표시되지 않는지 확인한다. 조회 실패 후 **다시 불러오기**, 빈 내역, 필터 결과 없음을 각각 구분한다.
3. **산출 목록**이 계산 패널보다 먼저 나오고, 다른 행의 **검토**를 누르면 선택 번호와 패널 내용이 바뀌며 패널 스크롤이 처음으로 돌아가는지 확인한다.
4. 기본 접기 영역인 **실별 검수 현황**, **상세 필터**, **실별 마감 추가**, **실사용 비교 기록**을 열어 기존 기능을 사용할 수 있는지 확인한다.
5. 도면 측정의 **PDF 쪽 번호**에 `1`을 입력하면 URL의 `/pages/0`과 첫 PDF 페이지가 열리는지 확인한다.
6. 데스크톱의 목록·검토 패널 나란히 배치와 1100px 이하의 세로 배치를 확인한다. 좁은 화면의 가로 스크롤은 표 내부로 제한되어야 한다.
7. 확정·거절 행의 병합 원본 선택·거절·편집 보호와 명시적인 **재검토 시작**을 확인한다.

## AI 보조 PRD 후속 smoke

1. 산출 탐색 보조에서 이름으로 프로젝트/PDF를 선택하고 실 번호·마감 코드로 검색한다.
2. 근거 페이지와 원문을 확인하고 산출 행을 선택한다. 치수마다 출처 페이지를 먼저 선택한 뒤 후보 또는 수동값·단위·메모를 입력한다.
3. 파티션은 면 수를 입력하고 공제를 확인한다. 저장 결과가 DRAFT이며 식·수량·단위·출처가 Excel에 남는지 확인한다.
4. 사용자가 CONFIRMED로 바꾼 행의 초안 재저장을 시도해 차단을 확인한다.
5. 텍스트 추출이 부족한 영역은 도면 측정의 **치수 영역 선택**에서 선택한다. 로컬 PNG 미리보기와 권한을 확인한 뒤 선택 영역만 판독한다. 키가 없으면 실제 모델 검증 미실시로 기록한다.
6. 원본이 바뀌거나 영역이 미리보기와 다르면 재확인을 요구해야 한다. 판독 후보는 미확정이며 숫자·단위·코드를 원본과 대조한다.
7. 산출 탐색 보조의 **실사용 비교 기록**을 열고 같은 과제명으로 수동/보조 작업의 전체 시간·수정·개입·오류·검수 결과를 저장한다. API 도구 테스트 시간을 실무 작업시간으로 기재하지 않는다.
8. 초안 저장 후 또는 산출 수정 폼에서 원본 대조 패널을 연다. 4200mm 입력이 실제 저장된 4.2m 변환값으로 표시되는지 확인하고 출처 버튼으로 해당 PDF 페이지를 나란히 본다. 기록 없는 과거 행에는 변환값을 만들어 표시하지 않아야 한다.
9. 계산 결과를 수동 수정하거나 원본이 바뀐 경우 이전 입력 기록과 현재 결과/원본의 차이를 경고해야 한다. 대조 화면을 열기만 해서는 산출값·검수 상태가 바뀌지 않아야 한다.

2026-11-05 개발자 확인: 합성 PDF와 실제 private PDF 130페이지의 예제 두 건을 로컬에서 재현했다. 실제 모델은 합성 자료의 9항목 평가를 통과했고 원본 대조 패널도 브라우저에서 확인했다. 실무자 정답 승인·현장 시간 비교는 미실시다. 자세한 범위는 `AI_ASSIST_PROGRESS.md`와 `AI_ASSIST_EVALUATION.md`를 참조한다.

## 파일럿 기록 준비 smoke (6차 step6)

격리 테스트 DB/합성 PDF에서만 확인한다. 빈 기록의 JSON 분석이 NOT_RUN/0건인지 확인하고, 선택 상세에서 관찰자·참여자·조건·실제 순서를 입력한다. 연습/실패/미검수도 각각 기록해 JSON에 전부 남는지 본다. 같은 묶음 재시도·다른 버전·조건 불일치는 시간 비교에서 제외되어야 한다. 세 방식 검수·채택 완료 묶음만 초/수정/개입/오류 비교가 생기며 정확도 지표는 생성하지 않는다. 전체 절차와 빈 양식은 [FIELD_PILOT](FIELD_PILOT.md)을 따른다. 실제 업무 DB에 합성 시간을 입력하지 않는다.
