# REST_TEST/utils/scrap_fast.py
import requests
from bs4 import BeautifulSoup
import pandas as pd
import os
import logging
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from concurrent.futures import ThreadPoolExecutor

OUTPUT_DIR = "outputs"
os.makedirs(OUTPUT_DIR, exist_ok=True)

logging.basicConfig(level=logging.INFO)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}


def build_page_url(base_url, page_num):
    parsed = urlparse(base_url)
    query = parse_qs(parsed.query)
    query["page"] = [str(page_num)]
    new_query = urlencode(query, doseq=True)
    return urlunparse(parsed._replace(query=new_query))


def scrape_product_features(product_url):
    """Scrape detailed product features from product page"""
    try:
        resp = requests.get(product_url, headers=HEADERS, timeout=20)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")

        features = []
        spec_sections = soup.select("div._2418kt, div._21lJbe")
        for section in spec_sections:
            rows = section.select("tr")
            for row in rows:
                th = row.select_one("td._1hKmbr")  # Feature name
                td = row.select_one("td.URwL2w")   # Feature value
                if th and td:
                    features.append(f"{th.get_text(strip=True)}: {td.get_text(strip=True)}")
        return " | ".join(features)
    except Exception as e:
        logging.warning(f"Failed to scrape product features: {e}")
        return ""


def scrape_flipkart(url: str, max_pages: int = 20, fetch_detailed_features=False):
    all_products = []
    page = 1

    while page <= max_pages:
        page_url = build_page_url(url, page)
        logging.info(f"Fetching page {page}: {page_url}")

        try:
            response = requests.get(page_url, headers=HEADERS, timeout=20)
            response.raise_for_status()
        except Exception as e:
            logging.warning(f"Failed to load page {page}: {e}")
            break

        soup = BeautifulSoup(response.text, "lxml")
        cards = soup.select("div.tUxRFH")
        if not cards:
            logging.info(f"No more products found at page {page}. Stopping.")
            break

        links_for_features = []

        for card in cards:
            try:
                title = card.select_one("div.KzDlHZ")
                title = title.get_text(strip=True) if title else "N/A"

                price = card.select_one("div.Nx9bqj._4b5DiR")
                price = price.get_text(strip=True) if price else "N/A"

                old_price = card.select_one("div.yRaY8j.ZYYwLA")
                old_price = old_price.get_text(strip=True) if old_price else ""

                discount = card.select_one("div.UkUFwK span")
                discount = discount.get_text(strip=True) if discount else ""

                rating = card.select_one("div.XQDdHH")
                rating = rating.get_text(strip=True).split()[0] if rating else "N/A"

                link_tag = card.select_one("a.CGtC98")
                if link_tag and link_tag.has_attr("href"):
                    link = "https://www.flipkart.com" + link_tag["href"] if not link_tag["href"].startswith("http") else link_tag["href"]
                else:
                    link = "N/A"

                image = card.select_one("img.DByuf4")
                image = image["src"] if image and image.has_attr("src") else ""

                # Fast features from search card itself
                features = []
                feature_container = card.select_one("div._6NESgJ")
                if feature_container:
                    features = [li.get_text(strip=True) for li in feature_container.find_all("li")]
                features_text = " | ".join(features)

                all_products.append({
                    "Title": title,
                    "Price": price,
                    "Old Price": old_price,
                    "Discount": discount,
                    "Rating": rating,
                    "Features": features_text,
                    "Link": link,
                    "Image": image
                })

                if fetch_detailed_features and link != "N/A":
                    links_for_features.append(link)

            except Exception as e:
                logging.warning(f"Error parsing product: {e}")

        # Optional: fetch detailed features in parallel
        if fetch_detailed_features and links_for_features:
            logging.info("Fetching detailed features in parallel...")
            with ThreadPoolExecutor(max_workers=10) as executor:
                detailed_features = list(executor.map(scrape_product_features, links_for_features))
            # Update features in all_products
            j = 0
            for i, prod in enumerate(all_products[-len(links_for_features):]):
                prod["Features"] = detailed_features[j]
                j += 1

        page += 1

    if not all_products:
        return {"error": "No products found on any page."}

    df = pd.DataFrame(all_products)
    csv_path = os.path.join(OUTPUT_DIR, "flipkart_all_pages_fast.csv")
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")

    logging.info(f"✅ Scraped {len(all_products)} products across {page - 1} pages.")
    return {"data": all_products, "file_path": csv_path, "pages_scraped": page - 1}


if __name__ == "__main__":
    # Example usage:
    url = "https://www.flipkart.com/search?q=ac"
    result = scrape_flipkart(url, max_pages=5, fetch_detailed_features=False)  # False = fast
    print(result["file_path"])
