#!/usr/bin/env bash
# vendor/ 의 라이브러리를 npm 레지스트리에서 다시 받아 교체한다.
# 버전을 올릴 때만 쓰면 된다. 평소에는 커밋된 vendor/ 를 그대로 쓴다.
# 필요: npm, tar
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VENDOR="$ROOT/vendor"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

LEAFLET=1.9.4
EXIFR=7.1.3
PIEXIF=1.0.6
JSZIP=3.10.1
HEIC2ANY=0.0.4

cd "$TMP"
for spec in "leaflet@$LEAFLET" "exifr@$EXIFR" "piexifjs@$PIEXIF" "jszip@$JSZIP" "heic2any@$HEIC2ANY"; do
  npm pack --silent "$spec" >/dev/null
done
for f in *.tgz; do d="${f%.tgz}"; mkdir -p "$d"; tar xzf "$f" -C "$d"; done

mkdir -p "$VENDOR/licenses"
cp "leaflet-$LEAFLET/package/dist/leaflet.js"      "$VENDOR/leaflet.js"
cp "leaflet-$LEAFLET/package/dist/leaflet.css"     "$VENDOR/leaflet.css"
cp "exifr-$EXIFR/package/dist/full.umd.js"         "$VENDOR/exifr.full.umd.js"
cp "piexifjs-$PIEXIF/package/piexif.js"            "$VENDOR/piexif.js"
cp "jszip-$JSZIP/package/dist/jszip.min.js"        "$VENDOR/jszip.min.js"
cp "heic2any-$HEIC2ANY/package/dist/heic2any.min.js" "$VENDOR/heic2any.min.js"

cp "leaflet-$LEAFLET/package/LICENSE"              "$VENDOR/licenses/leaflet-LICENSE.txt"
cp "exifr-$EXIFR/package/LICENSE"                  "$VENDOR/licenses/exifr-LICENSE.txt"
cp "piexifjs-$PIEXIF/package/LICENSE.txt"          "$VENDOR/licenses/piexifjs-LICENSE.txt"
cp "jszip-$JSZIP/package/LICENSE.markdown"         "$VENDOR/licenses/jszip-LICENSE.md"
cp "heic2any-$HEIC2ANY/package/LICENSE.md"         "$VENDOR/licenses/heic2any-LICENSE.md"

cd "$VENDOR" && sha256sum *.js *.css > SHA256SUMS
echo "vendor/ updated. 버전을 바꿨다면 scripts/build.py 의 LIBS 주석과 THIRD_PARTY_NOTICES.md 도 고칠 것."
