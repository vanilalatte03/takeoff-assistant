# F12: 프런트엔드 의존성 보안 갱신

확인일: 2026-11-04. 기준 main: `5b2681e762abb4d47a68329110af1531e038f771`.

## 결과와 범위

현재 npm registry의 advisory와 각 공식 보안 공지의 수정 범위를 확인한 뒤 Router, Vite 및 영향을 받는 전이 의존성을 갱신했다. `npm audit fix --force`와 강제 override는 사용하지 않았다. Python 의존성, API/exporter, 공통 README/COMMANDS/DEMO는 변경하지 않았다.

| 검사 | 변경 전 critical / high / moderate / low | 변경 후 critical / high / moderate / low |
| --- | --- | --- |
| `npm audit --json` | 0 / 5 / 4 / 2 (11개 패키지 항목) | 0 / 0 / 0 / 0 |
| `npm audit --omit=dev --json` | 0 / 0 / 3 / 0 (3개 패키지 항목) | 0 / 0 / 0 / 0 |

패키지 항목 수는 독립적인 앱 취약점 수가 아니다. 예를 들어 Router 하나의 advisory가 `react-router`, `react-router-dom`, `@remix-run/router` 경로에 중복 반영된다. audit 0은 이 시점 registry의 알려진 advisory에 대한 결과이며, 앱 전체의 보안이나 실제 공격 가능성을 증명하지 않는다.

## 버전 선택

| 의존성 | lock 변경 전 → 변경 후 | 선택 이유 |
| --- | --- | --- |
| react-router-dom / react-router | 6.30.3 → 7.18.2 | 6.x에 수정이 없는 권고와 7.18.0의 추가 RSC 권고까지 해소하는 최소 7.x 패치 |
| @remix-run/router | 1.23.2 → 제거 | Router 7의 의존성 구조로 대체 |
| vite | 7.3.2 → 7.3.7 | 현재 Vite/내장 launch-editor 공지의 7.x 수정 버전 |
| esbuild | 0.27.7 → 0.28.2 | Vite 7.3.7의 허용 범위에서 Windows serve 문제 수정 |
| @babel/core | 7.29.0 → 7.29.7 | `npm audit fix --package-lock-only`가 허용 범위에서 해소 |
| browserslist | 4.28.2 → 4.29.5 | 동일 |
| baseline-browser-mapping | 2.10.25 → 2.11.35 | 동일 |
| postcss | 8.5.13 → 8.5.32 | 동일 |
| nanoid | 3.3.12 → 3.3.20 | 동일 |
| source-map-js | 1.2.1 → 1.2.2 | 동일 |

전이 의존성 갱신에는 위 패키지가 요구하는 Babel helper와 브라우저 데이터, esbuild의 플랫폼별 optional package도 포함된다. React/React DOM, TypeScript, Vitest, jsdom, plugin-react의 직접 버전은 유지했다. 직접 선언의 하한은 `react-router-dom: ^7.18.2`, `vite: ^7.3.7`이고, 재현 설치에는 커밋된 lockfile과 `npm ci`를 사용한다.

### Router major 전환 검토

