"""Inspect item elements and see if there are per-company detail links."""
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

        # Show ALL hrefs (untruncated)
        hrefs = await page.evaluate("""
            () => Array.from(document.querySelectorAll('a[href]'))
                       .map(a => ({text: a.textContent.trim().substring(0,60), href: a.href}))
        """)
        print(f"ALL hrefs ({len(hrefs)}):")
        for h in hrefs:
            print(f"  {h['text']:55s}  {h['href']}")

        # Show all [class*="item"] HTML
        items_html = await page.evaluate("""
            () => Array.from(document.querySelectorAll('[class*="item"]'))
                       .slice(0, 5)
                       .map(e => e.outerHTML.substring(0, 500))
        """)
        print(f"\nFirst 5 [class*=item] elements:")
        for h in items_html:
            print(h)
            print("---")

        # Show the #result section if it exists
        result_html = await page.evaluate("""
            () => {
                const el = document.querySelector('#result') || document.querySelector('.result') ||
                           document.querySelector('[id*="result"]');
                return el ? el.outerHTML.substring(0, 2000) : 'not found';
            }
        """)
        print(f"\n#result section:")
        print(result_html)

        await browser.close()

asyncio.run(probe())
