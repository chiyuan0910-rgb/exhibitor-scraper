import asyncio, sys, re
sys.stdout.reconfigure(encoding='utf-8')
from playwright.async_api import async_playwright

URL = "https://directory.imts.com/8_0/explore/exhibitor-gallery.cfm?featured=false&pavilion=TOOL"

async def debug():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"
        )
        await page.goto(URL, wait_until="networkidle", timeout=60000)
        await page.wait_for_timeout(5000)

        # Try to get first few card HTML snippets
        cards_html = await page.evaluate("""
            () => {
                const sel = [
                    '.c-exhibitor-result', '.result-card', '.card',
                    '[ng-repeat]', '.exhibitor', 'li.item', '.result'
                ];
                for (const s of sel) {
                    const els = document.querySelectorAll(s);
                    if (els.length > 2) {
                        return {sel: s, count: els.length, samples: Array.from(els).slice(0,2).map(e=>e.outerHTML.substring(0,600))};
                    }
                }
                return {sel: 'none', count:0, samples:[]};
            }
        """)
        print(f"Card selector: {cards_html['sel']} ({cards_html['count']} found)")
        for s in cards_html['samples']:
            print(s[:600])
            print("---")

        # Get detail-page links
        links = await page.evaluate("""
            () => Array.from(document.querySelectorAll('a[href]'))
                .map(a => a.href)
                .filter(h => h.length > 30)
                .slice(0, 15)
        """)
        print("\nLinks found:")
        for l in links:
            print(l)

        # Body text excerpt
        body = await page.evaluate("document.body.innerText")
        counts = re.findall(r'(\d+)\s*[Ee]xhibitor', body)
        print(f"\nExhibitor counts: {counts}")
        print("\nBody text (first 800):")
        print(body[:800])

        await browser.close()

asyncio.run(debug())
