# 단계 1: room-navigation

## 읽어야 할 파일

- `/docs/DIMENSION_ASSIST_MVP_SPEC.md`
- `/apps/api/app/api/routes/room_finishes.py`
- `/apps/api/app/api/routes/measurements.py`
- `/apps/web/src/pages/RoomFinishesPage.tsx`
- `/apps/web/src/pages/MeasurementsPage.tsx`
- `/apps/web/src/pages/DrawingDetailPage.tsx`
- `/apps/web/src/api/client.ts`
- `/apps/web/src/types/api.ts`

## 작업

Room No 또는 Room Name에서 관련 도면 페이지로 이동하는 흐름을 구현하라.

- Backend에 필요하면 room/drawing 후보 조회 endpoint를 추가한다.
- 후보는 RoomFinish, Measurement, DrawingSheet source_sheet_no/source_sheets를 연결해 만든다.
- Frontend에서 Room No 검색 결과로 관련 sheet/page 후보를 표시한다.
- 사용자가 후보를 선택하면 `/drawings/{drawingFileId}/pages/{pageIndex}`로 이동할 수 있게 한다.
- source sheet가 page와 매칭되지 않으면 명확한 fallback 메시지를 표시한다.

## 인수 기준

```powershell
.\apps\api\.venv311\Scripts\python.exe scripts\checks.py --stage manual
```

## 검증 절차

1. Room No로 관련 후보가 표시되는지 확인한다.
2. 후보 선택 시 도면 상세 화면으로 이동하는지 확인한다.
3. 기존 Measurement/RoomFinish 목록 기능이 깨지지 않았는지 확인한다.
4. `phases/3-dimension-assist/index.json`의 해당 단계를 업데이트한다.

## 금지사항

- sheet number를 하드코딩하지 마라.
- 후보가 없을 때 조용히 빈 성공처럼 처리하지 마라.
