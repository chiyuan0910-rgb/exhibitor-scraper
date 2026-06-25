"""
JIMTOF 2026 exhibitor name scraper
https://www.jimtof.org/en/exhi_search_pronoun

The public listing only contains company names (no product, country, website, or email).
This scraper collects all names across every letter page and the overseas section,
deduplicates them, and writes exhibitors.csv.
"""
import asyncio, csv, sys
sys.stdout.reconfigure(encoding='utf-8')
from playwright.async_api import async_playwright

BASE    = "https://www.jimtof.org/en/exhi_search_pronoun"
OUTPUT  = "exhibitors.csv"
FIELDS  = ["Company Name", "Main Product", "Country", "Website", "Email"]
UA      = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
           "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36")

# All known letter keys on the site
KEYS = ["digit"] + list("abcdefghijklmnopqrstuvwxyz") + ["oversea"]


async def scrape_page(sem, context, key: str) -> list[str]:
    """Return list of company names for a given letter key."""
    url = f"{BASE}?k={key}#result"
    async with sem:
        page = await context.new_page()
        try:
            await page.goto(url, wait_until="networkidle", timeout=60000)
            await page.wait_for_timeout(1500)

            names = await page.evaluate("""
                () => {
                    const results = [];
                    // Each company: div.col-md-10 inside .exhi-search-list
                    document.querySelectorAll('.exhi-search-list .col-md-10').forEach(el => {
                        const t = el.textContent.trim();
                        if (t.length > 0) results.push(t);
                    });
                    return results;
                }
            """)

            # The list renders each company twice (Japanese + English rows with same text)
            # Deduplicate while preserving first-occurrence order
            seen, unique = set(), []
            for n in names:
                if n not in seen:
                    seen.add(n)
                    unique.append(n)

            print(f"  [{key:8s}]  {len(unique)} companies", flush=True)
            return unique
        except Exception as e:
            print(f"  [{key:8s}]  ERROR: {e}", flush=True)
            return []
        finally:
            await page.close()


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(user_agent=UA)

        sem = asyncio.Semaphore(6)
        tasks = [scrape_page(sem, context, key) for key in KEYS]
        results = await asyncio.gather(*tasks)
        await browser.close()

    # Global dedup across all letter pages
    seen, rows = set(), []
    for names in results:
        for name in names:
            k = name.lower().strip()
            # Strip co-exhibitor / represented-company markers
            clean = name.replace("(*)", "").replace("(**)", "").strip()
            ck = clean.lower().strip()
            if ck and ck not in seen:
                seen.add(ck)
                rows.append({
                    "Company Name": clean,
                    "Main Product": "",
                    "Country":      "",
                    "Website":      "",
                    "Email":        "",
                })

    rows.sort(key=lambda r: r["Company Name"].lower())

    with open(OUTPUT, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nDone: {len(rows)} exhibitors -> {OUTPUT}")
    print("Note: JIMTOF's public listing provides company names only.")
    print("      Product / Country / Website / Email are not published on this page.")
    for r in rows[:10]:
        print(f"  {r['Company Name']}")


if __name__ == "__main__":
    asyncio.run(main())
