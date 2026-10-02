#!/usr/bin/env python3
"""dist/사진동선지도.html 을 헤드리스 Chromium으로 열어 주요 기능을 확인한다.

순서: python3 scripts/build.py → python3 tests/make_test_images.py → python3 tests/e2e_test.py
필요: pip install playwright pillow  (+ playwright install chromium)
지도 타일 요청은 막아서 네트워크 없이도 돌도록 했다. 스크린샷은 tests/out/ 에 저장된다.
"""
import asyncio
import io
import json
import re
import sys
from urllib.parse import parse_qs, urlparse
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


async def test_start(browser):
    print("[start screen]")
    pg, errors = await new_page(browser, viewport={"width": 1300, "height": 850})
    await pg.wait_for_timeout(400)
    check(await pg.locator(".empty h2").count() > 0, "시작 화면(빈 상태) 표시")
    check(await pg.locator("label.btn[for='fileInput']").count() > 0, "사진 추가 버튼 표시")
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

    await pg.click("#dayTabs .day-tab >> nth=1")
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
    await pg.click("#dayTabs .day-tab >> nth=1")
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
    await pg.click("#dayTabs .day-tab >> nth=1")
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


async def make_trip(pg, name):
    await pg.click("[data-newtrip]")
    await pg.fill("#tripNew", name)
    await pg.press("#tripNew", "Enter")
    await pg.wait_for_timeout(300)


async def tab_labels(pg, sel):
    return [" ".join(t.split()) for t in await pg.locator(sel).all_inner_texts()]


