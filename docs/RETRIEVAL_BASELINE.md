# 합성 도면 검색 기준선

6차 step2는 검색 근거의 순위만 평가한다. 수량·산출 상태를 쓰거나 확정하지 않는다. 공개 [원본 fixture](../scripts/fixtures/retrieval_corpus.json)는 새로 작성한 가상 11페이지, 질문 12개와 검색 정답·근거 위치·검수 진술을 포함한다. `synthetic-contract-review`, 2026-11-06, `synthetic-retrieval-v1`은 개발 계약 검토이며 실무자 승인이나 실제 도면 성능이 아니다.

## 입력과 검수 경계

평가기 `scripts/evaluate_retrieval.py`는 이 고정 fixture만 읽는다. 각 페이지를 임시 PDF에 쓰고 PyMuPDF로 다시 추출해 `classify_sheet_role`로 역할을 결정한다. 임시 workbook/검수 sidecar를 만들어 [step1 로더](VERIFIED_EVALUATION_CASES.md)의 `scope="retrieval"` 승인 목록만 양성 평가에 사용한다. 수량은 비워 두고 상태는 NEEDS_REVIEW로 유지한다. 기존 업무 workbook과 앱 DB는 열거나 수정하지 않는다. source ID와 sheet 번호는 평가 매핑에만 사용하며 검색어·역할 규칙에 하드코딩하지 않는다.

- 양성 정답 9건: 반복된 실 번호/숫자·마감 코드, 영문 ROOM, 숫자로 시작하는 파티션 코드, 코드 suffix, 다중 필수 도면, 동점, 정답은 있으나 검색 결과가 없는 질문이다.
- `no-relevant`: 전체 합성 corpus를 검토해 관련 도면이 없다고 명시한 음성 1건이다. step1 로더는 빈 정답을 양성으로 승인하지 않는다. 양성 지표에서 제외하고 검수자/일자/전 페이지 검토 위치와 `correct_abstention`을 별도 진단한다. 빈 결과를 Recall=1로 더하지 않는다.
- `unknown-truth`: 관련성 검수 자체가 없는 1건이다. `scope_not_reviewed`로 제외하며 검색·AI 호출과 지표에 사용하지 않는다. 음성 정답으로 간주하지 않는다.
- `unreviewed`: 정답 후보가 있어도 미검수인 1건은 `scope_not_reviewed`로 제외한다. 보고서에는 Excel 행 번호·범위·로더의 제외 이유를 그대로 보존한다.

fixture의 원본·질문·검수 정보 전체 SHA256과 PDF에서 추출한 텍스트/역할 SHA256, Python/PyMuPDF 버전, 설정, 검색 소스 SHA256을 기록한다. workbook ZIP의 저장 시각이나 PDF 내부 ID는 점수에 사용하지 않는다. 동일 입력 반복 실행의 의미 있는 결과는 동일하다. 원본 텍스트나 질문·정답·검수·설정·런타임이 달라지면 `compare`는 비교를 거부한다. corpus를 수정하면 버전을 올리고 기준선과 후보를 모두 다시 측정한다.

## 지표 정의

각 사례에서 실제 `local_search_arguments(question)` → `search_sheets(sheets, arguments, question)`의 반환 순위(최대 12개)를 사용한다. 검수 정답은 순위가 완성된 다음에만 대조하며 검색 입력에 전달하지 않는다. source ID 중복은 제거한 순위로 계산한다.

- Recall@3: 상위 3개 안에 포함된 정답 도면 수 / 그 사례의 **모든 필수 정답 도면 수**. 사례별 값을 양성 9건에 대해 동일 가중 평균한다. 필수 도면이 3개보다 많으면 Recall@3은 1에 도달할 수 없다.
- MRR@12: 반환된 최대 12개 중 첫 정답의 1부터 시작하는 rank의 역수. 정답이 없거나 12개 밖이면 0이다. 양성 사례별 값의 평균이다. 여러 필수 도면 중 하나만 찾았어도 MRR은 높을 수 있으므로 단독 성공 지표로 쓰지 않는다.
- 모든 필수 도면 포함률@3: 상위 3개가 해당 사례의 필수 정답을 **모두** 포함한 사례 수 / 양성 사례 수. 사례별 `missing_at_3`도 기록한다.
- 동점: 요청 용어의 서로 다른 일치 수 → 기존 역할 우선순위 → 일치 빈도 → 페이지 인덱스 → sheet ID로 정렬한다. 입력 목록 순서가 바뀌어도 결과가 같다.
- 양성 검색 결과 없음은 세 지표 모두 0이다. 정답 없음·미검수·unknown은 이 분모에서 제외한다. 분모 0은 평균 `null`이며 비교를 거부한다.

## 수정 전후 결과

[기준선](evaluation/retrieval-baseline-v1.json)은 main `ae55dc0f60ea9ad25be3cf97eb3b84a5dde59df3`의 실제 검색 함수를 실행했고, [후보](evaluation/retrieval-candidate-v1.json)는 이 단계의 개선을 실행했다. 기준선을 처음 측정한 뒤 보고서 메타데이터를 추가하면서 원래 소스를 `git show ae55dc0:apps/api/app/services/assist_search.py`로 메모리의 별도 모듈에 로드해 다시 측정했다. 파일/원본 브랜치는 수정하지 않았다. 두 보고서의 입력·추출 corpus·설정·제외 목록은 동일하다.

| 지표 | 기준선 | 후보 | 변화 |
| --- | ---: | ---: | ---: |
| 양성 분모 | 9 | 9 | 0 |
| Recall@3 | 0.740741 | 0.888889 | +0.148148 |
| MRR@12 | 0.833333 | 0.888889 | +0.055556 |
| 모든 필수 포함률@3 | 0.555556 (5/9) | 0.888889 (8/9) | +0.333333 |
| 명시 음성의 올바른 빈 결과 | 1/1 | 1/1 | 0 |

