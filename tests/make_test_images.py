#!/usr/bin/env python3
"""E2E 테스트용 사진을 tests/fixtures/ 에 만든다 (실제 사진 아님).

- P0~P4.jpg : 촬영 시각 + GPS (P4는 새벽 01:30 → 하루 시작 04시 기준으로 전날에 들어가야 함)
- P5.jpg    : 촬영 시각만 있고 GPS 없음
- P9.png    : EXIF 없음 (파일 수정 시각으로 대체되는지 확인)
- H1.heic   : HEIC + 촬영 시각 + GPS (exifr가 컨테이너를 못 읽을 때의 대비 경로 확인)

필요: pip install pillow piexif pillow-heif
"""
from pathlib import Path

import piexif
import pillow_heif
from PIL import Image, ImageDraw

pillow_heif.register_heif_opener()
OUT = Path(__file__).resolve().parent / "fixtures"


def dms(v):
    v = abs(v)
    d = int(v)
    m = int((v - d) * 60)
    s = round(((v - d) * 60 - m) * 60 * 100)
    return ((d, 1), (m, 1), (s, 100))


def exif_bytes(t, lat=None, lng=None):
    gps = {}
    if lat is not None:
        gps = {
            piexif.GPSIFD.GPSLatitudeRef: "N" if lat >= 0 else "S",
            piexif.GPSIFD.GPSLatitude: dms(lat),
            piexif.GPSIFD.GPSLongitudeRef: "E" if lng >= 0 else "W",
            piexif.GPSIFD.GPSLongitude: dms(lng),
        }
    return piexif.dump({"0th": {}, "Exif": {piexif.ExifIFD.DateTimeOriginal: t}, "GPS": gps})


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    jpgs = [
        ("2026:09:12 09:10:00", 41.8902, 12.4922),
        ("2026:09:12 09:25:00", 41.8905, 12.4925),
        ("2026:09:12 10:40:00", 41.8925, 12.4853),
        ("2026:09:12 13:00:00", 41.8986, 12.4769),
        ("2026:09:13 01:30:00", 41.9009, 12.4833),
        ("2026:09:13 10:00:00", None, None),
    ]
    for i, (t, lat, lng) in enumerate(jpgs):
        im = Image.new("RGB", (1600, 1200), (40 + i * 30, 90, 140))
        ImageDraw.Draw(im).text((50, 50), t, fill="white")
        im.save(OUT / f"P{i}.jpg", exif=exif_bytes(t, lat, lng))

    Image.new("RGB", (800, 600), (200, 100, 50)).save(OUT / "P9.png")
    Image.new("RGB", (1200, 900), (30, 120, 60)).save(
        OUT / "H1.heic", exif=exif_bytes("2026:09:14 11:00:00", 43.7731, 11.2560)
    )
    print(f"fixtures written to {OUT}")


if __name__ == "__main__":
    main()
