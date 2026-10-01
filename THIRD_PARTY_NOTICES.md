# Third-party notices

`dist/사진동선지도.html` 에는 아래 라이브러리가 인라인되어 있습니다. 원본 파일은 `vendor/`, 라이선스 원문은 `vendor/licenses/` 에 있습니다. 모두 npm 레지스트리 패키지에서 수정 없이 가져왔습니다 (`vendor/SHA256SUMS`).

| 라이브러리 | 버전 | 파일 | 라이선스 (package.json 기준) | 원문 |
|---|---|---|---|---|
| [Leaflet](https://leafletjs.com/) | 1.9.4 | `leaflet.js`, `leaflet.css` | BSD-2-Clause | `licenses/leaflet-LICENSE.txt` |
| [exifr](https://github.com/MikeKovarik/exifr) | 7.1.3 | `dist/full.umd.js` → `exifr.full.umd.js` | MIT | `licenses/exifr-LICENSE.txt` |
| [piexifjs](https://github.com/hMatoba/piexifjs) | 1.0.6 | `piexif.js` | MIT | `licenses/piexifjs-LICENSE.txt` |
| [JSZip](https://stuk.github.io/jszip/) | 3.10.1 | `dist/jszip.min.js` | MIT OR GPL-3.0-or-later (여기서는 MIT 선택) | `licenses/jszip-LICENSE.md` |
| [heic2any](https://github.com/alexcorvi/heic2any) | 0.0.4 | `dist/heic2any.min.js` | MIT | `licenses/heic2any-LICENSE.md` |

## heic2any 안의 libheif

`heic2any.min.js` 번들에는 HEIC 디코더인 [libheif](https://github.com/strukturag/libheif)가 컴파일된 형태로 포함되어 있습니다 (번들 안에 `libheif.HeifDecoder` 호출이 있음). heic2any 자체는 MIT지만, libheif 업스트림은 LGPL-3.0 입니다. 개인 사용에는 문제가 없고, 저장소를 공개하거나 배포할 경우 LGPL 조건(라이브러리 교체 가능성, 소스 제공 방법 고지 등)을 확인하세요. 번들을 분리해 두는 것(`vendor/heic2any.min.js` 를 별도 파일로 로드)이 LGPL 조건을 맞추기 쉽습니다.

## 실행 중 사용하는 외부 서비스 (코드 포함 아님)

- 지도 타일: Esri World Street Map, Esri World Imagery (데이터 © Esri 및 각 데이터 제공자, © OpenStreetMap contributors)
- 글꼴: Google Fonts — IBM Plex Sans KR, IBM Plex Mono (SIL Open Font License 1.1)
- 구글 로그인: Google Identity Services (`accounts.google.com/gsi/client`) — 연동 기능을 켰을 때만 원격으로 로드. 인라인하지 않음(OAuth 특성상 구글 도메인에서 받아야 함).
- 구글드라이브 API (`www.googleapis.com`) — 연동을 켰을 때만, 사용자 본인 드라이브에 사진·메모를 저장/조회.

각 서비스의 저작권 표기는 지도 오른쪽 아래에 표시됩니다.
