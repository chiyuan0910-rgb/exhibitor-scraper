"""Show the HTML of the company listing section."""
import asyncio, sys
sys.stdout.reconfigure(encoding='utf-8')
from playwright.async_api import async_playwright

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36")

async def probe():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(user_agent=UA)
        await page.goto("https://www.jimtof.org/en/exhi_search_pronoun?k=a#result",
                        wait_until="networkidle", timeout=60000)
        await page.wait_for_timeout(2000)

        # Get full page HTML
        html = await page.evaluate("document.body.innerHTML")

        # Find first company occurrence
        idx = html.find('A.L.M.T')
        if idx >= 0:
            print(f"Found 'A.L.M.T' at index {idx}")
            print("=== HTML context (300 before, 1500 after) ===")
            print(html[max(0, idx-300):idx+1500])
        else:
            print("'A.L.M.T' not found in innerHTML")
            # Just dump first 4000 chars after main content
            mid = len(html) // 4
            print(html[mid:mid+3000])

        await browser.close()

asyncio.run(probe())
