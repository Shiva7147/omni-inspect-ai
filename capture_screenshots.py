import asyncio
import time
from pathlib import Path
from playwright.async_api import async_playwright

SCREENSHOTS_DIR = Path("D:/omni-inspect-ai/screenshots")
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

async def capture_all():
    async with async_playwright() as p:
        # Launch browser
        browser = await p.chromium.launch(
            executable_path=r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            headless=True
        )
        
        # --- VIEWPORT 1: 1920x1080 ---
        page = await browser.new_page(viewport={"width": 1920, "height": 1080})
        await page.goto("http://127.0.0.1:8000")
        await page.wait_for_timeout(1500)

        # Check no scroll at 1920x1080
        scroll_height = await page.evaluate("() => document.body.scrollHeight")
        client_height = await page.evaluate("() => document.body.clientHeight")
        print(f"[1920x1080] scrollHeight={scroll_height}, clientHeight={client_height}, diff={scroll_height - client_height}")

        # 1. State A: Nominal after Reset
        await page.click("button:has-text('RESET NOMINAL')")
        await page.wait_for_timeout(1500)
        await page.screenshot(path=str(SCREENSHOTS_DIR / "01_nominal_after_reset_1920x1080.png"), full_page=False)
        print("Captured 01_nominal_after_reset_1920x1080.png")

        # 2. State B: Mid-ramp
        await page.click("#precursorBtn")
        print("Precursor ramp started, waiting 12s for mid-ramp...")
        await page.wait_for_timeout(12000)
        await page.screenshot(path=str(SCREENSHOTS_DIR / "02_mid_ramp_1920x1080.png"), full_page=False)
        print("Captured 02_mid_ramp_1920x1080.png")

        # 3. State C: 10s after trip with RCA streaming
        print("Waiting for trip and RCA streaming...")
        # Wait until status pill changes to TRIPPED
        for _ in range(25):
            status = await page.inner_text("#statusPillText")
            if "TRIPPED" in status:
                print(f"Status tripped detected! Status: {status}")
                break
            await page.wait_for_timeout(1000)

        # Wait 10s after trip for RCA stream tokens to populate
        await page.wait_for_timeout(10000)
        await page.screenshot(path=str(SCREENSHOTS_DIR / "03_10s_after_trip_rca_1920x1080.png"), full_page=False)
        print("Captured 03_10s_after_trip_rca_1920x1080.png")

        # 4. State D: Tab 2 (Containment) view
        await page.click("#tabBtn2")
        await page.wait_for_timeout(1000)
        await page.screenshot(path=str(SCREENSHOTS_DIR / "04_tab2_containment_1920x1080.png"), full_page=False)
        print("Captured 04_tab2_containment_1920x1080.png")

        # --- VIEWPORT 2: 1440x900 ---
        page_compact = await browser.new_page(viewport={"width": 1440, "height": 900})
        await page_compact.goto("http://127.0.0.1:8000")
        await page_compact.wait_for_timeout(1500)
        scroll_height_c = await page_compact.evaluate("() => document.body.scrollHeight")
        client_height_c = await page_compact.evaluate("() => document.body.clientHeight")
        print(f"[1440x900] scrollHeight={scroll_height_c}, clientHeight={client_height_c}, diff={scroll_height_c - client_height_c}")
        await page_compact.screenshot(path=str(SCREENSHOTS_DIR / "05_nominal_1440x900.png"), full_page=False)
        print("Captured 05_nominal_1440x900.png")

        await browser.close()
        print("All screenshots captured successfully!")

if __name__ == "__main__":
    asyncio.run(capture_all())
