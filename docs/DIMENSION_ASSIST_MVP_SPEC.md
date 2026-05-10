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
- Backend는 `GET /drawing-files/{drawing_file_id}/room-page-candidates?room_query=...`를 제공합니다.
- 검색 기준은 `DrawingSheet.text_content`의 Room No/Room Name 매칭을 1순위로 두고, `RoomFinish.source_sheet_no`와 `Measurement.source_sheets`는 보조 evidence로 사용합니다.
- 후보 정렬은 plan 계열 sheet role(`FLOOR_PLAN`, `ENLARGED_FLOOR_PLAN`, `CEILING_PLAN`, `PARTITION_PLAN`)을 먼저 보여주고, 그 다음 text match confidence와 page index 순서를 따릅니다.
- 후보가 없으면 HTTP 성공 응답에 빈 `candidates`와 warning을 함께 반환해 사용자가 sheet 검색 또는 직접 page 이동 fallback으로 이어갈 수 있게 합니다.

### 2. 영역 선택

- `ManualMeasurementViewer`에 `DIMENSION_REGION` 또는 동등한 영역 선택 모드를 추가합니다.
- 사용자는 도면 위에서 사각형 영역을 드래그하거나 두 점으로 영역을 지정합니다.
- 선택 영역은 image 좌표, page index, zoom/pan metadata와 함께 저장 가능한 JSON 형태로 유지합니다.
- MVP의 `DIMENSION_REGION` 입력 방식은 두 점 사각형 선택입니다. 첫 번째 점은 시작점, 두 번째 점은 반대편 꼭짓점입니다.
- region 좌표는 rendered image pixel 좌표 기준 `x`, `y`, `width`, `height`로 유지합니다.

### 3. 치수 텍스트 후보 추출

- Backend는 DrawingSheet의 `text_content`와 가능한 경우 PDF text block 좌표를 기반으로 영역 주변 숫자 후보를 반환합니다.
- MVP에서는 완벽한 좌표 정합을 요구하지 않습니다. 좌표가 없으면 sheet text에서 `4200`, `4.2`, `2.7`, `2700`, `9'-0"` 같은 치수형 숫자 후보를 추출해 표시합니다.
- 후보에는 raw text, normalized numeric value, unit guess, source sheet, confidence/status를 포함합니다.
- 후보는 기본적으로 `NEEDS_REVIEW` 또는 선택 대기 상태로 취급합니다.
- Backend는 `POST /drawing-files/{drawing_file_id}/pages/{page_index}/dimension-candidates`를 제공합니다.
- 가능하면 stored PDF를 열어 `page.get_text("blocks")`를 on-demand로 읽고, block bbox를 rendered image 좌표계에 맞춰 변환한 뒤 region과 겹치거나 가까운 후보를 우선 반환합니다.
- PDF text block을 읽지 못하거나 bbox 기반 후보가 없으면 `DrawingSheet.text_content`에서 sheet-level 후보를 추출합니다.
- 정규화 규칙은 다음을 따릅니다.
  - `4200`, `2700`처럼 단위 없는 100 이상 숫자는 mm로 보고 m 값(`4.2`, `2.7`)으로 정규화합니다.
  - `4.2`, `2.7`처럼 소수 숫자는 m로 봅니다.
  - `9'-0"` 같은 feet-inch 값은 m로 변환합니다.
  - 정규화가 불확실한 후보는 버리지 않고 `status: "NEEDS_REVIEW"`와 warning을 붙입니다.

### 4. 치수 후보 선택과 계산 연결

- 사용자는 후보를 `width`, `height/depth`, `length`, `wall_height`, `side_multiplier` 중 필요한 입력에 매핑할 수 있습니다.
- 선택된 후보는 Calculation form의 입력값을 채우거나 Measurement update payload에 근거로 남깁니다.
- 계산 저장 전까지 Measurement를 `CONFIRMED`로 만들지 않습니다.
- 계산 API payload 명칭은 기존 `MeasurementCalculationInput`에 맞춰 `width`, `height`, `wall_length`, `wall_height`, `side_multiplier`를 사용합니다.
- 후보 선택값은 `MeasurementCalculationForm`의 입력값을 prefill하지만, 저장 버튼을 누르기 전에는 Measurement를 변경하지 않습니다.
- 기존 `저장 후 CONFIRMED로 확정` 체크박스만 `CONFIRMED` 전환 경로입니다. 후보 선택, 후보 API 호출, prefill만으로는 확정하지 않습니다.

