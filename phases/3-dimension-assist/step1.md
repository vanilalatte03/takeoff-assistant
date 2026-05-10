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

- Backend에 `GET /drawing-files/{drawing_file_id}/room-page-candidates?room_query=...` endpoint를 추가한다.
- response shape는 `RoomPageCandidateResponse`이며, candidate는 `page_index`, `sheet_no`, `sheet_title`, `sheet_role`, `room_no`, `room_name`, `evidence`, `confidence`를 포함한다.
- 후보는 `DrawingSheet.text_content`의 Room No/Room Name 매칭을 1순위로 만들고, `RoomFinish.source_sheet_no`와 `Measurement.source_sheets`는 보조 evidence로 사용한다.
- 후보 정렬은 plan 계열 sheet role(`FLOOR_PLAN`, `ENLARGED_FLOOR_PLAN`, `CEILING_PLAN`, `PARTITION_PLAN`) 우선, confidence 내림차순, page index 오름차순으로 한다.
- Frontend에서 Room No 검색 결과로 관련 sheet/page 후보를 표시한다.
- 사용자가 후보를 선택하면 `/drawings/{drawingFileId}/pages/{pageIndex}`로 이동할 수 있게 한다.
- source sheet가 page와 매칭되지 않거나 후보가 없으면 빈 성공처럼 처리하지 말고 response warning과 UI fallback 메시지를 표시한다.
- Frontend type과 API client에 `RoomPageCandidate`, `RoomPageCandidateResponse`, `findRoomPageCandidates(...)`를 추가한다.

## 인수 기준

```powershell
.\apps\api\.venv311\Scripts\python.exe scripts\checks.py --stage manual
```

## 검증 절차

1. Room No로 관련 후보가 표시되는지 확인한다.
2. 후보 선택 시 도면 상세 화면으로 이동하는지 확인한다.
3. Room Name 검색과 후보 없음 warning 경로를 확인한다.
4. 기존 Measurement/RoomFinish 목록 기능이 깨지지 않았는지 확인한다.
5. `phases/3-dimension-assist/index.json`의 해당 단계를 업데이트한다.

## 금지사항

- sheet number를 하드코딩하지 마라.
- 후보가 없을 때 조용히 빈 성공처럼 처리하지 마라.
