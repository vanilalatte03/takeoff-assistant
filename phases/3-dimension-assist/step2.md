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

- request는 최소 drawing_file_id, page_index, optional region coordinates를 받는다.
- response는 raw text, normalized value, unit guess, source sheet, confidence/status, warning을 포함한다.
- PDF text block 좌표를 사용할 수 있으면 region 주변 후보를 우선 반환한다.
- 좌표가 없으면 DrawingSheet.text_content에서 치수형 숫자 후보를 추출한다.
- `4200`, `4.2`, `2.7`, `2700`, `9'-0"` 같은 일반 치수 패턴을 테스트한다.
- 후보 추출 실패는 warning으로 드러내고 직접 입력 fallback을 가능하게 한다.

## 인수 기준

```powershell
.\apps\api\.venv311\Scripts\python.exe scripts\checks.py --stage manual
```

## 검증 절차

1. API unit/API test를 추가한다.
2. 후보 정규화와 warning 경로를 테스트한다.
3. 기존 sheet search/page processing 테스트가 통과하는지 확인한다.
4. `phases/3-dimension-assist/index.json`의 해당 단계를 업데이트한다.

## 금지사항

- OCR pipeline을 새로 추가하지 마라.
- 후보 confidence를 확정값처럼 취급하지 마라.
