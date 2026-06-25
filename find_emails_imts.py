import asyncio, csv, re, sys, warnings
warnings.filterwarnings("ignore")
sys.stdout.reconfigure(encoding='utf-8')
import httpx

INPUT_FILE  = "imts_exhibitors.csv"
OUTPUT_FILE = "imts_exhibitors.csv"
FIELDS      = ["Company Name", "Main Product", "Country", "Website", "Email"]
CONCURRENCY = 25
TIMEOUT     = 10

EMAIL_RE = re.compile(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}')
SKIP = {"noreply","no-reply","example","sentry","schema","w3.org","privacy","support@sentry"}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36",
    "Accept": "text/html,*/*",
}

def best_email(html, site_domain):
    for m in EMAIL_RE.finditer(html):
        e = m.group().lower()
        d = e.split("@")[-1]
        if any(s in d for s in SKIP): continue
        if any(x in e for x in ("noreply","no-reply","pixel","2x.")): continue
        if site_domain and site_domain in d:
            return e   # domain match = best
    # fallback: first non-skip email
    for m in EMAIL_RE.finditer(html):
        e = m.group().lower()
        d = e.split("@")[-1]
        if not any(s in d for s in SKIP):
            return e
    return ""

async def fetch(client, url):
    try:
        r = await client.get(url, timeout=TIMEOUT, follow_redirects=True)
        return r.text
    except Exception:
        return ""

async def scrape_email(sem, client, row, idx, total):
    website = row.get("Website","").strip()
    if not website or website in ("N/A","ERROR",""):
        return
    base = website.rstrip("/")
    try:
        from urllib.parse import urlparse
        site_domain = urlparse(base).netloc.replace("www.","")
    except Exception:
        site_domain = ""

    async with sem:
        pages = await asyncio.gather(
            fetch(client, base),
            fetch(client, base + "/contact"),
            fetch(client, base + "/contact-us"),
            fetch(client, base + "/about"),
            fetch(client, base + "/en/contact"),
        )
        email = best_email(" ".join(pages), site_domain)
        if email:
            row["Email"] = email
            print(f"[{idx}/{total}] {row['Company Name'][:40]} -> {email}", flush=True)
        else:
            print(f"[{idx}/{total}] {row['Company Name'][:40]} -> -", flush=True)

async def main():
    with open(INPUT_FILE, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    print(f"Loaded {len(rows)} rows")

    to_scrape = [(i,r) for i,r in enumerate(rows)
                 if str(r.get("Email","")).strip() in ("","N/A","ERROR")
                 and str(r.get("Website","")).strip() not in ("","N/A","ERROR")]
    print(f"Scraping emails for {len(to_scrape)} companies...")

    async with httpx.AsyncClient(headers=HEADERS, verify=False) as client:
        sem = asyncio.Semaphore(CONCURRENCY)
        await asyncio.gather(*[
            scrape_email(sem, client, row, i+1, len(to_scrape))
            for i, (_, row) in enumerate(to_scrape)
        ])

    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)

    found = sum(1 for r in rows if r.get("Email","").strip() not in ("","N/A","ERROR"))
    print(f"\nDone! Emails: {found}/{len(rows)} -> {OUTPUT_FILE}")

if __name__ == "__main__":
    asyncio.run(main())
