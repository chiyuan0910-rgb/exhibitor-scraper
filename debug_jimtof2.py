"""
Probe the per-letter pages and the exhibitor/en subdomain.
"""
import asyncio, sys
sys.stdout.reconfigure(encoding='utf-8')
from playwright.async_api import async_playwright

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36")

async def probe():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(user_agent=UA)

        # ── Check ?k=a page ──────────────────────────────────────────────
        url_a = "https://www.jimtof.org/en/exhi_search_pronoun?k=a#result"
        print(f"\nLoading {url_a} …", flush=True)
        await page.goto(url_a, wait_until="networkidle", timeout=60000)
        await page.wait_for_timeout(2000)

        body = await page.evaluate("document.body.innerText")
        print("Body (first 800):")
        print(body[:800])

        # All hrefs on this page
        hrefs = await page.evaluate("""
            () => Array.from(document.querySelectorAll('a[href]'))
                       .map(a => ({text: a.textContent.trim().substring(0,50), href: a.href}))
                       .filter(x => x.href.length > 10)
        """)
        print(f"\nAll hrefs ({len(hrefs)}):")
        for h in hrefs[:80]:
            print(f"  {h['text']:40s}  {h['href']}")

        # Element counts
        counts = await page.evaluate("""
            () => {
                const sels = ['tr','td','table','li','ul','ol','article',
                              '[class*="list"]','[class*="item"]','[class*="row"]',
                              '[class*="exhib"]','[class*="company"]',
                              'dt','dd','dl','p'];
                return sels.map(s => ({sel: s, n: document.querySelectorAll(s).length}))
                           .filter(x => x.n > 0);
            }
        """)
        print("\nElement counts:")
        for c in counts:
            print(f"  {c['sel']:35s} {c['n']}")

        # First few list items HTML
        li_html = await page.evaluate("""
            () => Array.from(document.querySelectorAll('li'))
                       .slice(0, 10)
                       .map(e => e.outerHTML.substring(0, 300))
        """)
        print("\nFirst 10 <li> elements:")
        for h in li_html:
            print(h)
            print("---")

        # ── Check exhibitor/en ───────────────────────────────────────────
        print("\n\nLoading https://www.jimtof.org/exhibitor/en …", flush=True)
        await page.goto("https://www.jimtof.org/exhibitor/en",
                        wait_until="networkidle", timeout=60000)
        await page.wait_for_timeout(2000)
        body2 = await page.evaluate("document.body.innerText")
        print("Body (first 600):")
        print(body2[:600])
        print(f"URL after redirect: {page.url}")

        hrefs2 = await page.evaluate("""
            () => Array.from(document.querySelectorAll('a[href]'))
                       .map(a => a.href)
                       .filter(h => h.length > 10)
                       .slice(0, 30)
        """)
        print("Links:")
        for h in hrefs2:
            print(" ", h)

        await browser.close()

asyncio.run(probe())
