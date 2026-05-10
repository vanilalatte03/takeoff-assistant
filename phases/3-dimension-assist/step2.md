# 단계 2: dimension-candidate-api

## 읽어야 할 파일

- `/docs/DIMENSION_ASSIST_MVP_SPEC.md`
- `/apps/api/app/models/drawing.py`
- `/apps/api/app/schemas/drawing.py`
- `/apps/api/app/api/routes/drawing_files.py`
- `/apps/api/app/services/sheet_search.py`
- `/apps/api/tests/test_sheet_search.py`

## 작업

도면 page 또는 선택 영역 기준 치수 텍스트 후보 API를 구현하라.

- Backend에 `POST /drawing-files/{drawing_file_id}/pages/{page_index}/dimension-candidates` endpoint를 추가한다.
- request shape는 `DimensionCandidateRequest`이며 optional `region: DimensionRegion | None`을 받는다.
- response shape는 `DimensionCandidateResponse`이며 candidate는 `raw_text`, `normalized_value`, `normalized_unit`, `unit_guess`, `source_sheet`, `page_index`, `bbox`, `confidence`, `status`, `warning`을 포함한다.
- `DimensionRegion`은 rendered image pixel 좌표 기준 `x`, `y`, `width`, `height`, optional `image_width`, `image_height`, `zoom`, `pan_x`, `pan_y`를 가진다.
- stored PDF를 열어 `page.get_text("blocks")`를 우선 사용하고, block bbox를 rendered image 좌표계로 변환해 region과 겹치거나 가까운 후보를 먼저 반환한다.
- PDF text block을 사용할 수 없거나 bbox 후보가 없으면 DrawingSheet.text_content에서 sheet-level 치수형 숫자 후보를 추출한다.
- `4200`, `2700`은 mm로 보고 m로 정규화하고, `4.2`, `2.7`은 m로 보고, `9'-0"`는 feet-inch에서 m로 변환한다.
- 일반 치수 패턴과 warning 경로를 테스트한다.
- 후보 추출 실패는 warning으로 드러내고 직접 입력 fallback을 가능하게 한다.
- Frontend type과 API client에 `DimensionRegion`, `DimensionCandidate`, `DimensionCandidateRequest`, `DimensionCandidateResponse`, `getDimensionCandidates(...)`를 추가한다.

## 인수 기준

```powershell
.\apps\api\.venv311\Scripts\python.exe scripts\checks.py --stage manual
```

## 검증 절차

1. API unit/API test를 추가한다.
2. mm/m/feet-inch 후보 정규화와 warning 경로를 테스트한다.
3. region bbox 후보와 sheet text fallback 후보를 테스트한다.
4. 기존 sheet search/page processing 테스트가 통과하는지 확인한다.
5. `phases/3-dimension-assist/index.json`의 해당 단계를 업데이트한다.

## 금지사항

- OCR pipeline을 새로 추가하지 마라.
- 후보 confidence를 확정값처럼 취급하지 마라.