async def test_trips(browser):
    print("[여행지 그룹]")
    pg, errors = await new_page(browser, viewport={"width": 1300, "height": 850})
    T = lambda r: [str(FIX / f"T{i:02d}.jpg") for i in r]
    check(await pg.locator("[data-newtrip]").count() == 1, "그룹 만들기 버튼 표시")

    # 그룹을 만들고 그 탭에서 사진 추가 → 그 그룹에 들어감
    await make_trip(pg, "로마")
    check("이 그룹에 사진을 추가하세요" in await pg.inner_text("#panel"), "빈 그룹 안내")
    await pg.set_input_files("#fileInput", T(range(0, 6)))
    await pg.wait_for_timeout(1500)
    await make_trip(pg, "나폴리")
    await pg.set_input_files("#fileInput", T(range(8, 14)))
    await pg.wait_for_timeout(1500)
    # 모든 사진 탭에서 넣은 사진은 미분류
    await pg.click("[data-place='all']")
    await pg.wait_for_timeout(300)
    await pg.set_input_files("#fileInput", T(range(14, 18)) + T(range(6, 8)))
    await pg.wait_for_timeout(1500)
    labels = await tab_labels(pg, "#placeTabs .day-tab")
    check(labels == ["모든 사진 18장", "◆ 로마 6장", "◆ 나폴리 6장", "미분류 6장", "+ 그룹 만들기"], f"그룹별 사진 수 {labels}")
    await pg.screenshot(path=str(OUT / "trips-all.png"))

    # 이미 넣은 사진을 새 그룹 탭에서 다시 추가 → 그 그룹으로 옮겨짐
    await make_trip(pg, "피렌체")
    await pg.set_input_files("#fileInput", T(range(14, 18)))
    await pg.wait_for_timeout(1200)
    labels = await tab_labels(pg, "#placeTabs .day-tab")
    check("◆ 피렌체 4장" in labels and "미분류 2장" in labels, f"다시 추가 → 그룹으로 옮김 {labels}")

    # 로마 선택 → 날짜 탭이 로마 날짜만, 9/21은 로마 부분만
    await pg.click("#placeTabs .day-tab:has-text('로마')")
    await pg.wait_for_timeout(500)
    days = await tab_labels(pg, "#dayTabs .day-tab")
    check(len(days) == 3 and "9/20" in days[1] and days[2].startswith("9/21") and days[2].endswith("2장"), f"로마 날짜 탭 {days}")
    await pg.screenshot(path=str(OUT / "trips-rome.png"))
    await pg.locator("#dayTabs .day-tab").nth(2).click()
    await pg.wait_for_timeout(400)
    check(await pg.locator(".group").count() == 2, "로마 9/21 은 로마 묶음만")
    others = await pg.inner_text(".others")
    check("나폴리" in others and "미분류" in others, f"이날 다른 그룹 표시 {others!r}")

    # 묶음 카드에서 미분류 → 나폴리로 옮기기
    await pg.click("[data-goplace]:has-text('미분류')")
    await pg.wait_for_timeout(400)
    await pg.select_option("[data-gplace] >> nth=0", label="나폴리")
    await pg.wait_for_timeout(400)
    labels = await tab_labels(pg, "#placeTabs .day-tab")
    check("미분류 1장" in labels and "◆ 나폴리 7장" in labels, f"묶음 카드에서 그룹 옮김 {labels}")

    # 이름 바꾸기
    await pg.click("#placeTabs .day-tab:has-text('피렌체')")
    await pg.wait_for_timeout(300)
    await pg.fill(".ptitle", "Firenze")
    await pg.press(".ptitle", "Enter")
    await pg.wait_for_timeout(300)
    check("Firenze" in await pg.inner_text("#placeTabs"), "그룹 이름 바꾸기")

    store = json.loads(await pg.evaluate(f"localStorage.getItem('{LS_KEY}')"))
    names = sorted(t["name"] for t in store["trips"].values())
    check(names == ["Firenze", "나폴리", "로마"], f"그룹 저장 {names}")

    # 새로고침 후 같은 사진을 넣으면 그룹이 다시 붙는지
    await pg.reload()
    await pg.wait_for_timeout(600)
    await pg.set_input_files("#fileInput", T(range(18)))
    await pg.wait_for_timeout(2500)
    labels = await tab_labels(pg, "#placeTabs .day-tab")
    check(labels[1:4] == ["◆ 로마 6장", "◆ 나폴리 7장", "◆ Firenze 4장"], f"다시 불러온 사진에 그룹 복원 {labels}")

    # 그룹 삭제 → 사진은 미분류로
    pg.on("dialog", lambda d: asyncio.ensure_future(d.accept()))
    await pg.click("#placeTabs .day-tab:has-text('Firenze')")
    await pg.wait_for_timeout(300)
    await pg.click("[data-deltrip]")
    await pg.wait_for_timeout(400)
    labels = await tab_labels(pg, "#placeTabs .day-tab")
    check("미분류 5장" in labels and not any("Firenze" in l for l in labels), f"그룹 삭제 → 미분류 {labels}")
    # 장소 이름 → 지도 마커 옆에 바로 표시, 그룹 전체 보기에도 표시
    await pg.click("#placeTabs .day-tab:has-text('로마')")
    await pg.wait_for_timeout(300)
    await pg.locator("#dayTabs .day-tab").nth(1).click()
    await pg.wait_for_timeout(400)
    await pg.fill(".gtitle >> nth=0", "콜로세움")
    await pg.wait_for_timeout(200)
    check("콜로세움" in await pg.inner_text("#map .leaflet-tooltip.glabel"), "장소 이름 → 지도 라벨 즉시 표시")
    await pg.screenshot(path=str(OUT / "trips-label.png"))
    await pg.locator("#dayTabs .day-tab").nth(0).click()
    await pg.wait_for_timeout(400)
    check("콜로세움" in await pg.inner_text("#map"), "그룹 전체 보기에도 장소 이름 표시")

    # 하루 통째로 옮기기: 미분류의 9/23 → 나폴리 (옮긴 그룹으로 따라감)
    await pg.click("#placeTabs .day-tab:has-text('미분류')")
    await pg.wait_for_timeout(300)
    await pg.locator("#dayTabs .day-tab:has-text('9/23')").click()
    await pg.wait_for_timeout(300)
    await pg.select_option("[data-daymove]", label="나폴리")
    await pg.wait_for_timeout(400)
    labels = await tab_labels(pg, "#placeTabs .day-tab")
    check("◆ 나폴리 11장" in labels and "미분류 1장" in labels, f"이날 사진 통째로 옮기기 {labels}")
    check("나폴리" in await pg.inner_text("#placeTabs [aria-selected='true']"), "옮긴 그룹으로 따라감")

    # 크게 보기에서 사진 한 장 옮기기
    await pg.click(".thumb >> nth=0")
    await pg.wait_for_timeout(500)
    await pg.select_option("#lbTrip", label="로마")
    await pg.wait_for_timeout(400)
    await pg.click("#lbClose")
    await pg.wait_for_timeout(300)
    labels = await tab_labels(pg, "#placeTabs .day-tab")
    check("◆ 로마 7장" in labels and "◆ 나폴리 10장" in labels, f"크게 보기에서 사진 한 장 옮기기 {labels}")

    await pg.set_viewport_size({"width": 400, "height": 820})
    await pg.wait_for_timeout(400)
    await pg.screenshot(path=str(OUT / "trips-mobile.png"))
    check(await pg.evaluate("document.documentElement.scrollWidth <= 400"), "폰 폭에서 가로 스크롤 없음")
    check(not errors, f"페이지 오류 없음 {errors}")
    await pg.close()