### 5. 추적성

- 선택 영역, 후보 raw text, 선택한 후보, 계산 반영 방식은 `coordinates_json`에 구조화해 남깁니다.
- source_sheets는 선택한 도면 sheet no를 유지합니다.
- 실패하거나 후보가 없는 경우 사용자가 직접 입력으로 이어갈 수 있게 warning을 표시합니다.
- 새 DB 컬럼은 추가하지 않습니다.
- `coordinates_json`은 구조화된 근거 저장소로 사용하고, `memo`는 사람이 읽는 짧은 요약만 저장합니다.
- dimension assist 근거는 `Measurement.coordinates_json.dimension_assist` 아래에 저장합니다.

```json
{
  "dimension_assist": {
    "region": {
      "drawing_file_id": 1,
      "page_index": 3,
      "source_sheet_no": "A101",
      "image": {
        "natural_width": 1800,
        "natural_height": 1200
      },
      "view_transform": {
        "zoom": 1.25,
        "pan": { "x": 16, "y": 16 }
      },
      "rect": { "x": 120, "y": 240, "width": 360, "height": 180 }
    },
    "selected_candidates": [
      {
        "slot": "width",
        "raw_text": "4200",
        "normalized_value": 4.2,
        "normalized_unit": "m",
        "source_sheet": "A101",
        "page_index": 3,
        "bbox": { "x": 130, "y": 250, "width": 48, "height": 14 },
        "confidence": 0.72,
        "status": "NEEDS_REVIEW"
      }
    ]
  }
}
```

## API contract

### Room page candidates

`GET /drawing-files/{drawing_file_id}/room-page-candidates?room_query=119`

Backend Pydantic schemas:

```python
class RoomPageCandidate(BaseModel):
    page_index: int
    sheet_no: str | None = None
    sheet_title: str | None = None
    sheet_role: DrawingSheetRole
    room_no: str | None = None
    room_name: str | None = None
    evidence: list[str] = Field(default_factory=list)
    confidence: float

class RoomPageCandidateResponse(BaseModel):
    drawing_file_id: int
    room_query: str
    candidates: list[RoomPageCandidate]
    warnings: list[str] = Field(default_factory=list)
```

Frontend types/client:

- `RoomPageCandidate`
- `RoomPageCandidateResponse`
- `findRoomPageCandidates(drawingFileId, roomQuery)`

### Dimension candidates

`POST /drawing-files/{drawing_file_id}/pages/{page_index}/dimension-candidates`

Backend Pydantic schemas:

```python
class DimensionRegion(BaseModel):
    x: float
    y: float
    width: float
    height: float
    image_width: float | None = None
    image_height: float | None = None
    zoom: float | None = None
    pan_x: float | None = None
    pan_y: float | None = None

class DimensionCandidateRequest(BaseModel):
    region: DimensionRegion | None = None

class DimensionCandidate(BaseModel):
    raw_text: str
    normalized_value: Decimal | None = None
    normalized_unit: str | None = None
    unit_guess: str | None = None
    source_sheet: str | None = None
    page_index: int
    bbox: dict[str, float] | None = None
    confidence: float
    status: ReviewStatus = ReviewStatus.NEEDS_REVIEW
    warning: str | None = None

class DimensionCandidateResponse(BaseModel):
    drawing_file_id: int
    page_index: int
    candidates: list[DimensionCandidate]
    warnings: list[str] = Field(default_factory=list)
```

Frontend types/client:

- `DimensionRegion`
- `DimensionCandidate`
- `DimensionCandidateRequest`
- `DimensionCandidateResponse`
- `getDimensionCandidates(drawingFileId, pageIndex, payload)`

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
