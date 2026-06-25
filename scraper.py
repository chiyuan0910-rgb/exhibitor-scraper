import asyncio
import csv
import sys
sys.stdout.reconfigure(encoding='utf-8')
from playwright.async_api import async_playwright

URL = "exhibitors.csv"
TARGET = "https://katalog.grupamtp.pl/en/?ec=TC22601&_ga=2.202882514.2110875607.1780539796-782084389.1780539687"
OUTPUT_FILE = "exhibitors.csv"
FIELDS = ["Company Name", "Main Product", "Country", "Website", "Email"]
CONCURRENCY = 10  # parallel detail-page workers


async def collect_links(browser):
    """Open listing page, click 'See more' until exhausted, return all detail URLs."""
    page = await browser.new_page()
    print(f"Opening catalog...")
    await page.goto(TARGET, wait_until="networkidle", timeout=60000)
    await page.wait_for_timeout(3000)

    n = 0
    while True:
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await page.wait_for_timeout(800)
        clicked = False
        for btn in await page.query_selector_all("button"):
            text = (await btn.text_content() or "").strip()
            if "See more" in text or "Load more" in text:
                ok = await btn.evaluate("el => el.offsetParent !== null && !el.disabled")
                if ok:
                    n += 1
                    print(f"  Click #{n} 'See more'", flush=True)
                    await btn.click()
                    await page.wait_for_timeout(1200)
                    clicked = True
                    break
        if not clicked:
            break

    links = await page.evaluate("""
        () => {
            const s = new Set();
            document.querySelectorAll('a[href]').forEach(a => {
                if (a.href.includes('katalog.grupamtp.pl') && a.href.includes('oid='))
                    s.add(a.href.split('&')[0]);  // strip GA params
            });
            return [...s];
        }
    """)
    await page.close()
    print(f"Found {len(links)} exhibitor pages after {n} clicks.")
    return links


async def scrape_one(sem, context, url, idx, total):
    async with sem:
        page = await context.new_page()
        try:
            await page.goto(url + "&ec=TC22601", wait_until="domcontentloaded", timeout=25000)
            await page.wait_for_timeout(500)
            data = await page.evaluate("""
                () => {
                    const h1 = document.querySelector('#company-top h1');
                    const name = h1 ? h1.textContent.trim() : '';

                    // Country: last line of address block
                    let country = '';
                    const addrP = document.querySelector('.c-company-info p');
                    if (addrP) {
                        const lines = addrP.innerHTML.split(/<br\\s*\\/?>/i)
                            .map(l => l.replace(/<[^>]+>/g,'').trim()).filter(Boolean);
                        if (lines.length) country = lines[lines.length - 1];
                    }

                    // Website: ng-init > globe link > "Website:" text
                    let website = '';
                    const ngEl = document.querySelector('[ng-init]');
                    if (ngEl) {
                        const m = ngEl.getAttribute('ng-init').match(/ctrl\\.init\\(['"]([^'"]+)['"]/);
                        if (m) website = m[1].startsWith('http') ? m[1] : 'https://' + m[1];
                    }
                    if (!website) {
                        document.querySelectorAll('a[href^="http"]').forEach(a => {
                            if (website) return;
                            if (a.querySelector('i.fa-globe') &&
                                !a.href.includes('mtp.pl') && !a.href.includes('google.'))
                                website = a.href;
                        });
                    }
                    if (!website) {
                        const ip = document.querySelector('.c-additional-info p');
                        if (ip) { const m = ip.textContent.match(/Website:\\s*(https?:\\/\\/\\S+)/i); if (m) website = m[1]; }
                    }

                    // Email: "e-mail:" pattern
                    let email = '';
                    const ip = document.querySelector('.c-additional-info p');
                    if (ip) {
                        const m = ip.textContent.match(/e-mail:\\s*([\\w.+\\-]+@[\\w.\\-]+\\.[a-z]{2,})/i);
                        if (m) email = m[1];
                    }
                    if (!email) {
                        const ml = document.querySelector('a[href^="mailto:"]');
                        if (ml) email = ml.href.replace('mailto:','').split('?')[0].trim();
                    }

                    // Main product: About section, first 200 chars
                    let mainProduct = '';
                    const ap = document.querySelector('#company-about p');
                    if (ap) mainProduct = ap.textContent.trim().replace(/\\s+/g,' ').substring(0,200);

                    return { name, country, website, email, mainProduct };
                }
            """)
            print(f"[{idx}/{total}] {data.get('name','?')} | {data.get('country','')} | {data.get('website','')}", flush=True)
            return data
        except Exception as e:
            print(f"[{idx}/{total}] ERROR {url}: {e}", flush=True)
            return None
        finally:
            await page.close()


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"
        )

        links = await collect_links(browser)

        sem = asyncio.Semaphore(CONCURRENCY)
        tasks = [scrape_one(sem, context, url, i+1, len(links)) for i, url in enumerate(links)]
        results = await asyncio.gather(*tasks)

        await browser.close()

    rows = [
        {"Company Name": r["name"], "Main Product": r["mainProduct"],
         "Country": r["country"], "Website": r["website"], "Email": r["email"]}
        for r in results if r and r.get("name")
    ]

    # dedup
    seen, unique = set(), []
    for row in rows:
        k = row["Company Name"].lower().strip()
        if k and k not in seen:
            seen.add(k); unique.append(row)

    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(unique)

    print(f"\nDone: {len(unique)} exhibitors -> {OUTPUT_FILE}")
    for i, r in enumerate(unique[:10], 1):
        print(f"{i}. {r['Company Name']} | {r['Country']} | {r['Website']} | {r['Email']}")


if __name__ == "__main__":
    asyncio.run(main())
