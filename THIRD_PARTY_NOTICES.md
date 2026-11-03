# Third-party notices

Copyright (C) 2026 vanilalatte03 and contributors — 프로젝트의 원본 코드·문서는 AGPL-3.0-only로 제공한다. [LICENSE](LICENSE), [적용 정책](docs/LICENSE_POLICY.md)을 따른다. 아래 외부 저작물의 고유 라이선스·저작권 표시는 유지되며 이 고지로 재허가하지 않는다.

이 저장소는 외부 패키지의 배포본을 vendoring하지 않는다. node_modules, Python wheel, 빌드 결과는 포함하지 않으며 의존성은 설치 시 원래 배포처에서 받는다. 아래는 사용 사실과 확인한 조건을 안내하기 위한 고지다.

## 직접 runtime 의존성

| 패키지 | 라이선스 | 원본 |
| --- | --- | --- |
| FastAPI | MIT | https://github.com/fastapi/fastapi |
| Uvicorn | BSD-3-Clause | https://github.com/encode/uvicorn |
| SQLAlchemy | MIT | https://github.com/sqlalchemy/sqlalchemy |
| pydantic-settings | MIT | https://github.com/pydantic/pydantic-settings |
| python-multipart | Apache-2.0 | https://github.com/Kludex/python-multipart |
| PyMuPDF / MuPDF | AGPL v3 또는 공급자의 Artifex Commercial 조건 | https://github.com/pymupdf/PyMuPDF |
| openpyxl | MIT | https://pypi.org/project/openpyxl/ |
| React / React DOM | MIT | https://github.com/facebook/react |
| React Router DOM | MIT | https://github.com/remix-run/react-router |

PyMuPDF와 MuPDF의 저작권자는 Artifex 및 해당 기여자다. 이 프로젝트는 공개 소스의 AGPL 방식으로 사용하며 공급자의 상용 라이선스를 제공하거나 구매했다는 주장을 하지 않는다. [공급자 안내](https://pymupdf.readthedocs.io/en/latest/about.html#license-and-copyright)와 설치된 PyMuPDF의 `.dist-info/COPYING` 원문을 확인한다.

## 직접 개발·검증 의존성

- pytest: MIT; httpx: BSD-3-Clause.
- TypeScript: Apache-2.0.
- Vite, @vitejs/plugin-react, Vitest, jsdom, @testing-library/dom, @testing-library/react, @types/react, @types/react-dom: MIT.
- 선언·설치 버전과 전이 의존성 전체는 [의존성 스냅샷](docs/DEPENDENCY_LICENSES.md)에 기록했다.

## 전이 의존성 중 별도로 확인할 조건

- **caniuse-lite 1.0.30001820 — CC-BY-4.0:** Ben Briggs와 caniuse-lite 기여자의 브라우저 지원 데이터 패키지다. [원본 프로젝트](https://github.com/browserslist/caniuse-lite), [해당 버전](https://www.npmjs.com/package/caniuse-lite/v/1.0.30001820), [CC BY 4.0 조건](https://creativecommons.org/licenses/by/4.0/), 설치 파일 `node_modules/caniuse-lite/LICENSE`를 참고한다. 이 저장소는 해당 패키지를 수정·재배포하지 않으며, 빌드 도구에서 원본 의존성을 사용한다. 데이터를 산출물에 포함해 배포한다면 출처·저작자·라이선스 링크와 변경 여부를 보존한다.
- **certifi — MPL-2.0:** Mozilla 루트 인증서 묶음을 포함하는 패키지다. [원본](https://github.com/certifi/python-certifi)과 설치된 배포본의 LICENSE를 따른다. 해당 파일을 별도로 수정·재배포할 때 MPL의 파일 단위 소스 제공 조건을 확인한다.
- **typing_extensions — PSF-2.0**, **packaging — Apache-2.0 OR BSD-2-Clause** 등도 원래 고지를 유지한다. 모든 전이 의존성을 MIT로 간주하지 않는다.

## 바이너리·bundle을 배포하는 경우

이 고지만을 외부 라이브러리의 원문 고지나 소스 제공의 대체물로 사용하지 않는다. 실제 배포 파일에 포함되는 각 버전의 LICENSE·COPYING·NOTICE·저작권 표시와 필요한 source를 수집하고, 수정 여부와 소스 접근 방법을 제공한다. AGPL 소스 제공 의무 등은 배포·서비스 형태에 따라 적용되므로 LICENSE 전문을 따른다.

실제 도면 PDF·업무 Excel·DB·고객 자료에 대한 재배포 권한은 이 파일에 포함되지 않는다.