class FakeDrive:
    """Drive v3 REST 를 흉내 내는 메모리 저장소 (연동 테스트용). uploads 에 업로드된 파일 이름을 순서대로 남긴다."""

    def __init__(self):
        self.files, self.n, self.uploads = {}, 0, []

    def add(self, meta, data):
        self.n += 1
        fid = f"f{self.n}"
        self.files[fid] = {"id": fid, "name": meta["name"], "mimeType": meta.get("mimeType", ""),
                           "parents": meta.get("parents", []), "data": data, "trashed": False}
        return fid

    def match(self, q, f):
        if f["trashed"]:
            return False
        for name in re.findall(r"name='([^']*)'", q):
            if f["name"] != name:
                return False
        for mt in re.findall(r"mimeType='([^']*)'", q):
            if f["mimeType"] != mt:
                return False
        if "mimeType contains 'image/'" in q and not f["mimeType"].startswith("image/"):
            return False
        for parent in re.findall(r"'([^']*)' in parents", q):
            if parent not in f["parents"]:
                return False
        return True

    def originals(self):
        root = next(f["id"] for f in self.files.values() if f["name"] == "사진동선지도")
        return [f for f in self.files.values() if root in f["parents"] and f["mimeType"].startswith("image/") and not f["trashed"]]

    def project(self):
        f = next((f for f in self.files.values() if f["name"] == "project.json"), None)
        return json.loads(f["data"]) if f else None

    async def handle(self, route):
        req = route.request
        u = urlparse(req.url)
        qs = parse_qs(u.query)
        path, method = u.path, req.method
        if path == "/drive/v3/files" and method == "GET":
            res = [f for f in self.files.values() if self.match(qs["q"][0], f)]
            return await route.fulfill(json={"files": [{"id": f["id"], "name": f["name"], "mimeType": f["mimeType"], "size": str(len(f["data"]))} for f in res]})
        if path == "/drive/v3/files" and method == "POST":
            return await route.fulfill(json={"id": self.add(json.loads(req.post_data), b"")})
        if path == "/upload/drive/v3/files" and method == "POST":
            boundary = req.headers["content-type"].split("boundary=")[1].encode()
            parts = req.post_data_buffer.split(b"--" + boundary)
            body = lambda part: part.split(b"\r\n\r\n", 1)[1][:-2]
            meta = json.loads(body(parts[1]))
            self.uploads.append(meta["name"])
            return await route.fulfill(json={"id": self.add(meta, body(parts[2]))})
        m = re.match(r"/upload/drive/v3/files/(\w+)$", path)
        if m and method == "PATCH":
            self.files[m[1]]["data"] = req.post_data_buffer
            return await route.fulfill(json={"id": m[1]})
        m = re.match(r"/drive/v3/files/(\w+)$", path)
        if m and method == "PATCH":
            self.files[m[1]].update(json.loads(req.post_data))
            return await route.fulfill(json={"id": m[1]})
        if m and qs.get("alt") == ["media"]:
            data = self.files[m[1]]["data"]
            rng = req.headers.get("range")
            if rng:
                data = data[: int(rng.split("-")[1]) + 1]
            return await route.fulfill(body=data)
        return await route.fulfill(status=404, body="not found")


FAKE_GIS = """
localStorage.setItem("photo-route-map.drive-token", JSON.stringify({ access_token: "fake", expiry: Date.now() + 3600e3 }));
window.google = { accounts: { oauth2: { initTokenClient: () => ({ requestAccessToken() {} }), revoke() {} } } };
"""


