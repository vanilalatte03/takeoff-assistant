# 단계 4: calculation-integration

## 읽어야 할 파일

- `/docs/DIMENSION_ASSIST_MVP_SPEC.md`
- `/apps/web/src/components/MeasurementCalculationForm.tsx`
- `/apps/web/src/components/ManualMeasurementViewer.tsx`
- `/apps/api/app/api/routes/measurements.py`
- `/apps/api/app/services/calculation_engine.py`
- `/apps/api/tests/test_measurement_calculation_api.py`
- `/apps/api/tests/test_measurement_update_api.py`

## 작업

선택한 치수 후보를 계산 입력과 Measurement 저장 근거로 연결하라.

- 사용자가 후보를 `width`, `height`, `wall_length`, `wall_height`, `side_multiplier` 입력 슬롯에 매핑할 수 있게 한다.
- 후보 선택은 계산 입력값을 채우되 자동 저장/자동 확정하지 않는다.
- `MeasurementCalculationForm`은 후보 prefill을 받을 수 있어야 하며, prefill된 값은 사용자가 수정할 수 있어야 한다.
- 저장 시 selected dimension candidates와 region metadata가 `Measurement.coordinates_json.dimension_assist`에 남도록 한다.
- source_sheets는 선택한 sheet no를 유지한다.
- 후보 기반 계산 후에도 사용자가 formula, quantity, status를 수정할 수 있어야 한다.
- 새 DB 컬럼은 추가하지 않는다. `coordinates_json`은 구조화된 근거 저장소로 쓰고 `memo`는 사람용 요약만 저장한다.
- `CONFIRMED` 전환은 기존 `저장 후 CONFIRMED로 확정` 체크박스가 선택된 경우에만 수행한다.

## 인수 기준

```powershell
.\apps\api\.venv311\Scripts\python.exe scripts\checks.py --stage manual
```

## 검증 절차

1. 후보를 선택해 계산 input에 반영되는지 확인한다.
2. 저장 payload에 후보/region 근거가 남는지 확인한다.
3. `CONFIRMED`는 사용자가 명시 선택한 경우에만 적용되는지 확인한다.
4. 후보 prefill 후 사용자가 값을 수정해도 계산/저장이 정상 동작하는지 확인한다.
5. `phases/3-dimension-assist/index.json`의 해당 단계를 업데이트한다.

## 금지사항

- 후보 선택만으로 계산을 확정하지 마라.
- 기존 직접 입력 계산 흐름을 제거하지 마라.
