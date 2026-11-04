# 합성 도면으로 산출 흐름 확인하기

[README의 환경 준비와 서버 실행](../README.md#빠른-시작--windows-powershell)을 먼저 완료한다. 실제 고객 도면·개인정보가 없는 두 페이지 PDF를 직접 생성한다. 이 예시는 기능 동작을 확인하기 위한 것이며 실무 도면의 정확도를 측정하는 benchmark가 아니다.

## 1. PDF 생성

저장소 루트의 PowerShell에서 실행한다. 지정한 이름의 파일이 이미 있으면 덮어쓰지 않는다. 다시 생성하려면 다른 파일명을 사용한다.

```powershell
@'
from pathlib import Path
import fitz

out = Path("data/samples/synthetic-demo.pdf")
out.parent.mkdir(parents=True, exist_ok=True)
if out.exists():
    raise SystemExit("File already exists; use it or choose another filename.")

doc = fitz.open()
page = doc.new_page(width=595, height=842)
page.insert_text((50, 50), "A101 FLOOR PLAN", fontsize=14)
page.insert_text((100, 110), "ROOM 101 DEMO ROOM")
page.draw_rect(fitz.Rect(100, 150, 520, 420), color=(0, 0, 0))
page.insert_text((280, 140), "4200")
page.insert_text((55, 290), "2700")

page = doc.new_page(width=595, height=842)
lines = [
    "A401 INTERIOR FINISH SCHEDULE",
    "RM NOS | ROOM NAMES | FLOOR | BASE | INTERIOR WALL | CEILING | HGT",
    "101 | DEMO ROOM | VCT | RB | PT | ACT | 2700",
]
for index, line in enumerate(lines):
    page.insert_text((30, 50 + index * 25), line, fontsize=9)
doc.save(out)
doc.close()
print(out.as_posix())
'@ | .\apps\api\.venv311\Scripts\python.exe -
```

출력 경로는 `data/samples/synthetic-demo.pdf`다. 현재 `.gitignore`의 PDF 제외 규칙을 유지한다. 이 파일을 공개 저장소에 강제로 추가할 필요는 없다.

## 2. 화면에서 업로드와 추출

1. <http://127.0.0.1:5173/upload>에서 Project를 선택하거나 데모용 프로젝트를 만든다.
2. 위 PDF를 선택해 `Upload`를 누르고 Drawing File ID를 기록한다.
3. `Process pages` → `Detect sheets` → `Classify sheets`를 순서대로 실행한다.
4. 도면 목록에서 다음 분류를 확인한다.

| 페이지 | 도면 | 역할 |
| --- | --- | --- |
| 0 | A101 | FLOOR_PLAN |
| 1 | A401 | FINISH_SCHEDULE |

5. Room Finish 화면에서 해당 Drawing File ID를 조회하고 후보를 추출한다. 방 101 / DEMO ROOM의 마감 후보 한 행을 확인한다.
6. Measurement 화면에서 산출 후보를 생성한다. 이 합성 마감표는 바닥·천장·걸레받이·벽 후보 네 개를 만든다.

## 3. 계산과 Excel 확인

1. 방 101의 `FLOOR_AREA` 후보를 선택한다.
2. 사각형 면적의 Width에 `4.2`, Height에 `2.7`을 입력하고, 출처에 `A101`을 추가한다.
3. 미리보기 `4.2 * 2.7 = 11.34 m2`를 확인하고 저장한다.
4. 검토 후 확정 체크박스를 사용한다. 수정하려면 **재검토 시작**으로 확정을 취소한다.
5. Excel을 내려받아 다음을 확인한다.

- `Summary`: FLOOR / VCT / m2의 수량 11.34
- `Details`: 방 번호, 식, 수량, 상태, 출처 도면 보존
- `Review`: 거절하지 않은 검수 대상 포함
- 바닥 행의 출처에는 마감표 `A401`과 평면도 `A101`이 함께 남음

다른 후보는 수량이 비어 있어도 정상이다. 이 데모에서는 바닥 한 행만 계산한다. 생성한 도형의 치수 표시는 합성 입력이며, 시스템이 방 경계와 치수의 관계를 스스로 이해했다고 해석하지 않는다.

## 문제 확인

- API 접속 불가: <http://127.0.0.1:8000/health>와 API 터미널을 확인한다.
- 이미지 없음: `Process pages`가 완료됐는지 확인한다.
- 마감 후보 없음: sheet 역할이 `FINISH_SCHEDULE`인지 확인하고, 필요하면 수동 입력 흐름을 사용한다. 실제 PDF의 표 구조에 따라 결과가 달라질 수 있다.
- 5173 포트 사용 중: 기존 서버를 확인한다. `--strictPort` 때문에 다른 포트로 조용히 이동하지 않는다.
- 손상 PDF 정리 오류: 현재 설치는 PyMuPDF 1.28.2가 포함된 Python lock을 사용한다. Windows 파일 핸들 문제는 메모리 스트림 검증으로 수정했다. 외부 잠금·권한으로 정리가 실패하면 로그의 upload_id를 확인하고 [PDF 오류·수동 정리 계약](PDF_UPLOAD_REPRODUCIBILITY.md)을 따른다.

## 검증 기록

2026-11-04, Python 3.11.9 / PyMuPDF 1.27.2.3 / Node 24.14.0에서 다음을 확인했다.

- 위 합성 PDF의 실제 API 업로드·렌더링·분류·후보 추출
- 방 후보 1개, 산출 후보 4개, 바닥 11.34 m2 계산·확정
- Excel 세 시트 및 출처 `A401, A101`
- API `/health`, Vite 화면 HTTP 응답, `/api/health` 프록시 각각 200

화면의 모든 클릭을 브라우저 E2E로 검증한 기록은 아니다. 계산·검수 UI의 기존 회귀 테스트와 실제 API 경로 검증을 구분한다.
