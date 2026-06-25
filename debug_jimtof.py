"""
Quick structural probe of https://www.jimtof.org/en/exhi_search_pronoun
Run this first; use its output to tune scraper_jimtof.py if needed.
"""
import asyncio, sys
sys.stdout.reconfigure(encoding='utf-8')
from playwright.async_api import async_playwright

URL = "https://www.jimtof.org/en/exhi_search_pronoun"
UA  = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
       "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36")

async def probe():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(user_agent=UA)
        print(f"Loading {URL} …", flush=True)
        await page.goto(URL, wait_until="networkidle", timeout=90000)
        await page.wait_for_timeout(3000)

        # Scroll once
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await page.wait_for_timeout(1500)

        # ── 1. Body text preview ─────────────────────────────────────────
        body = await page.evaluate("document.body.innerText")
        print("\n=== Body text (first 1000) ===")
        print(body[:1000])

        # ── 2. Page title & URL ──────────────────────────────────────────
        print(f"\n=== Title: {await page.title()} ===")
        print(f"=== URL: {page.url} ===")

        # ── 3. All <a href> links ────────────────────────────────────────
        hrefs = await page.evaluate("""
            () => Array.from(document.querySelectorAll('a[href]'))
                       .map(a => a.href)
                       .filter(h => h.length > 10)
        """)
        print(f"\n=== All hrefs ({len(hrefs)}) ===")
        for h in hrefs[:60]:
            print(" ", h)

        # ── 4. Card / row candidate selectors ───────────────────────────
        counts = await page.evaluate("""
            () => {
                const sels = [
                    'tr','td','table','li','article','.card',
                    '[class*="exhib"]','[class*="company"]','[class*="list"]',
                    '[class*="item"]','[class*="row"]','[class*="result"]',
                    'dl','dt','dd','section',
                ];
                return sels.map(s => ({sel: s, n: document.querySelectorAll(s).length}))
                           .filter(x => x.n > 0);
            }
        """)
        print("\n=== Element counts ===")
        for c in counts:
            print(f"  {c['sel']:35s} {c['n']}")

        # ── 5. First table HTML ──────────────────────────────────────────
        table_html = await page.evaluate("""
            () => {
                const t = document.querySelector('table');
                return t ? t.outerHTML.substring(0, 2000) : 'no table';
            }
        """)
        print("\n=== First table (first 2000 chars) ===")
        print(table_html)

        # ── 6. Pagination / next button ─────────────────────────────────
        nav_texts = await page.evaluate("""
            () => Array.from(document.querySelectorAll('a,button'))
                       .map(el => el.textContent.trim())
                       .filter(t => t.length > 0 && t.length < 30)
        """)
        print("\n=== Button/link texts ===")
        for t in nav_texts[:50]:
            print(f"  {repr(t)}")

        await browser.close()
        print("\nDone.")

asyncio.run(probe())
