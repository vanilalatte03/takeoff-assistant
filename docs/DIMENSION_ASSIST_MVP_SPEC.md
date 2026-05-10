# DIMENSION_ASSIST_MVP_SPEC.md

## 3차 MVP 범위

이 문서는 PRD의 **3차: 도면 위 치수 선택 보조** 상세 범위를 정의합니다. 3차는 자동 치수선 판독이나 자동 room boundary recognition이 아니라, 사용자가 선택한 방/영역 주변의 텍스트 치수 후보를 빠르게 확인하고 선택해 계산으로 연결하는 반자동 검수 흐름입니다.

## 목표

- 사용자가 Room No 또는 방 이름으로 관련 도면 페이지를 빠르게 찾을 수 있습니다.
- 사용자가 도면 상세 화면에서 방 주변 영역을 드래그해 치수 후보 탐색 범위를 지정할 수 있습니다.
- 시스템은 해당 영역 주변의 숫자/치수 텍스트 후보를 표시하되, 자동 확정하지 않습니다.
- 사용자는 가로/세로/둘레/높이 후보를 직접 선택하고 계산 입력에 반영할 수 있습니다.
- 선택 근거는 `coordinates_json`과 formula/source_sheets에 추적 가능하게 남습니다.

## 포함 범위

### 1. Room 기반 도면 이동

- Room No 또는 Room Name으로 Measurement/RoomFinish 관련 후보를 찾습니다.
- 관련 Drawing Sheet와 page index 후보를 표시합니다.
- 사용자는 후보 중 하나를 선택해 도면 상세 화면으로 이동할 수 있습니다.

### 2. 영역 선택

- `ManualMeasurementViewer`에 `DIMENSION_REGION` 또는 동등한 영역 선택 모드를 추가합니다.
- 사용자는 도면 위에서 사각형 영역을 드래그하거나 두 점으로 영역을 지정합니다.
- 선택 영역은 image 좌표, page index, zoom/pan metadata와 함께 저장 가능한 JSON 형태로 유지합니다.

### 3. 치수 텍스트 후보 추출

- Backend는 DrawingSheet의 `text_content`와 가능한 경우 PDF text block 좌표를 기반으로 영역 주변 숫자 후보를 반환합니다.
- MVP에서는 완벽한 좌표 정합을 요구하지 않습니다. 좌표가 없으면 sheet text에서 `4200`, `4.2`, `2.7`, `2700`, `9'-0"` 같은 치수형 숫자 후보를 추출해 표시합니다.
- 후보에는 raw text, normalized numeric value, unit guess, source sheet, confidence/status를 포함합니다.
- 후보는 기본적으로 `NEEDS_REVIEW` 또는 선택 대기 상태로 취급합니다.

### 4. 치수 후보 선택과 계산 연결

- 사용자는 후보를 `width`, `height/depth`, `length`, `wall_height`, `side_multiplier` 중 필요한 입력에 매핑할 수 있습니다.
- 선택된 후보는 Calculation form의 입력값을 채우거나 Measurement update payload에 근거로 남깁니다.
- 계산 저장 전까지 Measurement를 `CONFIRMED`로 만들지 않습니다.

### 5. 추적성

- 선택 영역, 후보 raw text, 선택한 후보, 계산 반영 방식은 `coordinates_json` 또는 `memo`에 남깁니다.
- source_sheets는 선택한 도면 sheet no를 유지합니다.
- 실패하거나 후보가 없는 경우 사용자가 직접 입력으로 이어갈 수 있게 warning을 표시합니다.

## 제외 범위

- 자동 room boundary recognition
- 자동 dimension-line reading
- CAD 수준의 치수선/화살표 인식
- 스캔 PDF full OCR pipeline
- AI API 기반 후보 판단
- 선택 후보를 사용자 확인 없이 `CONFIRMED` 처리

## 성공 기준

1. 사용자가 Room No로 관련 도면/Measurement 후보를 찾고 도면 상세로 이동할 수 있습니다.
2. 사용자가 도면 위에서 영역을 선택할 수 있습니다.
3. 영역 또는 sheet text 기준 치수 후보가 표시됩니다.
4. 사용자가 치수 후보를 계산 입력값으로 반영할 수 있습니다.
5. 후보가 없거나 불확실하면 warning과 직접 입력 fallback이 표시됩니다.
6. 저장된 Measurement는 formula, quantity, unit, source_sheets, coordinates_json에 선택 근거를 유지합니다.
7. 기존 scale/line/rectangle/polygon/count click 측정 흐름이 깨지지 않습니다.