async def test_drive_resume(browser):
    print("[연동: 중단 후 다시 추가해도 중복 업로드 없음]")
    fake = FakeDrive()
    ctx = await browser.new_context(viewport={"width": 1300, "height": 850})
    await ctx.add_init_script(FAKE_GIS)
    pg = await ctx.new_page()
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    await pg.route("**/*", lambda r: r.abort() if any(h in r.request.url for h in ("arcgisonline.com", "fonts.g", "accounts.google.com")) else r.continue_())
    await pg.route("https://www.googleapis.com/**", fake.handle)

    async def wait_for(cond, ms=20000):
        for _ in range(ms // 250):
            if cond():
                return True
            await pg.wait_for_timeout(250)
        return False

    files = [str(FIX / f"T{i:02d}.jpg") for i in range(6)]
    jpgs = lambda: [f for f in fake.uploads if re.fullmatch(r"T\d\d\.jpg", f)]  # 원본만 (썸네일 이름은 키_시각.jpg)
    thumbs = lambda: [f for f in fake.uploads if not re.fullmatch(r"T\d\d\.jpg", f) and f != "project.json"]
    await pg.goto(PAGE)
    await pg.wait_for_timeout(1500)
    await pg.set_input_files("#fileInput", files)
    ok = await wait_for(lambda: len(fake.originals()) == 6 and fake.project() and sum(1 for p in fake.project()["photos"] if p["thumbFileId"]) == 6)
    check(ok and len(jpgs()) == 6, f"처음 추가 → 원본 6장 업로드 {len(jpgs())}")

    # 창을 닫았다 다시 열고 같은 사진을 다시 추가 → 원본은 다시 올리지 않음
    await pg.reload()
    await pg.wait_for_timeout(2500)
    check("6장" in await pg.inner_text("#dayTabs"), "다시 열면 드라이브에서 6장 복원")
    await pg.set_input_files("#fileInput", files)
    await pg.wait_for_timeout(4000)
    check(len(jpgs()) == 6, f"같은 사진 다시 추가 → 원본 재업로드 없음 (업로드 {len(jpgs())})")

    # 업로드 도중 닫혀 목록(project.json)에 2장이 빠진 상황 → 자동 복구, 다시 추가해도 재업로드 없음
    pf = next(f for f in fake.files.values() if f["name"] == "project.json")
    proj = json.loads(pf["data"])
    proj["photos"] = proj["photos"][:4]
    pf["data"] = json.dumps(proj).encode()
    await pg.reload()
    await pg.wait_for_timeout(3000)
    check("6장" in await pg.inner_text("#dayTabs"), "목록에서 빠진 2장 자동 복구")
    await pg.set_input_files("#fileInput", files)
    await pg.wait_for_timeout(4000)
    check(len(jpgs()) == 6, f"복구 후 다시 추가 → 재업로드 없음 (업로드 {len(jpgs())})")

    # 드라이브 원본이 깨진(크기가 다른) 사진만 다시 올리고 옛 파일은 휴지통으로
    broken = next(f for f in fake.originals() if f["name"] == "T02.jpg")
    broken["data"] = broken["data"][:100]
    await pg.reload()
    await pg.wait_for_timeout(2500)
    await pg.set_input_files("#fileInput", files)
    await wait_for(lambda: len(jpgs()) == 7)
    check(jpgs()[6:] == ["T02.jpg"] and len(thumbs()) == 6, f"깨진 원본만 다시 업로드(썸네일 유지) {jpgs()[6:]} 썸네일 {len(thumbs())}")
    await wait_for(lambda: broken["trashed"])
    check(broken["trashed"] and len(fake.originals()) == 6, "깨진 옛 원본은 휴지통으로 · 드라이브 원본 6장 유지")
    check(not errors, f"페이지 오류 없음 {errors}")
    await ctx.close()


async def main():
    if not FIX.exists():
        print("tests/fixtures 가 없습니다. 먼저 python3 tests/make_test_images.py 를 실행하세요.")
        return 2
    OUT.mkdir(parents=True, exist_ok=True)
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        await test_start(browser)
        await test_jpeg_flow(browser)
        await test_heic_png(browser)
        await test_trips(browser)
        await test_drive_resume(browser)
        await browser.close()
    print(f"\n{'FAILED: ' + str(len(failures)) if failures else 'ALL PASSED'}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
