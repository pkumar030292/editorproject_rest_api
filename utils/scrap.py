# REST_TEST/utils/scrap_fast_db.py
import re
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

DB_FILE = os.path.join(OUTPUT_DIR, "price_tracker.db")


# --------------------------
# Database helpers
# --------------------------
def init_db():
    """Create tables. Use link as unique key to avoid duplicate products."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS price_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            link TEXT UNIQUE,
            old_price TEXT,
            old_price_num REAL,
            current_price TEXT,
            current_price_num REAL,
            remark TEXT,
            last_checked TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            discount TEXT,
            rating TEXT,
            image TEXT,
            features TEXT
        )
    """)
    conn.commit()
    conn.close()


def clean_price_to_number(price_str):
    """Return a float representing price digits, or None."""
    if not price_str:
        return None
    # Accept strings like '₹13,999' or '13,999' or '13999'
    digits = re.sub(r"[^\d.]", "", str(price_str))
    if digits == "":
        return None
    try:
        # prefer int-like floats but keep float
        return float(digits)
    except:
        return None


def format_price_display(price_num):
    """Return a display string like '₹13,999' from numeric price or 'NA'."""
    if price_num is None:
        return "NA"
    try:
        # round to nearest rupee
        v = int(round(price_num))
        return f"₹{v:,}"
    except:
        return str(price_num)


def upsert_product(product):
    """
    Insert new product or update existing by link.
    Logic:
      - If product exists, compare numeric prices (current_price_num).
      - If changed -> set old_price to previous current_price and update current_price.
      - remark contains increase/decrease/% change or 'Price Same' or 'New Product'.
    """
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    link = product.get("Link") or ""
    title = product.get("Title") or ""
    cur_price_text = product.get("PriceText") or product.get("Price") or "NA"
    cur_price_num = clean_price_to_number(cur_price_text)
    old_price_text_from_scrape = product.get("OldPriceText") or product.get("Old Price") or "NA"
    old_price_num_from_scrape = clean_price_to_number(old_price_text_from_scrape)

    discount = product.get("Discount", "")
    rating = product.get("Rating", "")
    image = product.get("Image", "")
    features = product.get("Features", "")

    remark = "New Product"

    try:
        c.execute("SELECT id, current_price, current_price_num FROM price_history WHERE title = ?", (title,))
        row = c.fetchone()

        if row:
            row_id, db_current_price_text, db_current_price_num = row
            db_price_num = clean_price_to_number(db_current_price_text) if db_current_price_text else db_current_price_num

            # Compare DB numeric price and scraped numeric price
            if db_price_num is not None and cur_price_num is not None:
                if cur_price_num < db_price_num:
                    diff = db_price_num - cur_price_num
                    pct = (diff / db_price_num) * 100 if db_price_num else 0
                    remark = f"Price Decreased by ₹{int(round(diff))} ({pct:.1f}%)"
                elif cur_price_num > db_price_num:
                    diff = cur_price_num - db_price_num
                    pct = (diff / db_price_num) * 100 if db_price_num else 0
                    remark = f"Price Increased by ₹{int(round(diff))} ({pct:.1f}%)"
                else:
                    remark = "Price Same"
            else:
                # If numeric compare not possible, fallback to text comparison
                if str(cur_price_text) != str(db_current_price_text):
                    remark = "Price Changed"
                else:
                    remark = "Price Same"

            # If price changed, set old_price to previous DB current_price
            new_old_price_text = db_current_price_text if db_current_price_text else (format_price_display(db_price_num) if db_price_num is not None else "NA")
            new_old_price_num = db_price_num

            # Update DB row with new current, and old set to previous current
            c.execute("""
                UPDATE price_history
                SET title = ?, old_price = ?, old_price_num = ?, current_price = ?, current_price_num = ?,
                    remark = ?, last_checked = CURRENT_TIMESTAMP,
                    discount = ?, rating = ?, features = ?, image = ?
                WHERE id = ?
            """, (
                title,
                new_old_price_text,
                new_old_price_num,
                format_price_display(cur_price_num),
                cur_price_num,
                remark,
                discount,
                rating,
                features,
                image,
                row_id
            ))
        else:
            # Insert new product record
            c.execute("""
                INSERT INTO price_history
                (title, link, old_price, old_price_num, current_price, current_price_num,
                 remark, last_checked, discount, rating, features, image)
                VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, ?, ?, ?, ?)
            """, (
                title,
                link,
                format_price_display(old_price_num_from_scrape) if old_price_num_from_scrape is not None else "NA",
                old_price_num_from_scrape,
                format_price_display(cur_price_num),
                cur_price_num,
                "New Product",
                discount,
                rating,
                features,
                image
            ))

        conn.commit()
    except Exception as e:
        logging.exception(f"DB upsert failed for link {link}: {e}")
    finally:
        conn.close()

    return remark


# --------------------------
# Scraping helpers
# --------------------------
def safe_text(el):
    return el.get_text(strip=True) if el else "NA"


