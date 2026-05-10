# 단계 5: smoke-test-docs

## 읽어야 할 파일

- `/docs/DIMENSION_ASSIST_MVP_SPEC.md`
- `/docs/ACCEPTANCE_CHECKLIST.md`
- `/docs/QA_SMOKE_TEST.md`
- `/docs/SAMPLE_DATA_GUIDE.md`
- `/docs/COMMANDS.md`

## 작업

3차 도면 위 치수 선택 보조 수동 검증 절차를 문서화하라.

- Room No 검색에서 도면 상세 이동까지 절차를 추가한다.
- 영역 선택, 후보 표시, 후보 선택, 계산 입력 반영, 저장 근거 확인 절차를 추가한다.
- 후보 없음/warning/direct input fallback 실패 기준을 명시한다.
- 기존 1차/2차 smoke 절차와 충돌하지 않게 별도 3차 섹션으로 정리한다.
- 기밀 샘플 PDF를 커밋하도록 지시하지 않는다.

## 인수 기준

```powershell
.\apps\api\.venv311\Scripts\python.exe scripts\checks.py --stage manual
```

## 검증 절차

1. smoke 문서가 실제 UI/API 흐름과 맞는지 확인한다.
2. acceptance checklist의 3차 항목과 대응되는지 확인한다.
3. `phases/3-dimension-assist/index.json`의 해당 단계를 업데이트한다.

## 금지사항

- 수동 검증 실패 기준을 완화하지 마라.
- AI API 사용을 요구하지 마라.
