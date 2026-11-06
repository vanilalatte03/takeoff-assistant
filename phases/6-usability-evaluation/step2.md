# 단계 2: 도면 검색 기준선과 회귀 비교

## 의존성과 범위

선행 단계: 1의 인수 기준 충족. 이 단계만 하나의 브랜치와 PR로 처리한다.

## 읽어야 할 파일

- `AGENTS.md`
- `phases/README.md`
- `phases/6-usability-evaluation/README.md`
- `phases/6-usability-evaluation/index.json`
- `docs/ARCHITECTURE.md`
- `docs/ADR.md`
- `docs/COMMANDS.md`
- `apps/api/app/services/assist_search.py`
- `apps/api/app/services/sheet_search.py`
- `apps/api/app/services/sheet_classifier.py`
- `apps/api/tests/test_assist_search.py`
- `docs/AI_ASSIST_EVALUATION.md`

## 작업

고정 합성 도면과 질문·관련 도면 정답을 사용해 로컬 검색을 평가한다. 반복 실 번호/숫자, 마감 코드, 다중 필수 도면, 결과 없음 등을 포함하고 Recall@3의 분모와 MRR 정의를 문서화한다. 필요한 도면 모두 포함 여부와 사례별 실패를 기록한다. 미검수 업무 데이터는 정량 점수에서 제외한다. 개선한다면 수정 전후를 동일 자료·질문·설정으로 비교하고 회귀를 보고한다. AI 비교는 명시적 선택 실행이며 같은 사례와 모델/설정을 기록한다.

## 인수 기준과 검증

지표 계산, 정답 없는 사례 제외, 다중 도면, 동점/결과 없음, 고정 입력 재현성을 테스트한다. baseline과 candidate 결과를 비교할 수 있어야 한다. API/스크립트 관련 테스트 및 전체 수동 검사를 실행한다. 모델 미호출이면 AI 품질 비교 미실행으로 표시한다.

공통 검사: `git diff --check`, `python scripts/doctor.py`. 기능 단계는 `docs/COMMANDS.md`의 API·스크립트·웹 테스트와 빌드를 실행한다 (`python scripts/checks.py --stage manual` 또는 표의 개별 명령). Windows에서 저장소 Python 가상환경을 사용한다. 사설 데이터와 실제 API 키 없이 CI가 통과해야 한다.

외부 Codex 읽기 전용 리뷰와 필수 CI를 통과한 뒤 머지한다. PR에 변경 이유·선택한 방식·검증·미검증 항목을 기록하고 해당 step 상태를 갱신한다. 실패/외부 조건은 `issues/6-usability-evaluation/issue-N.md`에 재현과 다음 조치를 기록한다.

## 금지사항

- 미검수 결과를 정답이나 CONFIRMED로 만들지 마라. 이유: 사용자 검수와 실무 정답은 별도 증거가 필요하다.
- 업무 PDF·산출표·DB·환경파일을 Git이나 공개 보고서에 포함하지 마라. 이유: 사설 자료와 비밀을 보존해야 한다.
- 기존 변경을 덮어쓰거나 후속 단계 기능을 함께 구현하지 마라. 이유: PR 범위와 복구 가능성을 유지해야 한다.
