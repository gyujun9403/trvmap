#!/usr/bin/env python3
"""E2E 테스트용 사진을 tests/fixtures/ 에 만든다 (실제 사진 아님).

- P0~P4.jpg : 촬영 시각 + GPS (P4는 새벽 01:30 → 하루 시작 04시 기준으로 전날에 들어가야 함)
- P5.jpg    : 촬영 시각만 있고 GPS 없음
- P9.png    : EXIF 없음 (파일 수정 시각으로 대체되는지 확인)
- H1.heic   : HEIC + 촬영 시각 + GPS (exifr가 컨테이너를 못 읽을 때의 대비 경로 확인)
- T00~T17.jpg : 여러 도시 여행(여행지 그룹 확인)
    T00~05 로마(9/20~9/21 오전) · T06~07 기차 안 · T08~13 나폴리·폼페이(9/21 오후~9/22) ·
    T14~17 피렌체(9/23, T16은 위치 없음)

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
    trip = [
        ("2026:09:20 09:00:00", 41.8902, 12.4922),  # 로마 콜로세움
        ("2026:09:20 09:20:00", 41.8905, 12.4925),
        ("2026:09:20 11:00:00", 41.8986, 12.4769),  # 판테온
        ("2026:09:20 15:00:00", 41.9022, 12.4539),  # 바티칸
        ("2026:09:21 08:00:00", 41.9009, 12.4833),  # 트레비
        ("2026:09:21 08:20:00", 41.9010, 12.5011),  # 테르미니
        ("2026:09:21 09:30:00", 41.4900, 13.3100),  # 기차 안
        ("2026:09:21 10:00:00", 41.1000, 14.0000),  # 기차 안
        ("2026:09:21 13:00:00", 40.8518, 14.2681),  # 나폴리
        ("2026:09:21 13:10:00", 40.8520, 14.2685),
        ("2026:09:21 16:00:00", 40.8359, 14.2488),  # 산타루치아
        ("2026:09:22 10:00:00", 40.7497, 14.4869),  # 폼페이
        ("2026:09:22 10:20:00", 40.7490, 14.4850),
        ("2026:09:22 11:00:00", 40.7505, 14.4880),
        ("2026:09:23 10:00:00", 43.7731, 11.2560),  # 피렌체 두오모
        ("2026:09:23 10:15:00", 43.7735, 11.2565),
        ("2026:09:23 10:25:00", None, None),        # 위치 없음
        ("2026:09:23 12:00:00", 43.7680, 11.2531),  # 베키오 다리
    ]
    for i, (t, lat, lng) in enumerate(trip):
        im = Image.new("RGB", (640, 480), (120, 60 + i * 8, 90))
        ImageDraw.Draw(im).text((30, 30), t, fill="white")
        im.save(OUT / f"T{i:02d}.jpg", exif=exif_bytes(t, lat, lng))
    print(f"fixtures written to {OUT}")


if __name__ == "__main__":
    main()
