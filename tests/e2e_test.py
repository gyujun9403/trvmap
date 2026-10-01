#!/usr/bin/env python3
"""dist/사진동선지도.html 을 헤드리스 Chromium으로 열어 주요 기능을 확인한다.

순서: python3 scripts/build.py → python3 tests/make_test_images.py → python3 tests/e2e_test.py
필요: pip install playwright pillow  (+ playwright install chromium)
지도 타일 요청은 막아서 네트워크 없이도 돌도록 했다. 스크린샷은 tests/out/ 에 저장된다.
"""
import asyncio
import io
import json
import sys
import zipfile
from pathlib import Path

from PIL import Image
from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parent.parent
PAGE = (ROOT / "dist" / "사진동선지도.html").as_uri()
FIX = ROOT / "tests" / "fixtures"
OUT = ROOT / "tests" / "out"
LS_KEY = "photo-route-map.v1"
TILE_HOSTS = ("arcgisonline.com", "fonts.googleapis.com", "fonts.gstatic.com", "accounts.google.com", "googleapis.com")

failures = []


def check(cond, msg):
    print(("  ok   " if cond else "  FAIL ") + msg)
    if not cond:
        failures.append(msg)


async def new_page(browser, **kw):
    pg = await browser.new_page(accept_downloads=True, **kw)
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    await pg.route("**/*", lambda r: r.abort() if any(h in r.request.url for h in TILE_HOSTS) else r.continue_())
    await pg.goto(PAGE)
    await pg.wait_for_timeout(600)
    return pg, errors


async def test_demo(browser):
    print("[demo]")
    pg, errors = await new_page(browser, viewport={"width": 1300, "height": 850})
    await pg.wait_for_timeout(400)
    check(not await pg.is_hidden("#demoBanner"), "예시 배너 표시")
    check(await pg.locator(".gmark").count() > 0, "예시 지도 마커 표시")
    await pg.screenshot(path=str(OUT / "desktop.png"))
    await pg.set_viewport_size({"width": 400, "height": 820})
    await pg.wait_for_timeout(400)
    await pg.screenshot(path=str(OUT / "mobile.png"))
    check(await pg.evaluate("document.documentElement.scrollWidth <= 400"), "폰 폭에서 가로 스크롤 없음")
    check(not errors, f"페이지 오류 없음 {errors}")
    await pg.close()


async def test_jpeg_flow(browser):
    print("[jpeg / notes / zip]")
    pg, errors = await new_page(browser, viewport={"width": 1300, "height": 850})
    files = [str(FIX / f"P{i}.jpg") for i in range(6)]
    await pg.set_input_files("#fileInput", files)
    await pg.wait_for_timeout(1500)
    tabs = await pg.inner_text("#dayTabs")
    check("9/12" in tabs and "5장" in tabs, "01:30 사진이 전날(9/12)로 들어감")
    check("9/13" in tabs, "9/13 날짜 탭 생성")

    await pg.click(".day-tab >> nth=1")
    await pg.wait_for_timeout(400)
    await pg.fill(".gtitle >> nth=0", "콜로세움")
    await pg.fill("#dayNote", "하루 메모")
    await pg.click(".thumb >> nth=1")
    await pg.wait_for_timeout(500)
    check(not await pg.is_hidden("#lightbox"), "사진 크게 보기 열림")
    await pg.fill("#lbNote", "사진 메모")
    groups_before = await pg.locator(".group").count()
    await pg.click("#lbSplit")
    await pg.wait_for_timeout(300)
    await pg.click("#lbClose")
    await pg.wait_for_timeout(500)
    check(await pg.locator(".group").count() == groups_before + 1, "이 사진부터 새 묶음 → 묶음 1개 증가")

    store = json.loads(await pg.evaluate(f"localStorage.getItem('{LS_KEY}')"))
    check(store["dayNotes"].get("2026-09-12") == "하루 메모", "하루 메모 자동 저장")
    check("사진 메모" in store["photoNotes"].values(), "사진 메모 자동 저장")
    check(any(v.get("title") == "콜로세움" for v in store["groupNotes"].values()), "묶음 이름 자동 저장")

    await pg.click("#menuData summary")
    async with pg.expect_download() as dl:
        await pg.click("#btnZipDay")
    path = OUT / "day.zip"
    await (await dl.value).save_as(path)
    names = zipfile.ZipFile(path).namelist()
    check(len(names) == 5 and names[0].startswith("2026-09-12_091000_"), f"날짜 ZIP 파일명·개수 {names}")

    await pg.click("#menuData summary")
    async with pg.expect_download() as dl:
        await pg.click("#btnExportNotes")
    notes = json.loads((await (await dl.value).path()).read_text(encoding="utf-8"))
    check(notes.get("v") == 1 and notes["dayNotes"].get("2026-09-12") == "하루 메모", "메모 파일 내보내기")

    # 새로고침 후 같은 사진을 넣으면 메모가 다시 붙는지
    await pg.reload()
    await pg.wait_for_timeout(600)
    await pg.set_input_files("#fileInput", files)
    await pg.wait_for_timeout(1500)
    await pg.click(".day-tab >> nth=1")
    await pg.wait_for_timeout(300)
    check(await pg.input_value("#dayNote") == "하루 메모", "다시 불러온 사진에 메모 복원")
    check(not errors, f"페이지 오류 없음 {errors}")
    await pg.close()


async def test_heic_png(browser):
    print("[heic / png → jpeg]")
    pg, errors = await new_page(browser, viewport={"width": 1300, "height": 850})
    await pg.set_input_files("#fileInput", [str(FIX / "H1.heic"), str(FIX / "P9.png")])
    await pg.wait_for_timeout(6000)
    tabs = await pg.inner_text("#dayTabs")
    check("9/14" in tabs, "HEIC 촬영 시각 판독 (9/14)")
    await pg.click(".day-tab >> nth=1")
    await pg.wait_for_timeout(400)
    check(await pg.locator(".thumb img").count() == 1, "HEIC 썸네일 생성")
    await pg.click(".thumb >> nth=0")
    await pg.wait_for_timeout(2500)
    check("43.77310" in await pg.inner_text("#lbFile"), "HEIC GPS 판독")
    check(await pg.eval_on_selector("#lbImg", "e => e.naturalWidth") == 1200, "HEIC 크게 보기 표시")
    await pg.click("#lbClose")

    await pg.click("#menuData summary")
    async with pg.expect_download(timeout=60000) as dl:
        await pg.click("#btnZipDay")
    path = OUT / "heic.zip"
    await (await dl.value).save_as(path)
    z = zipfile.ZipFile(path)
    im = Image.open(io.BytesIO(z.read(z.namelist()[0])))
    ex = im.getexif()
    check(im.format == "JPEG", "HEIC → JPEG 변환")
    check(ex.get_ifd(0x8769).get(36867) == "2026:09:14 11:00:00", "변환본에 촬영 시각 유지")
    check(ex.get_ifd(0x8825).get(1) == "N", "변환본에 GPS 유지")
    check(not errors, f"페이지 오류 없음 {errors}")
    await pg.close()


async def main():
    if not FIX.exists():
        print("tests/fixtures 가 없습니다. 먼저 python3 tests/make_test_images.py 를 실행하세요.")
        return 2
    OUT.mkdir(parents=True, exist_ok=True)
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        await test_demo(browser)
        await test_jpeg_flow(browser)
        await test_heic_png(browser)
        await browser.close()
    print(f"\n{'FAILED: ' + str(len(failures)) if failures else 'ALL PASSED'}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
