# REST_TEST/utils/sarkariresult_db.py
import re
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup
import pandas as pd
import os
import logging
import sqlite3
import time
from datetime import datetime

OUTPUT_DIR = "outputs"
os.makedirs(OUTPUT_DIR, exist_ok=True)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

DB_FILE = os.path.join(OUTPUT_DIR, "sarkariresult.db")


# =========================================================
# DATABASE HELPERS
# =========================================================
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS results (
            id INTEGER PRIMARY KEY AUTOINCREMENT
        )
    """)
    conn.commit()
    conn.close()


def add_missing_columns(parsed_keys):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("PRAGMA table_info(results)")
    existing_cols = [col[1].lower() for col in c.fetchall()]

    for key in parsed_keys:
        if key.lower() not in existing_cols:
            c.execute(f"ALTER TABLE results ADD COLUMN '{key}' TEXT")
            logging.info(f"Added missing column: {key}")

    conn.commit()
    conn.close()


def upsert_result(result):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    title = result.get("Title", "")
    link = result.get("Link", "")
    parsed = result.get("Details", {})
    parsed["title"] = title
    parsed["link"] = link
    parsed["last_checked"] = datetime.now().isoformat()

    # Add missing columns
    c.execute("PRAGMA table_info(results)")
    existing_cols = [col[1].lower() for col in c.fetchall()]
    for key in parsed.keys():
        if key.lower() not in existing_cols:
            c.execute(f"ALTER TABLE results ADD COLUMN '{key}' TEXT")
            logging.info(f"Added column: {key}")
            existing_cols.append(key.lower())

    # Upsert logic
    c.execute("SELECT id FROM results WHERE title = ?", (title,))
    row = c.fetchone()
    if row:
        set_clause = ", ".join([f"'{k}' = ?" for k in parsed.keys()])
        values = list(parsed.values()) + [row[0]]
        c.execute(f"UPDATE results SET {set_clause} WHERE id = ?", values)
        remark = "Updated"
    else:
        cols = ", ".join([f"'{k}'" for k in parsed.keys()])
        placeholders = ", ".join(["?"] * len(parsed))
        c.execute(f"INSERT INTO results ({cols}) VALUES ({placeholders})", list(parsed.values()))
        remark = "Inserted"

    conn.commit()
    conn.close()
    return remark


# =========================================================
# SCRAPING HELPERS
# =========================================================
def safe_text(el):
    return el.get_text(" ", strip=True) if el else "NA"


def scrape_page_links(session, url):
    """Extract all job/result links from main page"""
    try:
        resp = session.get(url, headers=HEADERS, timeout=20)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")

        results = []
        base_url = url

        for a in soup.find_all("a", href=True):
            title = safe_text(a)
            link = a["href"].strip()
            if not title or not link:
                continue
            if link.startswith("#") or "javascript" in link.lower():
                continue

            skip_patterns = [r"home", r"contact", r"privacy", r"disclaimer", r"terms"]
            if any(re.search(p, link, re.IGNORECASE) for p in skip_patterns):
                continue

            link = urljoin(base_url, link)
            results.append({"Title": title, "Link": link})

        unique_results = {r['Link']: r for r in results}.values()
        return list(unique_results)

    except Exception as e:
        logging.exception(f"Failed to load page {url}: {e}")
        return []


# =========================================================
# DETAILED SCRAPER — EXTRACT FIELDS DIRECTLY
# =========================================================
def scrape_job_details(session, url, div_class="gb-grid-wrapper gb-grid-wrapper-303102a8"):
    """
    Dynamically extract all 'Label : Value' pairs from the job page.
    Left side of ':' becomes column name, right side becomes value.
    """
    try:
        if not url or url.startswith("#") or "javascript" in url.lower():
            return {}

        resp = session.get(url, headers=HEADERS, timeout=20)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")

        # Find the container that has all details (update div_class as needed)
        container = soup.find("div", class_=div_class)
        if not container:
            logging.warning(f"No main div found for: {url}")
            return {}

        parsed = {}
        all_texts = []

        # Extract text lines from all relevant tags
        for tag in container.find_all(["p", "li", "span", "tr", "td", "div"]):
            text = tag.get_text(" ", strip=True)
            if text and len(text) > 3:
                all_texts.append(text)

        # Debug print (you can comment this out later)
        for t in all_texts:
            print("aaaaaaaaaaa", t)

        # Now dynamically detect all "Label : Value" patterns
        for text in all_texts:
            if ":" in text:
                parts = text.split(":", 1)
                key = parts[0].strip()
                value = parts[1].strip()

                # Clean column name for SQLite (replace invalid chars)
                clean_key = re.sub(r"[^a-zA-Z0-9_]", "_", key)
                if not clean_key:
                    continue

                parsed[clean_key] = value

        # If nothing matched, save fallback content
        if not parsed:
            parsed["Raw_Text"] = " | ".join(all_texts[:20])

        return parsed

    except Exception as e:
        logging.warning(f"Error scraping {url}: {e}")
        return {"Error": str(e)}



# =========================================================
# MAIN SCRAPER
# =========================================================
def scrape_sarkariresult(base_url="https://sarkariresult.com.cm/latest-jobs/", save_csv=False):
    init_db()
    session = requests.Session()
    all_results = []

    logging.info(f"Fetching result links from: {base_url}")
    links = scrape_page_links(session, base_url)
    if not links:
        logging.warning("No results found.")
        return {"count": 0, "db": DB_FILE, "csv": None}

    logging.info(f"Found {len(links)} results.")

    for idx, result in enumerate(links, start=1):
        details = scrape_job_details(session, result["Link"])
        result["Details"] = details
        remark = upsert_result(result)
        result["Remark"] = remark
        result["ScrapeTime"] = datetime.now().isoformat()
        all_results.append(result)
        logging.info(f"[{idx}/{len(links)}] {remark}: {result['Title']}")

    csv_path = None
    if save_csv and all_results:
        df = pd.DataFrame(all_results)
        csv_path = os.path.join(OUTPUT_DIR, f"sarkariresult_{int(time.time())}.csv")
        df.to_csv(csv_path, index=False, encoding="utf-8-sig")
        logging.info(f"CSV saved at {csv_path}")

    logging.info(f"Completed scraping {len(all_results)} results.")
    return {"count": len(all_results), "db": DB_FILE, "csv": csv_path}


# =========================================================
# FETCH ALL RESULTS
# =========================================================
def get_all_results():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM results ORDER BY last_checked DESC")
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]


# =========================================================
# RUN
# =========================================================
if __name__ == "__main__":
    result = scrape_sarkariresult(save_csv=True)
    print(f"\n✅ Scraped {result['count']} results.")
    print(f"DB: {result['db']}")
    if result['csv']:
        print(f"CSV: {result['csv']}")
