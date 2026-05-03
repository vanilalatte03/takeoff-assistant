# MANUAL_TEST_SCENARIO.md

## 목적

샘플 PDF를 기준으로 1차 MVP가 실제 마감 물량 산출 보조 도구로 사용할 수 있는지 확인한다.

검증 목표는 완전 자동 적산이 아니다. 아래 흐름이 가능해야 한다.

```text
PDF 업로드 -> 도면 목록/검색 -> 마감표 후보 확인/수정 -> Measurement 후보 생성
-> 직접 치수 입력/계산 -> CONFIRMED 처리 -> Excel Summary/Details 확인
```

## 사전 준비

- 샘플 PDF를 `data/samples/` 아래에 둔다.
- 샘플 PDF, 업로드 파일, Excel 결과물은 공개 저장소에 커밋하지 않는다.
- FastAPI 서버와 React 개발 서버를 실행한다.
- 업로드 화면에서 사용할 `Project ID`가 DB에 존재해야 한다.
  - 현재 MVP에는 Project 생성 화면이 없다.
  - 업로드 시 `Project not found.`가 나오면 테스트용 Project를 먼저 DB에 생성해야 한다.

## 테스트 기록 양식

```text
검증일:
검증자:
샘플 PDF 파일명:
Project ID:
Drawing File ID:
사용한 주요 도면:
  - 평면도:
  - 마감표:
  - 기타:
최종 Excel 파일명:
전체 판정: PASS / FAIL
```

## 1. PDF 업로드

### 절차

1. 앱에서 `PDF 업로드` 화면을 연다.
2. `Project ID`를 입력한다.
3. 샘플 PDF를 선택한다.
4. `PDF 업로드`를 누른다.

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

## 2. 도면 목록 생성

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

## 3. AE101 같은 평면도 검색

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

## 4. AE401 또는 AE402 같은 마감표 검색

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

## 5. FINISH_SCHEDULE에서 RoomFinish 후보 확인

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

## 6. RoomFinish 수정

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

### 기대 결과

- 수정한 값이 저장된다.
- 목록을 다시 조회해도 수정값이 유지된다.

### 체크

- [ ] Room No 수정 가능
- [ ] Room Name 수정 가능
- [ ] Floor/Base/Wall/Ceiling 수정 가능
- [ ] Height 수정 가능
- [ ] 저장 후 수정값 유지

## 7. Measurement 후보 생성

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

## 8. 직접 치수 입력으로 면적 계산

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
Formula: 4.2 * 2.7
Quantity: 11.34
Unit: m2
```

### 체크

- [ ] Measurement 선택 가능
- [ ] 면적 입력 필드 표시
- [ ] 미리보기 수량 11.34 확인
- [ ] 저장 후 formula 저장
- [ ] 저장 후 quantity 저장
- [ ] 저장 후 unit 저장

## 9. 직접 치수 입력으로 둘레 계산 및 공제값 입력

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
Formula: (4.2 + 2.7) * 2 - 0.8
Quantity: 13.00
Unit: m
```

### 체크

- [ ] 둘레 입력 필드 표시
- [ ] 공제 입력 가능
- [ ] 미리보기 수량 13.00 확인
- [ ] 저장 후 공제가 반영된 formula 저장

## 10. 직접 치수 입력으로 벽체면적 계산 및 공제값 입력

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
Formula: 4.2 * 4.6 - 0.9 * 2.1
Quantity: 17.43
Unit: m2
```

### 체크

- [ ] 벽체 길이/높이 입력 가능
- [ ] 문/창문 공제값 입력 가능
- [ ] 미리보기 수량 17.43 확인
- [ ] 저장 후 formula/quantity/unit 확인

## 11. 파티션 양면 계산 확인

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
Formula: 4.2 * 4.6 * 2
Quantity: 38.64
Unit: m2
```

### 체크

- [ ] side_count 입력 가능
- [ ] 양면 계산 가능
- [ ] 미리보기 수량 38.64 확인
- [ ] 저장 후 formula/quantity/unit 확인

## 12. 계산 결과 CONFIRMED 처리

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

## 13. Excel Summary/Details 다운로드

### 절차

1. `Measurement` 화면에서 `Excel 다운로드`를 누른다.
2. 다운로드된 `.xlsx` 파일을 연다.
3. `Summary` 시트를 확인한다.
4. `Details` 시트를 확인한다.

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

### 체크

- [ ] Excel 다운로드 성공
- [ ] Summary 시트 존재
- [ ] Details 시트 존재
- [ ] Summary가 Category/Code/Unit 기준으로 합산
- [ ] Details에 Room No가 남음
- [ ] Details에 Formula가 남음
- [ ] Details에 Quantity가 소수점 둘째 자리로 표시
- [ ] Details에 Source Sheets가 남음
- [ ] CONFIRMED 상태가 Details에 남음

## 최종 판정 기준

PASS로 볼 수 있는 기준:

- 샘플 PDF 업로드부터 Excel 다운로드까지 중단 없이 진행된다.
- 마감표 후보가 완벽하지 않아도 사용자가 수정할 수 있다.
- Measurement 후보를 Room별로 만들 수 있다.
- 사용자가 직접 숫자를 입력해 면적, 둘레, 벽체면적을 계산할 수 있다.
- 공제값이 formula와 quantity에 반영된다.
- 사용자가 검토한 항목만 `CONFIRMED`로 바꿀 수 있다.
- Excel Summary에서 마감 코드별 합계를 볼 수 있다.
- Excel Details에서 Room별 계산식과 도면 출처를 추적할 수 있다.

FAIL로 봐야 하는 기준:

- PDF 업로드가 되지 않는다.
- 도면 이미지 또는 텍스트 처리가 전혀 되지 않는다.
- 마감표를 도면 번호 하드코딩에 의존해서만 찾는다.
- RoomFinish를 사용자가 수정할 수 없다.
- Measurement 후보가 생성되지 않는다.
- 계산 결과에 formula, quantity, unit, source_sheets 중 하나가 저장되지 않는다.
- Excel에 Summary 또는 Details 시트가 없다.
- Excel Details에서 계산식이나 도면 출처를 확인할 수 없다.
