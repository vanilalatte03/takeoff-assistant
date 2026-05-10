# 단계 3: region-selection-ui

## 읽어야 할 파일

- `/docs/DIMENSION_ASSIST_MVP_SPEC.md`
- `/apps/web/src/components/ManualMeasurementViewer.tsx`
- `/apps/web/src/pages/DrawingDetailPage.tsx`
- `/apps/web/src/api/client.ts`
- `/apps/web/src/types/api.ts`
- `/apps/web/src/styles.css`

## 작업

도면 상세 viewer에 치수 후보 탐색용 영역 선택 UI를 추가하라.

- 기존 scale/line/rectangle/polygon/count click 모드를 유지한다.
- 영역 선택 모드는 사각형 region을 만들고 candidate API를 호출한다.
- 후보 목록은 viewer side panel 안에서 표시한다.
- 후보가 없으면 warning과 직접 입력 fallback 안내를 표시한다.
- region coordinates, page index, image size, zoom/pan metadata를 state로 유지한다.
- 텍스트가 버튼/패널 밖으로 넘치지 않게 responsive layout을 확인한다.

## 인수 기준

```powershell
.\apps\api\.venv311\Scripts\python.exe scripts\checks.py --stage manual
```

## 검증 절차

1. `npm run build` 또는 공식 check를 실행한다.
2. 영역 선택 모드가 기존 측정 모드를 깨지 않는지 확인한다.
3. 후보 표시/empty/warning 상태를 확인한다.
4. `phases/3-dimension-assist/index.json`의 해당 단계를 업데이트한다.

## 금지사항

- 3D/복잡한 시각 효과를 추가하지 마라.
- 기존 측정 저장 버튼 의미를 바꾸지 마라.
