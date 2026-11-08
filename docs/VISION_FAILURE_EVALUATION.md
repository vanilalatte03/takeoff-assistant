# Vision 실패 조건 평가 (6차 step5)

`scripts/evaluate_vision.py`는 업무 파일이나 DB를 열지 않고 고정 합성 crop만 생성한다. 기존 `assist_vision.read_crop`의 전송·구조 검증 경로를 그대로 사용한다. 기본 실행은 모델을 호출하지 않으며 공개 [manifest](evaluation/vision-manifest-v1.json)의 `model_quality=NOT_RUN`, 모든 지표·지연·사용량은 null이다. 과거 `AI_ASSIST_LIVE_RESULT.json`의 9항목은 다른 자료의 역사적 기록이며 이 corpus 품질로 사용하지 않는다.

## 자료와 정답

PyMuPDF 기본 Helvetica, 240×240 RGB PNG를 사용한다. 같은 고정 dependency 환경에서 재생성하고 이미지 SHA256, 정답 JSON fingerprint, 판독기 코드 hash, 설정 fingerprint와 Python/PyMuPDF 버전을 비교한다. 다른 런타임에서 PNG가 바뀌면 동일 입력 평가로 간주하지 않는다. PNG 전체가 평가할 선택 영역이며 앱의 전체 PDF가 아니다.

| 사례 | 생성 내용과 정답 | 판정 |
| --- | --- | --- |
| [rotated](evaluation/vision-v1/rotated.png) | 90도 회전한 `4200 mm` | dimension / mm, 사용자 확인 필요 |
| [low_resolution](evaluation/vision-v1/low_resolution.png) | `2700 mm`를 24px로 래스터화 → 240px 확대 → 분리형 7px box blur | 실제 육안 확인에서 불명확. 입력 문자열은 생성 근거일 뿐 판독 정답이 아님. 정답률 제외, 후보 수·기권 여부만 진단 |
| [mixed](evaluation/vision-v1/mixed.png) | ROOM 110 / ACST / 4200 mm | room_no 110 / finish_code ACST / dimension 4200 mm |
| [unitless](evaluation/vision-v1/unitless.png) | `4200` | dimension / unknown. mm 또는 m 추정은 단위 오류 |
| [blank](evaluation/vision-v1/blank.png) | 흰 영역 | 명시적 음성. 성공한 빈 후보만 NOT_FOUND, 후보 발생은 빈 영역 오탐 |

2026-11-08 로컬 PNG 5개를 실제 시각 확인했다. 합성 정답은 실무자가 검수한 업무 정답이 아니며 모든 판독 후보는 확인 필요다. 흐림 사례에서 숫자를 맞혀도 정확한 판독으로 단정하지 않는다.

## 실행

```powershell
.\apps\api\.venv311\Scripts\python.exe scripts/evaluate_vision.py --output "$env:TEMP\vision-manifest.json" --image-dir "$env:TEMP\vision-images"
.\apps\api\.venv311\Scripts\python.exe -m pytest scripts/test_evaluate_vision.py apps/api/tests/test_assist_vision.py
```

실제 호출은 별도 선택이다. 현재 프로세스에 사용자가 `TAKEOFF_AI_API_KEY`, 이미지 입력 가능한 `TAKEOFF_AI_VISION_MODEL`을 설정한 경우에만 아래 명령을 실행한다. 키나 외부 env 위치를 검색하거나 보고서에 저장하지 않는다. 공개 manifest를 실제 결과로 덮어쓰지 말고 별도 결과 파일을 사용한다. 5회 호출의 비용이 발생한다.

```powershell
.\apps\api\.venv311\Scripts\python.exe scripts/evaluate_vision.py --live --output "$env:TEMP\vision-live.json"
```

사용자가 직접 지정한 외부 파일이 있으면 `--live --env-file "<명시한-env-절대경로>" --model "<사용자가-선택한-Vision-모델>"`을 추가할 수 있다. 지정한 파일의 키/Vision 모델만 읽고 프로세스 내부에서 적용하며 파일 경로나 키를 결과에 쓰지 않는다. 검색 모델을 Vision으로 자동 대체하지 않는다. 파일 지정과 모델 override는 `--live` 없이 사용할 수 없다.

