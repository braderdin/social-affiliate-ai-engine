import os
import re
import time
import random
from urllib.parse import quote
from playwright.sync_api import sync_playwright
from src.guardrails import is_title_blacklisted, normalize_image_url

def extract_product_id(url):
    """Mengekstrak Product ID unik daripada URL produk Lazada."""
    if not url:
        return ""
    match = re.search(r'-i(\d+)', url)
    if match:
        return match.group(1)
    match_id = re.search(r'item_id=(\d+)', url)
    if match_id:
        return match_id.group(1)
    return ""

def clean_high_res_image(img_url):
    """Membuang pengubah saiz thumbnail untuk mendapatkan URL gambar beresolusi tinggi."""
    if not img_url:
        return ""
    url = normalize_image_url(img_url)
    cleaned_url = re.sub(r'_\d+x\d+.*?\.(jpg|png|jpeg|webp)', r'.\1', url, flags=re.IGNORECASE)
    return cleaned_url

def scrape_lazada_products(keywords, max_per_keyword=10, headless=True):
    """
    Menjalankan Playwright Local PC untuk mencari produk mengikut kata kunci.
    Mengambil URL produk asal, Product ID, Tajuk Produk, dan Gambar resolusi tinggi.
    """
    scraped_products = []
    seen_ids = set()

    if isinstance(keywords, str):
        keywords = [keywords]

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=headless,
            args=[
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-blink-features=AutomationControlled'
            ]
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800},
            locale="ms-MY"
        )
        page = context.new_page()

        for kw in keywords:
            if not kw:
                continue

            search_url = f"https://www.lazada.com.my/catalog/?q={quote(kw)}"
            try:
                page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
                time.sleep(random.uniform(2.5, 4.0))

                # Scroll perlahan untuk muat turun kandungan dinamik
                page.evaluate("window.scrollBy(0, 800)")
                time.sleep(1.5)
                page.evaluate("window.scrollBy(0, 800)")
                time.sleep(1.5)

                items = page.query_selector_all('div[data-qa-locator="product-item"]')
                if not items:
                    items = page.query_selector_all('.BmM3f') or page.query_selector_all('div[data-tracking="product-card"]')

                count_for_kw = 0
                for item in items:
                    if count_for_kw >= max_per_keyword:
                        break

                    try:
                        link_elem = item.query_selector('a[href*="-i"]') or item.query_selector('a')
                        if not link_elem:
                            continue

                        href = link_elem.get_attribute('href') or ""
                        if href.startswith('//'):
                            href = f"https:{href}"
                        elif href.startswith('/'):
                            href = f"https://www.lazada.com.my{href}"

                        product_id = extract_product_id(href)
                        if not product_id or product_id in seen_ids:
                            continue

                        # Gambar Produk Beresolusi Tinggi
                        img_elem = item.query_selector('img')
                        raw_img = ""
                        img_alt = ""
                        if img_elem:
                            raw_img = img_elem.get_attribute('src') or img_elem.get_attribute('data-src') or ""
                            img_alt = img_elem.get_attribute('alt') or ""

                        high_res_img = clean_high_res_image(raw_img)
                        if not high_res_img:
                            continue

                        # Ekstrak Tajuk Produk secara Menyeluruh
                        title = ""
                        title_elem = (
                            item.query_selector('.RfM31') or 
                            item.query_selector('a[title]') or 
                            item.query_selector('div[class*="title"]') or 
                            item.query_selector('.title')
                        )
                        if title_elem:
                            title = title_elem.get_attribute('title') or title_elem.inner_text().strip()

                        if not title and link_elem:
                            title = link_elem.get_attribute('title') or link_elem.inner_text().strip()

                        if not title and img_alt:
                            title = img_alt.strip()

                        # Bersihkan Tajuk dari Karakter Tak Diingini
                        title = re.sub(r'\s+', ' ', title).strip()
                        if not title:
                            title = f"Produk Lazada ID {product_id}"

                        # Semakan Kata Kunci Disekat
                        blacklisted, reason = is_title_blacklisted(title)
                        if blacklisted:
                            continue

                        # Harga Produk
                        price_elem = item.query_selector('.ooA3e') or item.query_selector('span[class*="price"]')
                        price_str = price_elem.inner_text().strip() if price_elem else ""

                        seen_ids.add(product_id)
                        scraped_products.append({
                            "product_id": product_id,
                            "title": title,
                            "original_url": href,
                            "image_url": high_res_img,
                            "price": price_str,
                            "keyword": kw
                        })
                        count_for_kw += 1

                    except Exception:
                        continue

            except Exception as e:
                print(f"⚠️ [SCRAPER WARN] Gagal scrape kata kunci '{kw}': {e}")
                continue

        browser.close()

    return scraped_products