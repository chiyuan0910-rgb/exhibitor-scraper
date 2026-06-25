import asyncio, csv, re, sys
sys.stdout.reconfigure(encoding='utf-8')

try:
    import httpx
    USE_HTTPX = True
except ImportError:
    USE_HTTPX = False

from playwright.async_api import async_playwright

INPUT_FILE  = "exhibitors.csv"
OUTPUT_FILE = "exhibitors_final.csv"
FIELDS      = ["Company Name", "Main Product", "Country", "Website", "Email"]
CONCURRENCY = 30
TIMEOUT     = 10

EMAIL_RE = re.compile(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}')
SKIP_DOMAINS = {
    "example.com","sentry.io","wixpress.com","jquery.com","schema.org","w3.org",
    "google.com","facebook.com","instagram.com","twitter.com","linkedin.com",
    "youtube.com","microsoft.com","apple.com","amazonaws.com","cloudflare.com",
}
# Distributor sites — skip their emails (they belong to the distributor, not the exhibitor)
DISTRIBUTOR_SITES = {
    "btc-maszyny.pl","switala.pl","polwelt.pl","awexim.pl","tatje.com",
    "swisschamber.pl","penny-gondek.pl","abplanalp.pl","interpoler.pl",
}

def best_email(html, site_domain):
    candidates = []
    for m in EMAIL_RE.finditer(html):
        e = m.group().lower()
        domain = e.split("@")[-1]
        if domain in SKIP_DOMAINS:
            continue
        if any(x in domain for x in ("noreply","no-reply","2x.","pixel.")):
            continue
        candidates.append(e)
    if not candidates:
        return None
    # Prefer emails whose domain matches the site domain
    for e in candidates:
        if site_domain and site_domain in e.split("@")[-1]:
            return e
    return candidates[0]


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,*/*",
    "Accept-Language": "en-US,en;q=0.9",
}

async def fetch_http(client, url):
    try:
        r = await client.get(url, timeout=TIMEOUT, follow_redirects=True)
        return r.text
    except Exception:
        return ""

async def scrape_http(sem, client, row, idx, total):
    website = row.get("Website", "").strip()
    if not website or website in ("N/A", "ERROR", ""):
        return
    base = website.rstrip("/")
    try:
        from urllib.parse import urlparse
        site_domain = urlparse(base).netloc.replace("www.", "")
    except Exception:
        site_domain = ""

    if any(d in site_domain for d in DISTRIBUTOR_SITES):
        print(f"[{idx}/{total}] {row['Company Name'][:35]} -> skip (distributor site)", flush=True)
        return

    async with sem:
        pages = await asyncio.gather(
            fetch_http(client, base),
            fetch_http(client, base + "/contact"),
            fetch_http(client, base + "/kontakt"),
            fetch_http(client, base + "/contact-us"),
            fetch_http(client, base + "/en/contact"),
        )
        combined = " ".join(pages)
        email = best_email(combined, site_domain)
        if email:
            row["Email"] = email
            print(f"[{idx}/{total}] {row['Company Name'][:35]} -> {email}", flush=True)
        else:
            print(f"[{idx}/{total}] {row['Company Name'][:35]} -> -", flush=True)


async def main():
    with open(INPUT_FILE, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    print(f"Loaded {len(rows)} rows")

    to_scrape = [
        (i, r) for i, r in enumerate(rows)
        if str(r.get("Email","")).strip() in ("", "N/A", "ERROR")
        and str(r.get("Website","")).strip() not in ("", "N/A", "ERROR")
    ]
    print(f"To scrape: {len(to_scrape)}  |  Already have email: {len(rows)-len(to_scrape)}")

    if USE_HTTPX:
        print("Using httpx (fast HTTP mode)")
        async with httpx.AsyncClient(headers=HEADERS, verify=False) as client:
            sem = asyncio.Semaphore(CONCURRENCY)
            await asyncio.gather(*[
                scrape_http(sem, client, row, i+1, len(to_scrape))
                for i, (_, row) in enumerate(to_scrape)
            ])
    else:
        print("httpx not found, using Playwright")
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            ctx = await browser.new_context(user_agent=HEADERS["User-Agent"], ignore_https_errors=True)
            sem = asyncio.Semaphore(10)
            async def pw_scrape(sem, ctx, row, idx, total):
                website = row.get("Website","").strip()
                if not website or website in ("N/A","ERROR",""): return
                base = website.rstrip("/")
                async with sem:
                    page = await ctx.new_page()
                    try:
                        for url in [base, base+"/contact", base+"/kontakt"]:
                            try:
                                await page.goto(url, wait_until="domcontentloaded", timeout=10000)
                                text = await page.evaluate("document.body.innerText")
                                e = best_email(text, "")
                                if e:
                                    row["Email"] = e
                                    print(f"[{idx}/{total}] {row['Company Name'][:35]} -> {e}", flush=True)
                                    return
                            except: pass
                        print(f"[{idx}/{total}] {row['Company Name'][:35]} -> -", flush=True)
                    finally:
                        await page.close()
            await asyncio.gather(*[pw_scrape(sem,ctx,row,i+1,len(to_scrape)) for i,(_,row) in enumerate(to_scrape)])
            await browser.close()

    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)

    found = sum(1 for r in rows if r.get("Email","").strip() not in ("","N/A","ERROR"))
    print(f"\nDone! Emails: {found}/{len(rows)} -> {OUTPUT_FILE}")

if __name__ == "__main__":
    import warnings; warnings.filterwarnings("ignore")
    asyncio.run(main())
