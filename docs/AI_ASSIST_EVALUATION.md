# AI 산출 보조 평가 범위

## 평가 입력의 검수 범위 (6차)

[검수된 평가 사례 로더](VERIFIED_EVALUATION_CASES.md)는 기존 workbook을 수정하지 않고 별도 검수 JSON의 검색/수량 범위별 승인과 근거를 확인한다. 미검수·검수자/일자/근거 누락·미해결 예외는 제외 이유를 반환한다. 공개 합성 fixture는 정상·수량 누락·단위 충돌·다중 도면·공제 오류·미검수 사례를 다룬다. 실제 R-04의 실무 승인 정답 20~50건은 step7 외부 게이트로 남으며, 아래 과거 합성/실모델 평가 기록과 구분한다.

아래는 합성 PDF와 대체 모델 응답으로 검증하는 기능 계약이다. 실제 모델의 검색 정확도·실무 산출 정확도·작업시간 단축률을 뜻하지 않는다.

| PRD 사례 | 자동 검증 내용 | 테스트 |
| --- | --- | --- |
| E-01 | 110호 ACST, 4200/2700 후보의 단위를 사용자가 mm로 확인 → 11.34m2 DRAFT, 출처와 입력·공제 기록, Excel 반영 | test_e01_candidate_inputs_draft_export_and_e06_protection |
| E-02 | 119호 5A, 4.2m × 4.6m, 명시적 면 수 1 → 19.32m2 DRAFT. 면 수 누락은 저장 거부 | test_e02_partition_requires_explicit_faces |
| E-03 | 필수 치수 누락 시 추정하지 않고 400. 기존 수량·상태 유지. 수동값은 출처·단위·검수 메모 필수 | test_e03_e05_invalid_inputs_do_not_write |
| E-04 | 동일 실의 다중 시트 후보와 경고 제공. 다른 PDF의 실행·후보 혼합 거부. 변경된 원본 텍스트는 재검색 요구 | test_e04_multiple_sheets_stale_and_foreign_run |
| E-05 | 단위 미확인·알 수 없는 단위·NaN·음수·후보 위조·공제 단위 불일치 거부. 단위를 크기만으로 확정하지 않음 | test_e03_e05_invalid_inputs_do_not_write |
| E-06 | CONFIRMED 행을 대상으로 로컬/대체 모델 탐색을 다시 해도 계산 초안 저장은 409. 기존 확정값·근거 유지 | test_e01_candidate_inputs_draft_export_and_e06_protection, test_model_assisted_search_can_feed_the_same_verified_draft_tools |

추가로 공제와 재시도 중복 방지, 사용자 최종 검수 상태의 실행 기록 반영, `2.7m`/`80mm` 같은 명시 단위의 정상 추출을 검증한다. 모델에 허용되지 않은 파일·프로젝트·확정 인자가 들어오면 거부한다.

## 선택 영역 Vision 합성 평가

`test_assist_vision.py`는 텍스트 레이어가 없는 합성 스캔 PDF를 사용한다. crop 미리보기와 모델 transport로 전달한 PNG가 같고 전체 페이지와 다름을 확인한다. 전송 권한 미확인·전체 페이지·페이지 경계 밖·미리보기 불일치·임의 파일 경로는 모델 호출 전에 거부한다. 잘못된 도구 응답·설정 누락·판독 불가를 각각 실패/근거 없음으로 표시한다.

대체 판독 결과의 4200/2700을 사용자가 mm로 확인했을 때만 11.34m2 DRAFT로 저장한다. 스캔 PDF 이미지가 변경되면 과거 미리보기와 후보로 전송·저장할 수 없다. 실제 모델의 OCR/시각 판독 정확도를 검증한 테스트는 아니다.

## 실행

저장소 루트에서:

```powershell
.\apps\api\.venv311\Scripts\python.exe -m pytest apps/api/tests/test_assist_search.py apps/api/tests/test_assist_drafts.py apps/api/tests/test_dimension_units.py apps/api/tests/test_known_takeoff_workflow.py
.\apps\api\.venv311\Scripts\python.exe -m pytest apps/api/tests/test_assist_vision.py apps/api/tests/test_evaluation_trials.py
```

전체 회귀·빌드는 `scripts/checks.py --stage manual`을 사용한다.

### 선택 실행하는 실제 모델 평가

`scripts/evaluate_ai_live.py`는 외부 환경설정 파일을 받아 임시 DB와 합성 자료만 사용하는 유료 평가다. 일반 회귀 테스트에서는 실행하지 않는다. 최신 실행 결과는 `AI_ASSIST_LIVE_RESULT.json`에 기록한다.

- E-01~E-06: 실제 검색 결과를 받은 뒤 계산·출처·입력 검증·확정 보호의 서버 계약 확인.
- V-01: 텍스트 레이어 없는 합성 이미지의 4200/2700 판독과 자동 수량 저장 방지.
- V-02: 단위가 인쇄되지 않은 숫자의 단위를 unknown으로 유지.
- V-03: 빈 합성 영역에서 NOT_FOUND와 후보 없음 반환, 산출 행 변경 없음.

2026-11-05 최신 실행은 9항목을 통과했다. 검색 3회와 이미지 판독 2회, 총 2428토큰을 사용했다. 단일 실행의 제한된 합성 평가이며 실제 도면 정확도나 환각이 발생하지 않는다는 보장이 아니다.

## 실제 비교 시 기록할 항목

실제 도면과 정답 산출표를 사용할 권한을 확인한 뒤, 같은 과제를 수동 검색과 AI 보조로 각각 수행한다. 시작부터 재검토·수정·Excel 확인까지의 시간을 기록한다. 과제 순서를 바꿔 이미 본 도면을 기억하는 영향을 구분한다.

- 과제 식별자와 도면 버전, 적용 공제·면 수 기준
- 모드와 모델, 실행 ID, 검색·수량·단위·마감 코드·출처의 정답 일치 여부
- 잘못된 근거 인용, 누락 공제, 수동 개입·수정 횟수, 총 소요시간
- 입력/출력 토큰, 지연시간, 당시 모델 요금에 근거한 비용
- 최종 검수자와 채택 여부, 미확정 질문

실무 정답 20~50건은 기존 4차 private workbook으로 축적한다. 실패 사례는 수량이 비어 있을 수 있으므로 정상 산출 행 템플릿과 구분해 기록한다. 현재 두 합성 사례로 품질 백분율이나 시간 절감 성과를 주장하지 않는다.

앱의 실사용 비교 기록 화면에는 과제 시간 시작/종료와 관찰값 입력이 있다. 동일 과제명·동일 PDF 버전으로 두 방식을 기록하고 GET assist/trials로 조회할 수 있다. 기록은 user_reported이며 자동 평가와 구분한다.