실제 결과는 사례별 모델·Responses endpoint·response ID·elapsed_ms·usage와 오류 유형을 기록한다. 예외 본문은 저장하지 않는다. 현재 검증한 단가가 없어 금액은 미산출(null)이다. 앱의 1회 호출/1500 출력토큰/30초/store=false/detail=high 계약을 사용하며 정답은 모델에게 전달하지 않는다. 실패가 하나라도 있으면 `INCOMPLETE`와 exit 1, 실패 사례 지표 null이다. 설정 누락·no-output·잘못된 응답·provider failure를 성공한 빈 답으로 바꾸지 않는다. 성공한 빈 답은 판독 가능한 양성에서 누락으로, 명시적 빈 영역에서 올바른 기권으로 처리한다.

## 지표와 한계

성공한 명확한 사례만 kind와 공백 정규화된 raw_text를 정확 비교한다. 누락은 정답에만 있는 토큰 수, 오탐은 응답에만 있는 토큰 수다(중복 포함). 값 또는 kind가 틀리면 누락과 오탐을 각각 1개 센다. `value_or_kind_errors`는 그 오탐 수로, 대응 토큰을 추측한 독립 오류율이 아니다. 단위 오류는 kind/raw_text가 일치한 토큰의 unit 불일치다. raw_text 자체의 잘못된 단위는 누락+오탐으로 드러난다. bbox 정확도·일반 OCR 정확도·실무 산출 정확도는 측정하지 않는다. 흐림 사례와 provider 실패는 정확도 분모에 포함하지 않는다. aggregate 정확도나 과거 9항목과의 합산 수치는 만들지 않는다.

대체 응답 테스트는 scorer/transport/API 저장 계약 검증이다. 가짜 모델명·가짜 usage를 사용하는 테스트 통과를 실모델 품질로 발표하지 않는다. 실제 호출 기록은 아래 별도 파일에만 보존하며 기본 manifest의 NOT_RUN을 바꾸지 않는다.

## 승인된 실모델 단일 실행 (2026-11-08)

사용자가 지정한 설정과 평가 프로세스의 명시적 모델 override로 `gpt-6.1-terra`를 사용했다. 공개 합성 PNG 5장에 각 1회 호출했고 유료 재시도는 하지 않았다. [실제 응답·사용량·지연·fingerprint](evaluation/vision-live-20261108.json)는 대체 응답 결과와 별개다. 원본 외부 설정파일은 수정하지 않았고 경로/키는 보고서에 포함하지 않는다.

| 사례 | 실제 응답과 비교 | elapsed_ms | total_tokens |
| --- | --- | ---: | ---: |
| rotated | 4200 mm / mm, 오탐·누락·값/kind·단위 오류 0 | 5014.752 | 577 |
| low_resolution | 빈 후보로 기권. 불명확 사례라 지표 null | 2376.719 | 511 |
| mixed | 110 / ACST / 4200 mm 모두 일치, 오류 0 | 5931.531 | 678 |
| unitless | 4200 / unknown 유지, 오류 0 | 2317.239 | 560 |
| blank | 빈 후보, 빈 영역 오탐 0 | 1425.267 | 493 |

5회 합계 2819토큰이며 확인한 단가가 없어 금액은 미산출이다. 전송·구조 응답은 모두 COMPLETED라 `model_quality=EXECUTED`다. 이 상태는 정확도 PASS나 실무 합격을 뜻하지 않는다. 명확한 양성 3개와 명시적 음성 1개에 대한 단일 실행이며, 작은 표본·고정 글꼴·고정 배치라 일반화할 수 없다. 후보 위치 bbox는 점수화하지 않았다. 실무 정확도·작업시간 절감·사용자 채택은 미검증이다.

API 회귀는 오독 값·잘못 추정한 단위·실 번호 혼동·실제 빈 crop의 대체 오탐·오류가 수량/수식/단위/상태/출처/좌표/공제를 바꾸지 않음을 비교한다. 후보의 suggested_value는 null, unit_confirmed=false, 근거·crop hash·동의·NEEDS_REVIEW를 유지한다. 단위 확인 누락·검수 메모 누락·모델이 지정한 quantity/CONFIRMED 저장은 거부한다. 사람이 명시적으로 잘못된 값을 확인한 경우까지 시스템이 정답을 보장하지는 않는다. 기존 정상 회귀는 사용자가 출처·단위·공제를 확인했을 때만 DRAFT를 저장하고, 원본 이미지 변경 시 거부함을 검증한다.

step5 도구와 합성 계약의 완료는 step7의 업무 도면 권한·실무 정답·실제 관찰·작업시간·채택 판단이나 R-04/11/12의 완료를 뜻하지 않는다.
