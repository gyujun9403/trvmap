#!/usr/bin/env python3
"""src/index.html 에 vendor/ 라이브러리를 인라인해서 dist/사진동선지도.html 한 파일로 만든다.

사용법: python3 scripts/build.py
외부 패키지 필요 없음 (표준 라이브러리만 사용).
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src" / "index.html"
VENDOR = ROOT / "vendor"
OUT = ROOT / "dist" / "사진동선지도.html"

# 로드 순서 중요: Leaflet → exifr → piexif → JSZip → heic2any
LIBS = [
    ("Leaflet 1.9.4 (BSD-2-Clause)", "leaflet.js"),
    ("exifr 7.1.3 (MIT)", "exifr.full.umd.js"),
    ("piexifjs 1.0.6 (MIT)", "piexif.js"),
    ("JSZip 3.10.1 (MIT OR GPL-3.0-or-later)", "jszip.min.js"),
    ("heic2any 0.0.4 (MIT, bundles libheif)", "heic2any.min.js"),
]

CSS_MARK = "/*__LEAFLET_CSS__*/"
JS_MARK = "<!--__VENDOR__-->"


def main() -> int:
    src = SRC.read_text(encoding="utf-8")
    for mark in (CSS_MARK, JS_MARK):
        if src.count(mark) != 1:
            print(f"error: {SRC} 에 {mark} 가 정확히 1번 있어야 합니다", file=sys.stderr)
            return 1

    css = (VENDOR / "leaflet.css").read_text(encoding="utf-8")
    parts = []
    for name, fname in LIBS:
        js = (VENDOR / fname).read_text(encoding="utf-8")
        if "</script" in js.lower():
            print(f"error: {fname} 안에 </script 가 있어 인라인할 수 없습니다", file=sys.stderr)
            return 1
        parts.append(f"<script>/* {name} */\n{js}\n</script>")

    out = src.replace(CSS_MARK, css).replace(JS_MARK, "\n".join(parts))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(out, encoding="utf-8")
    print(f"built {OUT.relative_to(ROOT)} ({OUT.stat().st_size / 1e6:.2f} MB)")

    # GitHub Pages 등 정적 호스팅 배포용으로 같은 내용을 index.html 로도 출력 (연동 기능은 https 호스팅 필요)
    index = OUT.parent / "index.html"
    index.write_text(out, encoding="utf-8")
    print(f"built {index.relative_to(ROOT)} (동일 내용, Pages 배포용)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
