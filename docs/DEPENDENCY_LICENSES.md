# 의존성 라이선스 스냅샷

확인일: 2026-11-04. 원본 소스와 외부 의존성의 라이선스는 구분한다. 아래 라이선스 표기는 각 버전의 배포 metadata/lockfile 선언을 기록한 것이며 전체 코드의 라이선스 감사를 대신하지 않는다.

## Python

Python 3.11.9 / Windows에서 설치한 API runtime 및 dev 의존성의 현재 플랫폼 dependency closure다. `apps/api/pyproject.toml`의 runtime/dev와 uvicorn standard extras를 따라 수집했다. pip/setuptools 등 환경 관리 도구는 제외했다. 버전 고정 파일이 아니며 다른 플랫폼의 조건부 의존성이나 이후 설치 결과는 달라질 수 있다.

| 배포 패키지 | 확인 버전 | 선언 라이선스 | 원본 metadata |
| --- | --- | --- | --- |
| annotated-doc | 0.0.5 | MIT | [PyPI](https://pypi.org/project/annotated-doc/0.0.5/) |
| annotated-types | 0.8.0 | MIT | [PyPI](https://pypi.org/project/annotated-types/0.8.0/) |
| anyio | 4.15.1 | MIT | [PyPI](https://pypi.org/project/anyio/4.15.1/) |
| certifi | 2026.10.19 | MPL-2.0 | [PyPI](https://pypi.org/project/certifi/2026.10.19/) |
| click | 8.5.0 | BSD-3-Clause | [PyPI](https://pypi.org/project/click/8.5.0/) |
| colorama | 0.4.6 | BSD-3-Clause (installed LICENSE.txt verified) | [PyPI](https://pypi.org/project/colorama/0.4.6/) |
| et_xmlfile | 2.0.0 | MIT | [PyPI](https://pypi.org/project/et_xmlfile/2.0.0/) |
| fastapi | 0.159.1 | MIT | [PyPI](https://pypi.org/project/fastapi/0.159.1/) |
| h11 | 0.16.0 | MIT | [PyPI](https://pypi.org/project/h11/0.16.0/) |
| httpcore | 1.0.9 | BSD-3-Clause | [PyPI](https://pypi.org/project/httpcore/1.0.9/) |
| httptools | 0.9.0 | MIT | [PyPI](https://pypi.org/project/httptools/0.9.0/) |
| httpx | 0.28.1 | BSD-3-Clause | [PyPI](https://pypi.org/project/httpx/0.28.1/) |
| idna | 3.20 | BSD-3-Clause | [PyPI](https://pypi.org/project/idna/3.20/) |
| iniconfig | 2.3.1 | MIT | [PyPI](https://pypi.org/project/iniconfig/2.3.1/) |
| openpyxl | 3.1.5 | MIT | [PyPI](https://pypi.org/project/openpyxl/3.1.5/) |
| opentelemetry-api | 1.45.1 | Apache-2.0 | [PyPI](https://pypi.org/project/opentelemetry-api/1.45.1/) |
| packaging | 26.3 | Apache-2.0 OR BSD-2-Clause | [PyPI](https://pypi.org/project/packaging/26.3/) |
| pluggy | 1.7.0 | MIT | [PyPI](https://pypi.org/project/pluggy/1.7.0/) |
| pydantic | 2.14.1 | MIT | [PyPI](https://pypi.org/project/pydantic/2.14.1/) |
| pydantic-settings | 2.16.1 | MIT | [PyPI](https://pypi.org/project/pydantic-settings/2.16.1/) |
| pydantic_core | 2.50.1 | MIT | [PyPI](https://pypi.org/project/pydantic_core/2.50.1/) |
| Pygments | 2.21.0 | BSD-2-Clause | [PyPI](https://pypi.org/project/Pygments/2.21.0/) |
| PyMuPDF | 1.27.2.3 | AGPL v3 / Artifex Commercial | [PyPI](https://pypi.org/project/PyMuPDF/1.27.2.3/) |
| pytest | 8.4.2 | MIT | [PyPI](https://pypi.org/project/pytest/8.4.2/) |
| python-dotenv | 1.2.4 | BSD-3-Clause | [PyPI](https://pypi.org/project/python-dotenv/1.2.4/) |
| python-multipart | 0.0.32 | Apache-2.0 | [PyPI](https://pypi.org/project/python-multipart/0.0.32/) |
| PyYAML | 6.0.3 | MIT | [PyPI](https://pypi.org/project/PyYAML/6.0.3/) |
| SQLAlchemy | 2.1.6 | MIT | [PyPI](https://pypi.org/project/SQLAlchemy/2.1.6/) |
| starlette | 1.9.0 | BSD-3-Clause | [PyPI](https://pypi.org/project/starlette/1.9.0/) |
| typing-inspection | 0.4.4 | MIT | [PyPI](https://pypi.org/project/typing-inspection/0.4.4/) |
| typing_extensions | 4.16.0 | PSF-2.0 | [PyPI](https://pypi.org/project/typing_extensions/4.16.0/) |
| uvicorn | 0.54.0 | BSD-3-Clause | [PyPI](https://pypi.org/project/uvicorn/0.54.0/) |
| watchfiles | 1.3.0 | MIT | [PyPI](https://pypi.org/project/watchfiles/1.3.0/) |
| websockets | 17.3 | BSD-3-Clause | [PyPI](https://pypi.org/project/websockets/17.3/) |

## npm

`apps/web/package-lock.json`의 모든 비루트 package entry를 포함한다. 중첩 설치와 플랫폼별 optional package도 각 경로별로 표시한다. 같은 이름의 다른 버전·경로를 합쳐 숨기지 않는다. 아래 표기는 lockfile의 `license` 필드에서 수집했다. 실제 배포 전에는 해당 버전의 배포 tarball에 있는 LICENSE/NOTICE 원문도 확인해야 한다.

| 패키지 | 버전 | 선언 라이선스 | 구분 | lockfile 경로 |
| --- | --- | --- | --- | --- |
| @asamuzakjp/css-color | 3.2.0 | MIT | dev | `node_modules/@asamuzakjp/css-color` |
| lru-cache | 10.4.3 | ISC | dev | `node_modules/@asamuzakjp/css-color/node_modules/lru-cache` |
| @babel/code-frame | 7.29.0 | MIT | dev | `node_modules/@babel/code-frame` |
| @babel/compat-data | 7.29.3 | MIT | dev | `node_modules/@babel/compat-data` |
| @babel/core | 7.29.0 | MIT | dev | `node_modules/@babel/core` |
| @babel/generator | 7.29.1 | MIT | dev | `node_modules/@babel/generator` |
| @babel/helper-compilation-targets | 7.28.6 | MIT | dev | `node_modules/@babel/helper-compilation-targets` |
| @babel/helper-globals | 7.28.0 | MIT | dev | `node_modules/@babel/helper-globals` |
| @babel/helper-module-imports | 7.28.6 | MIT | dev | `node_modules/@babel/helper-module-imports` |
| @babel/helper-module-transforms | 7.28.6 | MIT | dev | `node_modules/@babel/helper-module-transforms` |
| @babel/helper-plugin-utils | 7.28.6 | MIT | dev | `node_modules/@babel/helper-plugin-utils` |
| @babel/helper-string-parser | 7.27.1 | MIT | dev | `node_modules/@babel/helper-string-parser` |
| @babel/helper-validator-identifier | 7.28.5 | MIT | dev | `node_modules/@babel/helper-validator-identifier` |
| @babel/helper-validator-option | 7.27.1 | MIT | dev | `node_modules/@babel/helper-validator-option` |
| @babel/helpers | 7.29.2 | MIT | dev | `node_modules/@babel/helpers` |
| @babel/parser | 7.29.3 | MIT | dev | `node_modules/@babel/parser` |
| @babel/plugin-transform-react-jsx-self | 7.27.1 | MIT | dev | `node_modules/@babel/plugin-transform-react-jsx-self` |
| @babel/plugin-transform-react-jsx-source | 7.27.1 | MIT | dev | `node_modules/@babel/plugin-transform-react-jsx-source` |
| @babel/runtime | 7.29.10 | MIT | dev | `node_modules/@babel/runtime` |
| @babel/template | 7.28.6 | MIT | dev | `node_modules/@babel/template` |
| @babel/traverse | 7.29.0 | MIT | dev | `node_modules/@babel/traverse` |
| @babel/types | 7.29.0 | MIT | dev | `node_modules/@babel/types` |
| @csstools/color-helpers | 5.1.0 | MIT-0 | dev | `node_modules/@csstools/color-helpers` |
| @csstools/css-calc | 2.1.4 | MIT | dev | `node_modules/@csstools/css-calc` |
| @csstools/css-color-parser | 3.1.0 | MIT | dev | `node_modules/@csstools/css-color-parser` |
| @csstools/css-parser-algorithms | 3.0.5 | MIT | dev | `node_modules/@csstools/css-parser-algorithms` |
| @csstools/css-tokenizer | 3.0.4 | MIT | dev | `node_modules/@csstools/css-tokenizer` |
| @esbuild/aix-ppc64 | 0.27.7 | MIT | dev | `node_modules/@esbuild/aix-ppc64` |
| @esbuild/android-arm | 0.27.7 | MIT | dev | `node_modules/@esbuild/android-arm` |
| @esbuild/android-arm64 | 0.27.7 | MIT | dev | `node_modules/@esbuild/android-arm64` |
| @esbuild/android-x64 | 0.27.7 | MIT | dev | `node_modules/@esbuild/android-x64` |
| @esbuild/darwin-arm64 | 0.27.7 | MIT | dev | `node_modules/@esbuild/darwin-arm64` |
| @esbuild/darwin-x64 | 0.27.7 | MIT | dev | `node_modules/@esbuild/darwin-x64` |
| @esbuild/freebsd-arm64 | 0.27.7 | MIT | dev | `node_modules/@esbuild/freebsd-arm64` |
| @esbuild/freebsd-x64 | 0.27.7 | MIT | dev | `node_modules/@esbuild/freebsd-x64` |
| @esbuild/linux-arm | 0.27.7 | MIT | dev | `node_modules/@esbuild/linux-arm` |
| @esbuild/linux-arm64 | 0.27.7 | MIT | dev | `node_modules/@esbuild/linux-arm64` |
| @esbuild/linux-ia32 | 0.27.7 | MIT | dev | `node_modules/@esbuild/linux-ia32` |
| @esbuild/linux-loong64 | 0.27.7 | MIT | dev | `node_modules/@esbuild/linux-loong64` |
| @esbuild/linux-mips64el | 0.27.7 | MIT | dev | `node_modules/@esbuild/linux-mips64el` |
| @esbuild/linux-ppc64 | 0.27.7 | MIT | dev | `node_modules/@esbuild/linux-ppc64` |
| @esbuild/linux-riscv64 | 0.27.7 | MIT | dev | `node_modules/@esbuild/linux-riscv64` |
| @esbuild/linux-s390x | 0.27.7 | MIT | dev | `node_modules/@esbuild/linux-s390x` |
| @esbuild/linux-x64 | 0.27.7 | MIT | dev | `node_modules/@esbuild/linux-x64` |
| @esbuild/netbsd-arm64 | 0.27.7 | MIT | dev | `node_modules/@esbuild/netbsd-arm64` |
| @esbuild/netbsd-x64 | 0.27.7 | MIT | dev | `node_modules/@esbuild/netbsd-x64` |
| @esbuild/openbsd-arm64 | 0.27.7 | MIT | dev | `node_modules/@esbuild/openbsd-arm64` |
| @esbuild/openbsd-x64 | 0.27.7 | MIT | dev | `node_modules/@esbuild/openbsd-x64` |
| @esbuild/openharmony-arm64 | 0.27.7 | MIT | dev | `node_modules/@esbuild/openharmony-arm64` |
| @esbuild/sunos-x64 | 0.27.7 | MIT | dev | `node_modules/@esbuild/sunos-x64` |
| @esbuild/win32-arm64 | 0.27.7 | MIT | dev | `node_modules/@esbuild/win32-arm64` |
| @esbuild/win32-ia32 | 0.27.7 | MIT | dev | `node_modules/@esbuild/win32-ia32` |
| @esbuild/win32-x64 | 0.27.7 | MIT | dev | `node_modules/@esbuild/win32-x64` |
| @jridgewell/gen-mapping | 0.3.13 | MIT | dev | `node_modules/@jridgewell/gen-mapping` |
| @jridgewell/remapping | 2.3.5 | MIT | dev | `node_modules/@jridgewell/remapping` |
| @jridgewell/resolve-uri | 3.1.2 | MIT | dev | `node_modules/@jridgewell/resolve-uri` |
| @jridgewell/sourcemap-codec | 1.6.0 | MIT | dev | `node_modules/@jridgewell/sourcemap-codec` |
| @jridgewell/trace-mapping | 0.3.31 | MIT | dev | `node_modules/@jridgewell/trace-mapping` |
| @remix-run/router | 1.23.2 | MIT | runtime | `node_modules/@remix-run/router` |
| @rolldown/pluginutils | 1.0.0-rc.3 | MIT | dev | `node_modules/@rolldown/pluginutils` |
| @rollup/rollup-android-arm-eabi | 4.60.2 | MIT | dev | `node_modules/@rollup/rollup-android-arm-eabi` |
| @rollup/rollup-android-arm64 | 4.60.2 | MIT | dev | `node_modules/@rollup/rollup-android-arm64` |
| @rollup/rollup-darwin-arm64 | 4.60.2 | MIT | dev | `node_modules/@rollup/rollup-darwin-arm64` |
| @rollup/rollup-darwin-x64 | 4.60.2 | MIT | dev | `node_modules/@rollup/rollup-darwin-x64` |
| @rollup/rollup-freebsd-arm64 | 4.60.2 | MIT | dev | `node_modules/@rollup/rollup-freebsd-arm64` |
| @rollup/rollup-freebsd-x64 | 4.60.2 | MIT | dev | `node_modules/@rollup/rollup-freebsd-x64` |
| @rollup/rollup-linux-arm-gnueabihf | 4.60.2 | MIT | dev | `node_modules/@rollup/rollup-linux-arm-gnueabihf` |
| @rollup/rollup-linux-arm-musleabihf | 4.60.2 | MIT | dev | `node_modules/@rollup/rollup-linux-arm-musleabihf` |
| @rollup/rollup-linux-arm64-gnu | 4.60.2 | MIT | dev | `node_modules/@rollup/rollup-linux-arm64-gnu` |
| @rollup/rollup-linux-arm64-musl | 4.60.2 | MIT | dev | `node_modules/@rollup/rollup-linux-arm64-musl` |
| @rollup/rollup-linux-loong64-gnu | 4.60.2 | MIT | dev | `node_modules/@rollup/rollup-linux-loong64-gnu` |
| @rollup/rollup-linux-loong64-musl | 4.60.2 | MIT | dev | `node_modules/@rollup/rollup-linux-loong64-musl` |
| @rollup/rollup-linux-ppc64-gnu | 4.60.2 | MIT | dev | `node_modules/@rollup/rollup-linux-ppc64-gnu` |
| @rollup/rollup-linux-ppc64-musl | 4.60.2 | MIT | dev | `node_modules/@rollup/rollup-linux-ppc64-musl` |
| @rollup/rollup-linux-riscv64-gnu | 4.60.2 | MIT | dev | `node_modules/@rollup/rollup-linux-riscv64-gnu` |
| @rollup/rollup-linux-riscv64-musl | 4.60.2 | MIT | dev | `node_modules/@rollup/rollup-linux-riscv64-musl` |
| @rollup/rollup-linux-s390x-gnu | 4.60.2 | MIT | dev | `node_modules/@rollup/rollup-linux-s390x-gnu` |
| @rollup/rollup-linux-x64-gnu | 4.60.2 | MIT | dev | `node_modules/@rollup/rollup-linux-x64-gnu` |
| @rollup/rollup-linux-x64-musl | 4.60.2 | MIT | dev | `node_modules/@rollup/rollup-linux-x64-musl` |
| @rollup/rollup-openbsd-x64 | 4.60.2 | MIT | dev | `node_modules/@rollup/rollup-openbsd-x64` |
| @rollup/rollup-openharmony-arm64 | 4.60.2 | MIT | dev | `node_modules/@rollup/rollup-openharmony-arm64` |
| @rollup/rollup-win32-arm64-msvc | 4.60.2 | MIT | dev | `node_modules/@rollup/rollup-win32-arm64-msvc` |
| @rollup/rollup-win32-ia32-msvc | 4.60.2 | MIT | dev | `node_modules/@rollup/rollup-win32-ia32-msvc` |
| @rollup/rollup-win32-x64-gnu | 4.60.2 | MIT | dev | `node_modules/@rollup/rollup-win32-x64-gnu` |
| @rollup/rollup-win32-x64-msvc | 4.60.2 | MIT | dev | `node_modules/@rollup/rollup-win32-x64-msvc` |
| @testing-library/dom | 10.4.2 | MIT | dev | `node_modules/@testing-library/dom` |
| @testing-library/react | 16.3.3 | MIT | dev | `node_modules/@testing-library/react` |
| @types/aria-query | 5.0.4 | MIT | dev | `node_modules/@types/aria-query` |
| @types/babel__core | 7.20.5 | MIT | dev | `node_modules/@types/babel__core` |
| @types/babel__generator | 7.27.0 | MIT | dev | `node_modules/@types/babel__generator` |
| @types/babel__template | 7.4.4 | MIT | dev | `node_modules/@types/babel__template` |
| @types/babel__traverse | 7.28.0 | MIT | dev | `node_modules/@types/babel__traverse` |
| @types/chai | 5.2.3 | MIT | dev | `node_modules/@types/chai` |
| @types/deep-eql | 4.0.2 | MIT | dev | `node_modules/@types/deep-eql` |
| @types/estree | 1.0.8 | MIT | dev | `node_modules/@types/estree` |
| @types/react | 19.2.14 | MIT | dev | `node_modules/@types/react` |
| @types/react-dom | 19.2.3 | MIT | dev | `node_modules/@types/react-dom` |
| @vitejs/plugin-react | 5.2.0 | MIT | dev | `node_modules/@vitejs/plugin-react` |
| @vitest/mocker | 5.0.5 | MIT | dev | `node_modules/@vitest/mocker` |
| @vitest/spy | 5.0.5 | MIT | dev | `node_modules/@vitest/spy` |
| agent-base | 7.1.4 | MIT | dev | `node_modules/agent-base` |
| ansi-regex | 5.0.1 | MIT | dev | `node_modules/ansi-regex` |
| ansi-styles | 5.2.0 | MIT | dev | `node_modules/ansi-styles` |
| aria-query | 5.3.0 | Apache-2.0 | dev | `node_modules/aria-query` |
| assertion-error | 2.0.1 | MIT | dev | `node_modules/assertion-error` |
| baseline-browser-mapping | 2.10.25 | Apache-2.0 | dev | `node_modules/baseline-browser-mapping` |
| browserslist | 4.28.2 | MIT | dev | `node_modules/browserslist` |
| caniuse-lite | 1.0.30001791 | CC-BY-4.0 | dev | `node_modules/caniuse-lite` |
| chai | 6.3.0 | MIT | dev | `node_modules/chai` |
| convert-source-map | 2.0.0 | MIT | dev | `node_modules/convert-source-map` |
| cssstyle | 4.6.0 | MIT | dev | `node_modules/cssstyle` |
| csstype | 3.2.3 | MIT | dev | `node_modules/csstype` |
| data-urls | 5.0.0 | MIT | dev | `node_modules/data-urls` |
| debug | 4.4.3 | MIT | dev | `node_modules/debug` |
| decimal.js | 10.6.0 | MIT | dev | `node_modules/decimal.js` |
| dequal | 2.0.3 | MIT | dev | `node_modules/dequal` |
| dom-accessibility-api | 0.5.16 | MIT | dev | `node_modules/dom-accessibility-api` |
| electron-to-chromium | 1.5.349 | ISC | dev | `node_modules/electron-to-chromium` |
| entities | 6.0.1 | BSD-2-Clause | dev | `node_modules/entities` |
| es-module-lexer | 2.3.2 | MIT | dev | `node_modules/es-module-lexer` |
| esbuild | 0.27.7 | MIT | dev | `node_modules/esbuild` |
| escalade | 3.2.0 | MIT | dev | `node_modules/escalade` |
| estree-walker | 3.0.3 | MIT | dev | `node_modules/estree-walker` |
| expect-type | 1.4.0 | Apache-2.0 | dev | `node_modules/expect-type` |
| fdir | 6.5.0 | MIT | dev | `node_modules/fdir` |
| fsevents | 2.3.3 | MIT | dev | `node_modules/fsevents` |
| gensync | 1.0.0-beta.2 | MIT | dev | `node_modules/gensync` |
| html-encoding-sniffer | 4.0.0 | MIT | dev | `node_modules/html-encoding-sniffer` |
| http-proxy-agent | 7.0.2 | MIT | dev | `node_modules/http-proxy-agent` |
| https-proxy-agent | 7.0.6 | MIT | dev | `node_modules/https-proxy-agent` |
| iconv-lite | 0.6.3 | MIT | dev | `node_modules/iconv-lite` |
| is-potential-custom-element-name | 1.0.1 | MIT | dev | `node_modules/is-potential-custom-element-name` |
| js-tokens | 4.0.0 | MIT | dev | `node_modules/js-tokens` |
| jsdom | 26.1.0 | MIT | dev | `node_modules/jsdom` |
| jsesc | 3.1.0 | MIT | dev | `node_modules/jsesc` |
| json5 | 2.2.3 | MIT | dev | `node_modules/json5` |
| lru-cache | 5.1.1 | ISC | dev | `node_modules/lru-cache` |
| lz-string | 1.5.0 | MIT | dev | `node_modules/lz-string` |
| magic-string | 1.4.3 | MIT | dev | `node_modules/magic-string` |
| ms | 2.1.3 | MIT | dev | `node_modules/ms` |
| nanoid | 3.3.12 | MIT | dev | `node_modules/nanoid` |
| node-releases | 2.0.38 | MIT | dev | `node_modules/node-releases` |
| nwsapi | 2.2.28 | MIT | dev | `node_modules/nwsapi` |
| obug | 3.0.0 | MIT | dev | `node_modules/obug` |
| parse5 | 7.3.0 | MIT | dev | `node_modules/parse5` |
| picocolors | 1.1.1 | ISC | dev | `node_modules/picocolors` |
| picomatch | 4.0.7 | MIT | dev | `node_modules/picomatch` |
| postcss | 8.5.13 | MIT | dev | `node_modules/postcss` |
| pretty-format | 27.5.1 | MIT | dev | `node_modules/pretty-format` |
| punycode | 2.3.1 | MIT | dev | `node_modules/punycode` |
| react | 19.2.5 | MIT | runtime | `node_modules/react` |
| react-dom | 19.2.5 | MIT | runtime | `node_modules/react-dom` |
| react-is | 17.0.2 | MIT | dev | `node_modules/react-is` |
| react-refresh | 0.18.0 | MIT | dev | `node_modules/react-refresh` |
| react-router | 6.30.3 | MIT | runtime | `node_modules/react-router` |
| react-router-dom | 6.30.3 | MIT | runtime | `node_modules/react-router-dom` |
| rollup | 4.60.2 | MIT | dev | `node_modules/rollup` |
| rrweb-cssom | 0.8.0 | MIT | dev | `node_modules/rrweb-cssom` |
| safer-buffer | 2.1.2 | MIT | dev | `node_modules/safer-buffer` |
| saxes | 6.0.0 | ISC | dev | `node_modules/saxes` |
| scheduler | 0.27.0 | MIT | runtime | `node_modules/scheduler` |
| semver | 6.3.1 | ISC | dev | `node_modules/semver` |
| source-map-js | 1.2.1 | BSD-3-Clause | dev | `node_modules/source-map-js` |
| std-env | 4.3.0 | MIT | dev | `node_modules/std-env` |
| symbol-tree | 3.2.4 | MIT | dev | `node_modules/symbol-tree` |
| tinybench | 6.2.2 | MIT | dev | `node_modules/tinybench` |
| tinyexec | 1.3.1 | MIT | dev | `node_modules/tinyexec` |
| tinyglobby | 0.2.17 | MIT | dev | `node_modules/tinyglobby` |
| tldts | 6.1.86 | MIT | dev | `node_modules/tldts` |
| tldts-core | 6.1.86 | MIT | dev | `node_modules/tldts-core` |
| tough-cookie | 5.1.2 | BSD-3-Clause | dev | `node_modules/tough-cookie` |
| tr46 | 5.1.1 | MIT | dev | `node_modules/tr46` |
| typescript | 5.9.3 | Apache-2.0 | dev | `node_modules/typescript` |
| update-browserslist-db | 1.2.3 | MIT | dev | `node_modules/update-browserslist-db` |
| vite | 7.3.2 | MIT | dev | `node_modules/vite` |
| vitest | 5.0.5 | MIT | dev | `node_modules/vitest` |
| w3c-xmlserializer | 5.0.0 | MIT | dev | `node_modules/w3c-xmlserializer` |
| webidl-conversions | 7.0.0 | BSD-2-Clause | dev | `node_modules/webidl-conversions` |
| whatwg-encoding | 3.1.1 | MIT | dev | `node_modules/whatwg-encoding` |
| whatwg-mimetype | 4.0.0 | MIT | dev | `node_modules/whatwg-mimetype` |
| whatwg-url | 14.2.0 | MIT | dev | `node_modules/whatwg-url` |
| why-is-node-running | 3.2.1 | MIT | dev | `node_modules/why-is-node-running` |
| ws | 8.22.0 | MIT | dev | `node_modules/ws` |
| xml-name-validator | 5.0.0 | Apache-2.0 | dev | `node_modules/xml-name-validator` |
| xmlchars | 2.2.0 | MIT | dev | `node_modules/xmlchars` |
| yallist | 3.1.1 | ISC | dev | `node_modules/yallist` |

확인한 범위: Python 34개 배포 패키지, npm 186개 lockfile entry. 라이선스가 자동 판별되지 않은 entry는 없다. 선언 문자열이 존재한다는 뜻이며 권리·호환성 보증은 아니다.

## 갱신과 배포

의존성을 바꾸면 이 목록과 `THIRD_PARTY_NOTICES.md`를 함께 검토한다. Python은 실제 배포 환경의 `importlib.metadata`, npm은 lockfile 및 설치된 각 package의 LICENSE/NOTICE를 확인한다. 직접 의존성만 검토하고 전이 의존성을 생략하지 않는다.

빌드 산출물·wheel·컨테이너·설치 패키지를 배포할 경우 실제 포함 버전의 원본 저작권·라이선스·NOTICE와 필요한 소스 제공 방식을 별도로 구성한다. 소스 저장소의 요약 표만으로 바이너리 배포 의무를 대체하지 않는다.