def scrape_product_details(session, link):
    """Scrape details from a single product link (sequential)."""
    try:
        resp = session.get(link, headers=HEADERS, timeout=25)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")

        # Title (multiple possible selectors)
        title_el = soup.select_one("span.VU-ZEz, span.B_NuCI, h1._2rI4yX")
        title = safe_text(title_el) if title_el else "N/A"

        # Current price: try new and old selectors
        price_el = soup.select_one("div.Nx9bqj.CxhGGd")
        price_text = safe_text(price_el) if price_el else "NA"

        # Old price (strikethrough) if present
        old_price_el = soup.select_one("div.yRaY8j.A6+E6v")
        old_price_text = safe_text(old_price_el) if old_price_el else "NA"

        # Discount
        discount_el = soup.select_one("div._3Ay6Sb span, div.UkUFwK.WW8yVX")
        discount = safe_text(discount_el) if discount_el else ""

        # Rating
        rating_el = soup.select_one("div.XQDdHH, div.Nwhkb3")
        rating = safe_text(rating_el) if rating_el else "N/A"

        # Image
        image_el = soup.select_one("img._396cs4._2amPTt._3qGmMb, img.DByuf4")
        image = image_el["src"] if image_el and image_el.has_attr("src") else ""

        # Features/specs (robust selection)
        # Features section - multiple selectors for safety
        features_text = "NA"

        # Each feature is inside <tr class="WJdYP6 row">
        feature_rows = soup.select("tr.WJdYP6")

        features = []
        for row in feature_rows:
            tds = row.find_all("td")
            if len(tds) == 2:
                key_text = tds[0].get_text(strip=True)
                val_text = tds[1].get_text(strip=True)
                features.append(f"{key_text}: {val_text}")

        if features:
            features_text = " | ".join(features)

        product = {
            "Title": title,
            "PriceText": price_text,
            "OldPriceText": old_price_text,
            "Price": price_text,         # for compatibility
            "Old Price": old_price_text, # compatibility
            "Discount": discount,
            "Rating": rating,
            "Image": image,
            "Features": features_text,
            "Link": link
        }
        return product

    except Exception as e:
        logging.exception(f"Failed scraping link {link}: {e}")
        return None


def scrape_page_links(session, url):
    """Return list of product links for the given page (deduped)."""
    try:
        resp = session.get(url, headers=HEADERS, timeout=20)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")

        # Many Flipkart product anchors: support multiple possible classes
        hrefs = set()
        for tag in soup.select("a.CGtC98, a._1fQZEK, a.IRpwTa, a._2rpwqI"):
            href = tag.get("href")
            if href:
                full = "https://www.flipkart.com" + href if href.startswith("/") else href
                hrefs.add(full)

        return list(hrefs)
    except Exception as e:
        logging.exception(f"Failed to load page {url}: {e}")
        return []


# --------------------------
# Main flow (sequential per product)
# --------------------------
def scrape_flipkart(base_url, max_pages=1, save_csv=False):
    init_db()
    session = requests.Session()
    all_products = []
    page_scraped = 0

    for page in range(1, max_pages + 1):
        # build page url: if base_url already contains page param, replace; else append &page=
        if "page=" in base_url:
            page_url = re.sub(r"page=\d+", f"page={page}", base_url)
        else:
            sep = "&" if "?" in base_url else "?"
            page_url = f"{base_url}{sep}page={page}"

        logging.info(f"Fetching product links from page {page}: {page_url}")
        links = scrape_page_links(session, page_url)
        page_scraped = page

        if not links:
            logging.info("No products found on this page. Stopping.")
            break

        logging.info(f"Found {len(links)} links on page {page}. Processing sequentially...")

        # Sequential processing per link (scrape -> update DB -> next)
        for idx, link in enumerate(links, start=1):
            logging.info(f"[Page {page} | {idx}/{len(links)}] Scraping: {link}")
            product = scrape_product_details(session, link)
            if not product:
                logging.warning(f"Skipping link due to scrape failure: {link}")
                continue

            remark = upsert_product(product)
            product["Remark"] = remark
            product["ScrapeTime"] = datetime.now().isoformat()
            all_products.append(product)

            # Logging only when price changed or new
            if remark and remark != "Price Same":
                logging.info(f"{remark} -> {product.get('Title','N/A')} | {product.get('PriceText')} | {link}")

    # Save CSV summary if requested
    if save_csv and all_products:
        df = pd.DataFrame(all_products)
        csv_path = os.path.join(OUTPUT_DIR, f"flipkart_results_{int(time.time())}.csv")
        df.to_csv(csv_path, index=False, encoding="utf-8-sig")
        logging.info(f"CSV saved at: {csv_path}")
    else:
        csv_path = None

    logging.info(f"Completed scraping. Pages scraped: {page_scraped}, products processed: {len(all_products)}")
    return {"count": len(all_products), "db": DB_FILE, "csv": csv_path, "pages": page_scraped}


def get_all_products():
    """Return all products from DB as a list of dicts"""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM price_history ORDER BY last_checked DESC")
    rows = c.fetchall()
    conn.close()

    products = []
    for row in rows:
        products.append({
            "Title": row["title"],
            "Price": row["current_price"],
            "Old Price": row["old_price"],
            "Discount": row["discount"],
            "Rating": row["rating"],
            "Features": row["features"],
            "Image": row["image"],
            "Link": row["link"],
            "Remark": row["remark"],
            "ScrapeTime": row["last_checked"]
        })
    return products




if __name__ == "__main__":
    # Example usage
    url = "https://www.flipkart.com/search?q=refrigerator"
    result = scrape_flipkart(url, max_pages=5)
    print(f"\n✅ Scraped {result['count']} products across {result['pages']} pages.")
    print(f"DB: {result['db']}")
    if result['csv']:
        print(f"CSV: {result['csv']}")
