"""
exhibitors.csv 自動補全腳本
使用 Claude AI + Web Search 自動搜尋並填入 Website、Email、Main Product
"""
import sys, os, json, time
sys.stdout.reconfigure(encoding='utf-8')
import pandas as pd
import anthropic

BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
INPUT_FILE  = os.path.join(BASE_DIR, "exhibitors.csv")
OUTPUT_FILE = os.path.join(BASE_DIR, "exhibitors_enriched.csv")
FIELDS      = ["Company Name", "Main Product", "Country", "Website", "Email"]
DELAY_SEC   = 1.2

client = anthropic.Anthropic()

SYSTEM_PROMPT = """You are a business research assistant.
Given a company name and country, search the web and return ONLY a JSON object:
{
  "website": "https://...",
  "email": "contact@example.com",
  "main_products": "Brief description of main products/services (max 60 words)"
}
If any field cannot be found, use "N/A". Return JSON only, no other text.
"""

def search_company_info(company: str, country: str) -> dict:
    for attempt in range(3):
        try:
            response = client.messages.create(
                model="claude-sonnet-4-5",
                max_tokens=500,
                system=SYSTEM_PROMPT,
                tools=[{"type": "web_search_20250305", "name": "web_search"}],
                messages=[{"role": "user", "content": f"Company: {company}\nCountry: {country}"}]
            )
            text = " ".join(b.text for b in response.content if hasattr(b, "text"))
            s, e = text.find("{"), text.rfind("}") + 1
            if s >= 0 and e > s:
                return json.loads(text[s:e])
        except Exception as ex:
            print(f"    API error (attempt {attempt+1}): {ex}")
            if attempt < 2:
                time.sleep(3)
    return {"website": "N/A", "email": "N/A", "main_products": "N/A"}


def save(df):
    tmp = OUTPUT_FILE + ".tmp"
    df[FIELDS].to_csv(tmp, index=False, encoding="utf-8-sig")
    os.replace(tmp, OUTPUT_FILE)   # atomic rename — no lock issues


def main():
    # Load source
    df_src = pd.read_csv(INPUT_FILE, encoding="utf-8-sig")
    # Normalise column names (strip BOM/spaces)
    df_src.columns = [c.strip().lstrip("﻿") for c in df_src.columns]
    total = len(df_src)
    print(f"Loaded {total} rows from {INPUT_FILE}")

    # Load or create progress file
    if os.path.exists(OUTPUT_FILE):
        df_out = pd.read_csv(OUTPUT_FILE, encoding="utf-8-sig")
        df_out.columns = [c.strip().lstrip("﻿") for c in df_out.columns]
        # Ensure all required columns exist
        for col in FIELDS:
            if col not in df_out.columns:
                df_out[col] = ""
        print(f"Resuming from existing {OUTPUT_FILE} ({len(df_out)} rows)")
    else:
        df_out = df_src[FIELDS].copy()
        for col in ["Website", "Email", "Main Product"]:
            df_out[col] = df_out[col].fillna("").astype(str).replace("nan", "")

    # Align index
    df_out = df_out.reset_index(drop=True)

    done = skipped = errors = 0
    for i in range(total):
        company = str(df_src.at[i, "Company Name"]).strip()
        country = str(df_src.at[i, "Country"]).strip()

        email_val = str(df_out.at[i, "Email"]).strip()
        if email_val and email_val not in ("N/A", "nan", "", "ERROR"):
            skipped += 1
            print(f"[{i+1}/{total}] skip: {company}")
            continue

        print(f"[{i+1}/{total}] searching: {company} ({country})", flush=True)
        info = search_company_info(company, country)

        df_out.at[i, "Website"]     = info.get("website", "N/A")
        df_out.at[i, "Email"]       = info.get("email", "N/A")
        df_out.at[i, "Main Product"] = info.get("main_products", "N/A")

        print(f"    website: {info.get('website')}", flush=True)
        print(f"    email:   {info.get('email')}", flush=True)
        print(f"    product: {info.get('main_products','')[:80]}", flush=True)

        save(df_out)
        done += 1
        time.sleep(DELAY_SEC)

    save(df_out)
    emails_found = (df_out["Email"].str.strip().ne("") &
                    df_out["Email"].str.strip().ne("N/A")).sum()
    print(f"\nDone. Processed={done}, skipped={skipped}")
    print(f"Emails found: {emails_found}/{total}")
    print(f"Saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
