import asyncio
import time
from pathlib import Path
from playwright.async_api import async_playwright

SCREENSHOTS_DIR = Path("D:/omni-inspect-ai/screenshots")
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
BRAIN_DIR = Path(r"C:\Users\Shiva\.gemini\antigravity\brain\90a7ad29-9e4d-4328-881c-dbf09db83ee7")

async def capture_all():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            executable_path=r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            headless=True
        )
        
        # 1920x1080
        page = await browser.new_page(viewport={"width": 1920, "height": 1080})
        await page.goto("http://127.0.0.1:8000")
        await page.wait_for_timeout(2000)

        # Tab 1: Reset Nominal
        await page.click("button:has-text('RESET NOMINAL')")
        await page.wait_for_timeout(1500)
        await page.screenshot(path=str(SCREENSHOTS_DIR / "01_nominal_after_reset_1920x1080.png"))
        print("Captured 01_nominal_after_reset_1920x1080.png")

        # Tab 1: Mid-ramp
        await page.click("#precursorBtn")
        print("Waiting 12s for mid-ramp...")
        await page.wait_for_timeout(12000)
        await page.screenshot(path=str(SCREENSHOTS_DIR / "02_mid_ramp_1920x1080.png"))
        print("Captured 02_mid_ramp_1920x1080.png")

        # Tab 1: Trip & RCA
        print("Waiting for trip and RCA stream...")
        for _ in range(25):
            status = await page.inner_text("#statusPillText")
            if "TRIPPED" in status:
                break
            await page.wait_for_timeout(1000)
        await page.wait_for_timeout(10000)
        await page.screenshot(path=str(SCREENSHOTS_DIR / "03_10s_after_trip_rca_1920x1080.png"))
        print("Captured 03_10s_after_trip_rca_1920x1080.png")

        # Tab 2: Containment
        await page.click("#tabBtn2")
        await page.wait_for_timeout(1200)
        await page.screenshot(path=str(SCREENSHOTS_DIR / "04_tab2_containment_1920x1080.png"))
        print("Captured 04_tab2_containment_1920x1080.png")

        # Tab 3: Muse Diagnosis
        await page.click("#tabBtn3")
        await page.wait_for_timeout(1200)
        await page.screenshot(path=str(SCREENSHOTS_DIR / "05_tab3_muse_diagnosis_1920x1080.png"))
        print("Captured 05_tab3_muse_diagnosis_1920x1080.png")

        # Tab 4: Repair & Audit
        await page.click("#tabBtn4")
        await page.wait_for_timeout(1200)
        await page.screenshot(path=str(SCREENSHOTS_DIR / "06_tab4_repair_and_audit_1920x1080.png"))
        print("Captured 06_tab4_repair_and_audit_1920x1080.png")

        # 1440x900 Tab 1
        page_compact = await browser.new_page(viewport={"width": 1440, "height": 900})
        await page_compact.goto("http://127.0.0.1:8000")
        await page_compact.wait_for_timeout(2000)
        await page_compact.screenshot(path=str(SCREENSHOTS_DIR / "07_nominal_1440x900.png"))
        print("Captured 07_nominal_1440x900.png")

        await browser.close()

        # Copy to brain dir
        for p_file in SCREENSHOTS_DIR.glob("*.png"):
            dest = BRAIN_DIR / p_file.name
            dest.write_bytes(p_file.read_bytes())
        print("Copied all screenshots to brain artifacts directory!")

if __name__ == "__main__":
    asyncio.run(capture_all())