`room-ceiling`, `english-room`, `partition-multi`의 순위가 개선됐다. 다른 실의 반복 코드가 관련 도면을 밀어내던 문제를 요청 용어의 **범위 충족 수** 우선 정렬로 줄이고, 그 안에서는 역할 순서를 유지했다. `ROOM`/`RM`을 마감 코드에서 제외하고 `ZXQ-7` 같은 코드의 suffix 숫자를 실 번호로 오인하지 않도록 경계를 고쳤다. 특정 실/마감 코드/도면 번호를 규칙에 추가하지 않았다. 모든 사례의 세 지표 중 악화는 0건이다.

남은 실패 `not-found-positive`는 "도면에 없는 별칭 연구공간"을 Room 120 Lab과 연결하지 못해 빈 결과다. 이 질문의 양성 정답 FLOOR가 알려져 있으므로 점수 0이며, no-relevant와 다르다. 별칭 사전이나 AI 추론을 이 fixture에 맞춰 추가하지 않았다. 추출 텍스트가 있는 간단한 합성 PDF만 다루므로 OCR·실무 도면·작업시간에 대한 결과로 일반화하지 않는다.

## 실행과 비교

```powershell
.\apps\api\.venv311\Scripts\python.exe scripts/evaluate_retrieval.py --output "$env:TEMP\retrieval-current.json" --baseline docs/evaluation/retrieval-baseline-v1.json
.\apps\api\.venv311\Scripts\python.exe -m pytest scripts/test_evaluate_retrieval.py apps/api/tests/test_assist_search.py
```

보고서는 사례별 질문·검색 인자·전체 순위·정답·누락·지표, 제외 이유, 음성 진단과 baseline 대비 delta/악화 사례를 포함한다. 고정 artifact를 덮어쓰지 않고 별도 결과 경로로 비교할 수 있다. CI의 Python patch 버전이 다르면 비교기가 이를 감지하므로 같은 runtime에서 양쪽을 다시 실행해야 한다. 회귀 테스트는 CI에서 원본/추출 hash·사례별 결과·지표를 검사하며 개발 PC의 runtime 문자열을 강제하지 않는다.

다른 runtime에서 수정 전후를 다시 측정하려면 **현재 단계의 evaluator를 유지한 채** 아래 명령으로 검증된 이전 commit의 검색 함수만 메모리에서 로드한다. 새 evaluator가 없는 과거 commit으로 checkout할 필요가 없다. 저장소 루트 PowerShell에서 실행하며 결과만 임시 폴더에 쓴다. 고정된 저장소 commit의 신뢰된 코드를 실행하는 절차이므로 임의 외부 소스나 입력으로 대체하지 않는다. 소스 SHA256은 Windows 개행 차이를 제거한 UTF-8/LF 기준이다.

```powershell
@'
import hashlib, json, subprocess, sys, tempfile, types
from pathlib import Path
sys.path.insert(0, 'scripts')
import evaluate_retrieval as evaluation
source = subprocess.check_output([
    'git', 'show',
    'ae55dc0f60ea9ad25be3cf97eb3b84a5dde59df3:apps/api/app/services/assist_search.py'
]).decode('utf-8').replace('\r\n', '\n')
original = types.ModuleType('trusted_retrieval_baseline')
exec(compile(source, 'ae55dc0:assist_search.py', 'exec'), original.__dict__)
evaluation.local_search_arguments = original.local_search_arguments
evaluation.search_sheets = original.search_sheets
report = evaluation.evaluate()
report['search_source_sha256'] = hashlib.sha256(source.encode()).hexdigest()
output = Path(tempfile.gettempdir()) / 'retrieval-baseline-current-runtime.json'
output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(output)
'@ | .\apps\api\.venv311\Scripts\python.exe -
.\apps\api\.venv311\Scripts\python.exe scripts/evaluate_retrieval.py --output "$env:TEMP\retrieval-candidate-current-runtime.json" --baseline "$env:TEMP\retrieval-baseline-current-runtime.json"
```

### 선택적 실제 AI 비교

이번 단계에서는 **실제 AI 품질 비교 미실행** (`ai_quality_comparison: not_run`)이다. 대체 함수 테스트는 질문 누출 방지 계약만 확인한다. 이전 단계의 실제 모델 결과를 이번 corpus 점수로 재사용하지 않는다.

명시적으로 유료 호출을 선택할 때만, 기존 서버 설정에 모델과 키가 준비된 환경에서 아래를 실행한다. 평가기는 외부 환경 파일을 탐색하거나 불러오지 않는다.

```powershell
.\apps\api\.venv311\Scripts\python.exe scripts/evaluate_retrieval.py --ai-opt-in --output "$env:TEMP\retrieval-ai.json" --baseline docs/evaluation/retrieval-candidate-v1.json
```

동일한 검수 양성 9개와 음성 1개의 **질문만** 기존 `model_search_arguments`에 보낸다. 정답·원문·sheet ID·검수 기록은 보내지 않는다. 검색은 같은 로컬 corpus에서 `search_sheets`로 실행한다. 모델 이름, 모델별 응답 ID/사용량, 500 출력 토큰·25초 timeout·단일 도구·병렬 호출 금지·store=false 설정을 기록한다. 모델 실패는 성공/빈 정답으로 바꾸지 않고 실행 오류로 중단한다. 별도의 수량 계산·확정 권한이나 후속 에이전트 기능은 없다.
