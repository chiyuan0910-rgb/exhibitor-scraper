import asyncio, sys
sys.stdout.reconfigure(encoding='utf-8')
from playwright.async_api import async_playwright

async def debug():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36")
        # Test a few exhibitors
        for url in [
            "https://directory.imts.com/8_0/exhibitor/00002875/BIG-DAISHOWA",
            "https://directory.imts.com/8_0/exhibitor/00064359/Blue-Photon-Technology-Workholding-Systems-LLC",
        ]:
            await page.goto(url, wait_until="domcontentloaded", timeout=25000)
            await page.wait_for_timeout(1500)
            text = await page.evaluate("document.body.innerText")
            # Print address/country section
            lines = [l.strip() for l in text.split('\n') if l.strip()]
            print(f"\n=== {url.split('/')[-1]} ===")
            # Find address-like content
            for i, line in enumerate(lines):
                if any(x in line.upper() for x in ['BOOTH','ADDRESS','CITY','STATE','COUNTRY','ZIP','PHONE','FAX','IL','USA','CHICAGO']):
                    print(f"  [{i}] {line}")
            # Print first 50 lines
            print("First 40 lines:")
            for l in lines[:40]:
                print(f"  {repr(l)}")
        await browser.close()

asyncio.run(debug())