[공식 v6→v7 가이드](https://github.com/remix-run/react-router/blob/react-router%407.18.2/docs/upgrading/v6.md)의 Node 20+/React 18+ 요구사항은 기존 Node 24/React 19 조합이 충족한다. 앱은 `BrowserRouter`, `Routes`, `Route`, `Navigate`, `NavLink`, `Link`, `useNavigate`, `useParams`, `useSearchParams`를 사용하는 Declarative SPA다. SSR/hydration, RSC, Data Router action/loader, 다중 세그먼트 splat, 컴포넌트 내부 `React.lazy` 사용이 없다. 기존 `react-router-dom` 호환 진입점을 유지하여 화면 구현과 import의 전면 변경을 피했다.

6.30.6은 일부 redirect 문제를 수정하지만 [GHSA-wrjc-x8rr-h8h6](https://github.com/remix-run/react-router/security/advisories/GHSA-wrjc-x8rr-h8h6)와 [GHSA-337j-9hxr-rhxg](https://github.com/remix-run/react-router/security/advisories/GHSA-337j-9hxr-rhxg)의 수정 범위는 7.18.0부터다. 7.18.0을 설치한 뒤 재검사하자 [GHSA-qwww-vcr4-c8h2](https://github.com/remix-run/react-router/security/advisories/GHSA-qwww-vcr4-c8h2)가 남아, 해당 수정 버전인 7.18.2로 최종 선택했다. 이 앱은 SSR/RSC를 사용하지 않으며 외부 입력을 navigation URL로 그대로 전달하는 경로도 확인되지 않았다. major 전환은 알려진 dependency 경고를 제거하기 위한 선택이며, 기존 앱에서 공격을 재현했다는 의미는 아니다.

## 공지별 수정 범위와 노출 조건

아래 수정 버전은 maintainer 공지와 GitHub 공식 advisory DB/API의 현재 npm 범위를 확인한 결과다. maintainer 공지 페이지가 없는 항목은 GitHub advisory DB로 연결한다. 초기 audit에 직접 포함된 21개 공지와 갱신 중 확인된 RSC 공지를 기록한다. 공지의 심각도와 npm audit의 집계 심각도는 다를 수 있다.

| 경로 | 공식 공지 | 해당 계열 최초 수정 | 조건 및 현재 앱에서의 판단 |
| --- | --- | --- | --- |
| plugin-react → Babel | [4x5r-pxfx-6jf8](https://github.com/babel/babel/security/advisories/GHSA-4x5r-pxfx-6jf8) | core 7.29.6 | 공격자가 소스·sourceMappingURL을 제어하고 변환 출력을 읽어야 한다. PDF는 Babel 입력으로 사용하지 않는다. |
| Babel → browserslist → baseline | [w5vr-8v7q-w6rv](https://github.com/advisories/GHSA-w5vr-8v7q-w6rv) | 2.11.0 | 잘못된 옵션 입력으로 process 종료. 앱이 브라우저 대상 옵션을 외부 입력으로 받지 않는다. |
| Babel → browserslist | [c83g-rgw3-j3cx](https://github.com/browserslist/browserslist/security/advisories/GHSA-c83g-rgw3-j3cx) | 4.28.7 | 다양한 외부 query를 장시간 처리할 때 cache 증가. 고정된 로컬 빌드 경로다. |
| Babel → browserslist | [73wf-gq98-2v4g](https://github.com/browserslist/browserslist/security/advisories/GHSA-73wf-gq98-2v4g) | 4.28.7 | 신뢰하지 않는 custom stats 파일/옵션이 필요하다. 업로드 도면을 stats로 쓰지 않는다. |
| Vite → esbuild | [g7r4-m6w7-qqqr](https://github.com/evanw/esbuild/security/advisories/GHSA-g7r4-m6w7-qqqr) | 0.28.1 | Windows esbuild `serve/servedir`. 앱은 esbuild의 독립 serve API를 사용하지 않는다. |
| Vite → PostCSS → nanoid | [28wg-ghj8-5hjv](https://github.com/advisories/GHSA-28wg-ghj8-5hjv) | 3.3.16 | non-secure generator에 외부 음수 size가 들어가야 한다. 앱에 직접 generator 호출이 없다. |
| Vite → PostCSS → nanoid | [2v37-7h3g-55p8](https://github.com/advisories/GHSA-2v37-7h3g-55p8) | 3.3.18 | custom generator의 size 0. 앱이 size를 입력받지 않는다. |
| Vite → PostCSS | [r28c-9q8g-f849](https://github.com/postcss/postcss/security/advisories/GHSA-r28c-9q8g-f849) | 8.5.18 | 공격자 CSS의 sourceMappingURL을 처리하고 map 출력을 노출하는 경우. 앱은 업로드 PDF를 CSS로 처리하지 않는다. |
| Vite → PostCSS | [fxqj-rqcc-2cmp](https://github.com/postcss/postcss/security/advisories/GHSA-fxqj-rqcc-2cmp) | 8.5.23 | `from` 미설정 때 이전 map 경로 검사 누락. 위와 같은 빌드 입력 조건이다. |
| Vite → PostCSS → source-map-js | [68fv-2mgg-jv7q](https://github.com/advisories/GHSA-68fv-2mgg-jv7q) | 1.2.2 | 공격자가 indexed source map offset을 제어해야 한다. 앱은 이를 외부 입력으로 받지 않는다. |
| Router | [2j2x-hqr9-3h42](https://github.com/remix-run/react-router/security/advisories/GHSA-2j2x-hqr9-3h42) | router 6.30.4 / 7.14.1, remix router 1.23.3 | untrusted redirect URL. 공식 공지상 BrowserRouter Declarative Mode는 영향 없음. |
| Router | [jjmj-jmhj-qwj2](https://github.com/remix-run/react-router/security/advisories/GHSA-jjmj-jmhj-qwj2) | DOM 6.30.6 / router 7.13.0 | 앱에 open redirect가 있어야 한다. 현재 링크는 고정 내부 경로와 숫자 ID다. |
| Router | [wrjc-x8rr-h8h6](https://github.com/remix-run/react-router/security/advisories/GHSA-wrjc-x8rr-h8h6) | 7.18.0 | 공격자 경로가 navigation에 전달돼야 한다. 현재 해당 경로를 확인하지 못했다. |
| Router | [337j-9hxr-rhxg](https://github.com/remix-run/react-router/security/advisories/GHSA-337j-9hxr-rhxg) | 7.18.0 | 특정 SSR 오류 hydration 코드. 앱은 SSR/hydration을 사용하지 않는다. |
| Router (갱신 중 확인) | [qwww-vcr4-c8h2](https://github.com/remix-run/react-router/security/advisories/GHSA-qwww-vcr4-c8h2) | 7.18.2 | unstable RSC API에 한정. 앱에 RSC가 없다. |
| Vite 내장 launch-editor | [v6wh-96g9-6wx3](https://github.com/vitejs/launch-editor/security/advisories/GHSA-v6wh-96g9-6wx3) | Vite 7.3.5 | Windows/NTLM 활성, middleware 실행 중 악성 사이트의 요청 등 조건. loopback 사용만으로 이 문제를 배제하지 않는다. |
| Vite 내장 launch-editor | [698v-4r3x-3vcv](https://github.com/vitejs/launch-editor/security/advisories/GHSA-698v-4r3x-3vcv) | Vite 7.3.7 | Windows의 악성 파일명·환경변수/ADS 조합과 editor 호출. 수정된 내장 코드를 사용한다. |
| Vite 내장 launch-editor | [r825-w8mm-5pxw](https://github.com/vitejs/launch-editor/security/advisories/GHSA-r825-w8mm-5pxw) | Vite 7.3.7 | 특정 editor, 공격자 파일, Vite 사용 시 WSL 등의 조건. 사용하지 않는 editor라고 패치를 생략하지 않았다. |
| Vite 내장 launch-editor | [587h-7wmj-h5pm](https://github.com/vitejs/launch-editor/security/advisories/GHSA-587h-7wmj-h5pm) | Vite 7.3.7 | Windows 경로 검사 우회로 기존 파일 조건이 완화된다. 위 % escaping 문제와 결합 가능하다. |
| Vite | [9jrq-w75r-8gcw](https://github.com/vitejs/vite/security/advisories/GHSA-9jrq-w75r-8gcw) | 7.3.7 | custom middleware의 URL 전달 및 inline module 등의 조건. 앱은 기본 SPA 설정이다. |
| Vite | [rq7h-c2jc-7f22](https://github.com/vitejs/vite/security/advisories/GHSA-rq7h-c2jc-7f22) | 7.3.7 | 비Windows, 네트워크 노출, host 절대 경로와 같은 import 등의 조건. 현재 Windows 로컬 실행과 구분한다. |
| Vite | [fx2h-pf6j-xcff](https://github.com/vitejs/vite/security/advisories/GHSA-fx2h-pf6j-xcff) | 7.3.5 | 네트워크 노출 및 NTFS/8.3 경로 등의 조건. 현재 외부 host 설정 없이 로컬에서 사용한다. |

## 검증 기록

Windows, Node `24.14.0`, npm `11.9.0`에서 별도 clone에 설치했다.

| 검사 | 결과 |
| --- | --- |
| 변경 전 `npm ci`, `npm test` | 설치 성공, 기존 UI 26개 통과 |
| 갱신 lock으로 `npm ci` | 성공, audit 0 |
| `npm test` | 기존 26개 + 라우팅 4개 = 30개 통과 |
| `npm run build` | TypeScript 검사 및 Vite production build 통과 |
| `npm audit --json`, `npm audit --omit=dev --json` | 모두 exit 0, 모든 severity 0 |
| `npm ls` | Router/Vite 및 관련 전이 의존성 정상 연결, 강제 override 없음 |
| Python 3.11.9 `scripts/doctor.py` | 필수 운영 파일 정상, hook 미설정. 설정 점검이며 Python 테스트 실행은 아님 |
| 라이선스 대조 | npm 187개 lock entry를 재생성. Python 구간 보존. 새 runtime cookie/set-cookie-parser는 MIT 원문, baseline은 Apache-2.0 원문, caniuse-lite는 CC-BY-4.0 원문 확인 |

`src/test/routing.test.tsx`는 실제 `App`과 페이지를 MemoryRouter에서 렌더링하고 API 응답만 대체한다. 기본/미등록 경로의 업로드 이동, 네 메뉴와 활성 메뉴, 뒤로/앞으로, 도면 상세 ID·page 0→3 전환, 목록 링크의 `drawingFileId` query 보존을 검증한다. 기존 26개는 계산·측정·검수 상태의 회귀를 확인한다.

Playwright CLI의 별도 `takeoff-f12` Chromium 세션에서 Vite dev server를 `127.0.0.1:5182`로 실행했다. 네 메뉴, history 뒤로/앞으로, `/drawings/42/pages/0` 직접 진입, Page Index 3 이동, 이미지 URL/표시 변경, 목록 query와 입력값 보존, 미등록 경로의 `/upload` 이동을 확인했다. 상세 페이지의 screenshot도 시각 확인했다. API·이미지는 빈 합성 JSON/SVG로 대체했다. fixture 설정 후 수집한 pageerror와 console error는 0이다. 최초 fixture 설정 전에는 미실행 API에 대한 500 및 favicon 404가 기록됐으며 이 로그를 앱 회귀로 집계하지 않았다.

브라우저 smoke는 프런트엔드 라우팅 확인이다. 실제 API 통합, PDF 추출, 파일 업로드, Excel export 전체 E2E나 실무 물량 정확도 검증은 수행하지 않았다. Python 파일·패키지를 변경하지 않아 Python 테스트는 이 PR에서 실행하지 않았다. `npm ci`의 기존 `whatwg-encoding` deprecated 안내는 남지만 현재 audit advisory는 없다.

## 라이선스와 남은 한계

[라이선스 스냅샷](DEPENDENCY_LICENSES.md)의 npm 구간만 현재 lock과 맞췄다. caniuse-lite의 CC-BY-4.0 버전 고지는 [THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md)에서 갱신했다. 패키지·빌드 산출물은 저장소에 포함하지 않는다. 실제 bundle 배포 때 필요한 원문 고지 수집은 기존 라이선스 정책을 따른다.

현재 audit 잔여 경로는 없다. 향후 advisory·registry metadata는 바뀔 수 있으므로 공개/배포 전에 위 두 audit 명령을 재실행한다. Router major 변경의 확인 범위는 자동 회귀와 합성 응답 브라우저 smoke까지이며 실제 도면 데이터로 전체 업무 흐름을 검증했다는 주장은 하지 않는다.
