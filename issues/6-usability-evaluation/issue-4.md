# Step 4: Windows 사용자 종료 조작 검증 미완료

상태: 실제 GUI 종료 조작 검증 대기. 구현과 자동 검사는 별도 진행하며 step4는 pending으로 유지한다. 다음 단계로 완료를 전파하지 않는다.

## 확인한 사실 (2026-11-08)

- 준비된 Windows의 Python은 tkinter를 포함하지 않아, 추가 의존성 없이 ctypes/Win32 GUI로 구현했다.
- 실제 `Start Takeoff.cmd`를 Shell에서 실행한 뒤 Computer Use로 **시작**을 클릭했다. GUI 실행 중 상태·임시 데이터 경로와 기본 Edge에 열린 작업 화면을 관찰했다.
- API/웹은 각각 127.0.0.1:8000 / 127.0.0.1:5173에서만 listen했다. 같은 저장소의 두 번째 실행은 한국어 중복 안내를 표시했고 기존 실행은 유지됐다.
- 별도 Playwright 세션에서 `/workflow`와 프로젝트 선택이 표시됐다. API 요청은 정상이며 favicon 404 하나가 관찰됐다.
- 임시 SQLite에 합성 프로젝트를 저장한 뒤, 확인된 소유 GUI 프로세스 핸들로 비정상 종료를 모사했다. stdin EOF 정리 후 supervisor/API/Vite/venv shim의 관찰 PID가 모두 종료됐고 두 포트도 닫혔다. DB의 합성 프로젝트는 보존됐다. 업무 DB·도면·키는 사용하지 않았다.
- Playwright 소유 브라우저 세션은 종료했다. 사용자의 기존 브라우저는 종료하지 않았다.

## 중단 원문과 미완료 범위

Edge 탭 URL을 Windows Computer Use로 확인하던 중 다음 정책 중단을 받았다.

> Computer Use has been stopped for this turn because it could not determine the current browser URL on Windows with enough confidence to enforce policy. Stop your work and send a final message noting why Computer Use ended.

이후 UI 입력을 중단하고 완료 요약을 남겼다. 새 CUA 세션·다른 UI 자동화·SendMessage로 우회하지 않았다. 비UI 수단으로 소유 프로세스만 정리했다.

**안전 종료 버튼 및 실행 중 창의 ×를 실제 클릭한 결과는 미검증**이다. 하위 프로세스/Job 자동 테스트와 비정상 종료 정리는 그 사용자 조작 검증을 대신하지 않는다. 구현 후 변경한 준비 신호·환경 정규화도 자동 검사와 비UI 실행 검증으로 구분한다.

## 다음 조치

허용된 정상 사용자 세션에서 준비된 환경과 임시 DB/합성 파일로 `Start Takeoff.cmd` → **시작** → 작업 화면 → 저장 성공 → **안전 종료** 완료를 확인한다. 재시작 뒤 창의 **×**로도 정상 종료되는지 확인하고, 두 포트·소유 프로세스 종료와 저장 데이터 보존을 기록한다. 충돌 시 무관한 listener가 계속 살아 있고 실패 후 재시도할 수 있는지도 확인한다. 현재 정책 중단을 우회해 자동화하지 않는다. 이 증거가 생기기 전 step4 완료·merge를 승인하지 않는다.
