# F08: Excel 텍스트의 수식 해석 방지

## 문제와 재현

`Summary`, `Details`, `Review`의 텍스트를 `sheet.append()`에 그대로 전달하면 openpyxl이 셀 타입을 추론한다. 수정 전에는 `room_name`, `memo`, 계산 근거 `formula`에 저장한 `=1+1`이 다운로드한 workbook에서 문자열이 아닌 수식(`data_type="f"`)이었다. `#N/A` 문자열도 오류 셀(`data_type="e"`)로 바뀌었다.

무해한 문자열과 합성 DB로 재현했다. Office 외부 연결이나 명령 실행을 검증한 결과는 아니다.

## 출력 계약

- 세 시트의 행과 헤더는 공통 `_append_row()`를 통해 기록한다. Python 문자열은 명시적으로 문자열 셀(`data_type="s"`)로 지정한다.
- 계산 근거 `Formula`도 설명용 문자열이다. Excel에서 실행할 수식을 생성하지 않는다.
- 문자열 앞에 작은따옴표, 공백 등 접두 문자를 추가하지 않는다. `=`, `+`, `-`, `@`로 시작하는 문자열과 `#N/A`, 선행 0, 한글·이모지·줄바꿈을 텍스트로 보존한다.
- 수량과 합계는 숫자 셀을 유지하며 표시 형식은 `0.00`이다. 수량이 없으면 빈 셀을 유지한다.
- `None`과 빈 문자열은 기존처럼 빈 셀로 내보낸다. openpyxl로 저장 후 다시 읽으면 둘 다 `None`이며, 빈 문자열과 null을 구별하는 별도 표현은 추가하지 않는다.
- 기존 도면 출처 분리·합치기와 Review의 `m2` → `m²` 표시는 유지한다. 상태, 합계 포함 기준, 거절 행 제외 규칙도 기존 계약을 따른다.

## 회귀 검증

`apps/api/tests/test_measurement_excel_export.py`는 다음을 검사한다.

1. PDF에서 유래할 수 있는 방 이름을 DB에 넣고, 수정 API로 메모·계산 근거를 저장한 뒤 실제 export endpoint 응답의 Details/Review 셀을 다시 읽는다.
2. 세 시트의 모든 가변 텍스트 열에서 `=1+1`, `=`, `+1+1`, `-1+1`, `@SUM(A1:A2)`, `#N/A`, `00110`, 한글·이모지·줄바꿈의 값과 문자열 타입을 확인한다. 수량은 숫자 타입과 값을 함께 확인한다.
3. `data_only=False`로 수식 셀 생성 여부를 검사하고, `data_only=True`로 읽어도 계산 근거와 메모가 원문 문자열로 남는지 확인한다.
4. 빈값과 미계산 수량, 기존 합계·표시·거절 행 규칙을 검사한다.

수정 전 회귀 파일 실행 결과는 **3 failed, 10 passed**였다. 수식(`f`)과 오류(`e`) 타입 단언이 실패했고, 수정 후에는 **13 passed**였다.

2026-11-04 Windows / Python 3.11.9 / Node 24.14.0 / openpyxl 3.1.5 / PyMuPDF 1.27.2.3에서 검증했다. 설치는 README의 독립 가상환경 절차를 사용했다.

| 명령 | 결과 |
| --- | --- |
| `.\apps\api\.venv311\Scripts\python.exe -m pytest apps/api/tests` | 169 passed, 2 skipped |
| `.\apps\api\.venv311\Scripts\python.exe -m pytest scripts` | 71 passed |
| `npm.cmd --prefix apps/web test` | 26 passed |
| `npm.cmd --prefix apps/web run build` | 통과 |
| `.\apps\api\.venv311\Scripts\python.exe scripts/doctor.py` | 통과 |

비공개 샘플 PDF가 필요한 테스트 2개는 생략됐다. API 실행에는 Starlette의 httpx TestClient 사용에 관한 deprecation warning 1개가 있었다. 실제 Excel/LibreOffice 앱에서 열기와 브라우저 E2E는 수행하지 않았다.

F09 Python 의존성·PDF 오류 처리와 F12 frontend 의존성 갱신은 별도 작업이다. README와 의존성 파일은 이 변경에 포함하지 않는다. 기존 README의 Excel 보강 예정 문구는 F08 병합 후 공개 준비 문서 정리 시 갱신할 필요가 있다.
