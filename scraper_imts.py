import asyncio, csv, sys, re
sys.stdout.reconfigure(encoding='utf-8')
from playwright.async_api import async_playwright

BASE    = "https://directory.imts.com"
URL     = f"{BASE}/8_0/explore/exhibitor-gallery.cfm?featured=false&pavilion=TOOL"
OUTPUT  = "imts_exhibitors.csv"
CONCURRENCY = 15
FIELDS  = ["Company Name", "Main Product", "Country", "Website", "Email"]
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"

EMAIL_RE = re.compile(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}')
SKIP_EMAIL = {"noreply","no-reply","example","sentry","schema","w3.org"}


def clean_email(e):
    e = (e or "").strip()
    if not e: return ""
    d = e.split("@")[-1].lower()
    if any(s in d for s in SKIP_EMAIL): return ""
    return e


async def load_all(page):
    """Click 'Load More Results' until all cards are loaded."""
    clicks = 0
    while True:
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await page.wait_for_timeout(800)
        btn = None
        for b in await page.query_selector_all("button, a"):
            t = (await b.text_content() or "").strip()
            if "Load More" in t or "load more" in t.lower():
                ok = await b.evaluate("el => el.offsetParent !== null && !el.disabled")
                if ok:
                    btn = b
                    break
        if not btn:
            break
        clicks += 1
        print(f"  Load More click #{clicks}", flush=True)
        await btn.click()
        await page.wait_for_timeout(1500)

    # Collect all exhibitor detail links
    links = await page.evaluate(f"""
        () => {{
            const seen = new Set();
            const results = [];
            document.querySelectorAll('a[href*="/8_0/exhibitor/"]').forEach(a => {{
                const href = a.href.split('?')[0];
                if (!seen.has(href)) {{ seen.add(href); results.push(href); }}
            }});
            return results;
        }}
    """)
    print(f"Total unique exhibitor links: {len(links)}")
    return links


async def scrape_detail(sem, context, url, idx, total):
    async with sem:
        page = await context.new_page()
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=25000)
            await page.wait_for_timeout(800)

            data = await page.evaluate("""
                () => {
                    const bodyText = document.body.innerText;
                    const lines = bodyText.split('\\n').map(l => l.trim()).filter(Boolean);

                    // Company name: first h1 or line after nav
                    const h1 = document.querySelector('h1');
                    const name = h1 ? h1.textContent.trim() : '';

                    // Country + Website: parse "Company Information" block
                    let country = '', website = '';
                    const ciIdx = lines.findIndex(l => l === 'Company Information');
                    if (ciIdx >= 0) {
                        // Pattern: [0]=Company Information, [1]=street, [2]=city/state/zip, [3]=country, [4]=website
                        const block = lines.slice(ciIdx + 1, ciIdx + 8);
                        for (let i = 0; i < block.length; i++) {
                            const l = block[i];
                            // Country: not a number/phone, not US state pattern, longer word(s)
                            if (!country && l.length > 3 && !/^[+0-9()\-\s]+$/.test(l)
                                && !/^\d/.test(l) && !/^www\./i.test(l)
                                && !l.includes('@') && i >= 2) {
                                // Likely a country name (comes after street + city/state/zip)
                                country = l;
                            }
                            if (!website && /^www\./i.test(l)) {
                                website = 'https://' + l.replace(/\\/+$/, '');
                            }
                        }
                    }

                    // Website fallback: external links
                    if (!website) {
                        document.querySelectorAll('a[href^="http"]').forEach(a => {
                            if (website) return;
                            const h = a.href;
                            if (!h.includes('imts.com') && !h.includes('mapyourshow') &&
                                !h.includes('google') && !h.includes('facebook') &&
                                !h.includes('linkedin') && !h.includes('twitter') &&
                                !h.includes('youtube') && !h.includes('instagram')) {
                                website = h.split('?')[0];
                            }
                        });
                    }

                    // Main Product: paragraph after "About [CompanyName]"
                    let mainProduct = '';
                    const aboutMarker = 'About ' + name;
                    const aboutIdx = lines.findIndex(l => l.startsWith(aboutMarker));
                    if (aboutIdx >= 0 && aboutIdx + 1 < lines.length) {
                        // Next non-trivial line after the marker
                        for (let i = aboutIdx + 1; i < Math.min(aboutIdx + 4, lines.length); i++) {
                            if (lines[i].length > 30 && !lines[i].startsWith('About ')) {
                                mainProduct = lines[i].substring(0, 250);
                                break;
                            }
                        }
                    }

                    // Email — mailto links first
                    let email = '';
                    const ml = document.querySelector('a[href^="mailto:"]');
                    if (ml) email = ml.href.replace('mailto:','').split('?')[0].trim();

                    return { name, mainProduct, country, website, email };
                }
            """)

            # Regex email fallback from page text
            if not data.get("email"):
                text = await page.evaluate("document.body.innerText")
                m = EMAIL_RE.search(text)
                if m:
                    data["email"] = clean_email(m.group())

            print(f"[{idx}/{total}] {data.get('name','?')[:45]} | {data.get('country','')} | {data.get('website','')[:40]}", flush=True)
            return data

        except Exception as e:
            print(f"[{idx}/{total}] ERROR {url}: {e}", flush=True)
            return None
        finally:
            await page.close()


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(user_agent=UA)

        # Step 1: load listing page and collect all links
        page = await context.new_page()
        print(f"Opening: {URL}")
        await page.goto(URL, wait_until="networkidle", timeout=60000)
        await page.wait_for_timeout(3000)
        links = await load_all(page)
        await page.close()

        # Step 2: scrape all detail pages in parallel
        sem = asyncio.Semaphore(CONCURRENCY)
        tasks = [
            scrape_detail(sem, context, url, i+1, len(links))
            for i, url in enumerate(links)
        ]
        results = await asyncio.gather(*tasks)
        await browser.close()

    # Build rows
    rows = []
    for r in results:
        if r and r.get("name"):
            rows.append({
                "Company Name": r["name"],
                "Main Product": r.get("mainProduct", ""),
                "Country":      r.get("country", ""),
                "Website":      r.get("website", ""),
                "Email":        clean_email(r.get("email", "")),
            })

    # Dedup by name
    seen, unique = set(), []
    for row in rows:
        k = row["Company Name"].lower().strip()
        if k and k not in seen:
            seen.add(k); unique.append(row)

    with open(OUTPUT, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(unique)

    has_w = sum(1 for r in unique if r["Website"])
    has_e = sum(1 for r in unique if r["Email"])
    print(f"\nDone: {len(unique)} exhibitors | Website: {has_w} | Email: {has_e}")
    print(f"Saved -> {OUTPUT}")
    for r in unique[:5]:
        print(f"  {r['Company Name']} | {r['Country']} | {r['Website']} | {r['Email']}")


if __name__ == "__main__":
    asyncio.run(main())
