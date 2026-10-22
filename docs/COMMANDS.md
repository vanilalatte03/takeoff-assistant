# 명령어

이 파일은 프로젝트 운영 명령의 단일 출처입니다. `.codex/project-profile.json`과 동기화해서 유지하세요. Template guard/check script는 두 파일을 모두 읽습니다.

## 활성 명령

| 이름 | 명령 | 필수 | 설명 |
| --- | --- | --- | --- |
| dev-api | `cd apps/api && .\.venv311\Scripts\python.exe -m uvicorn app.main:app --reload` | no | API 의존성 설치 후 FastAPI backend를 로컬에서 실행 |
| dev-web | `cd apps/web && npm run dev` | no | Vite frontend 실행 |
| setup-api-venv | `C:\WorkSpace\finish-takeoff\.tools\python-3.11.9-nuget\tools\python.exe -m venv apps\api\.venv311` | no | 로컬 Python 3.11.9 runtime으로 backend venv 생성 |
| install-api | `cd apps/api && .\.venv311\Scripts\python.exe -m pip install -e ".[dev]"` | no | backend runtime/test dependency 설치 |
| install-web | `cd apps/web && npm install` | no | frontend dependency 설치 |
| test | `cd apps/api && .\.venv311\Scripts\python.exe -m pytest` | yes | backend test 실행 |
| test-harness | `.\apps\api\.venv311\Scripts\python.exe -m pytest scripts` | yes | repository harness script test 실행 |
| test-web | `cd apps/web && npm run test` | yes | 계산·페이지 전환·측정 저장의 frontend 회귀 테스트 실행 |
| build | `cd apps/web && npm run build` | yes | frontend type-check 및 build 실행 |
| review | `.\apps\api\.venv311\Scripts\python.exe scripts\doctor.py` | no | Codex template 준비 상태 점검 |
| check | `.\apps\api\.venv311\Scripts\python.exe scripts\checks.py --stage manual` | no | 설정된 lint/test/build check 실행 |
| phase | `.\apps\api\.venv311\Scripts\python.exe scripts\execute.py <phase-name>` | no | Harness phase step 실행 |

## 현재 Windows 로컬 Python 3.11 환경

- Python runtime: `C:\WorkSpace\finish-takeoff\.tools\python-3.11.9-nuget\tools\python.exe`
- Backend venv: `apps/api/.venv311`
- 시스템 PATH에 `python` 또는 `py`가 없어도 위 명령은 동작해야 한다.
- 기존 `apps/api/.venv`가 Windows Store Python 경로를 가리키면 사용하지 말고 `.venv311`을 사용한다.

### Backend test

```powershell
cd C:\WorkSpace\finish-takeoff\takeoff-assistant\apps\api
.\.venv311\Scripts\python.exe -m pytest
```

### Harness script test

```powershell
cd C:\WorkSpace\finish-takeoff\takeoff-assistant
.\apps\api\.venv311\Scripts\python.exe -m pytest scripts
```

## 참고

- F01~F07 무결성 회귀와 기존 SQLite 소속 처리 기준은 `docs/INTEGRITY_FIXES.md`를 참고합니다.
- 프론트엔드 컴포넌트 테스트 환경은 Node 24에서 검증합니다. 지원 Node 범위는 `apps/web/package.json`의 engines와 `apps/web/README.md`를 따릅니다.

- 명령 자체가 디렉터리를 이동하지 않는 한 저장소 root에서 실행합니다.
- Backend 명령은 `apps/api/.venv311` Python 3.11 환경을 전제합니다.
- Frontend build는 `apps/web/node_modules`가 설치되어 있다고 가정합니다.
- 아직 root package manager workspace가 없으므로 API와 web 명령은 의도적으로 각 app 디렉터리로 scope를 제한합니다.
