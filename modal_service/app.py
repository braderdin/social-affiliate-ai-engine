import modal
import urllib.parse
import re
import json
from typing import List, Dict, Any

# Imej Docker Debian dengan Playwright & System Dependencies
image = (
    modal.Image.debian_slim(python_version="3.10")
    .pip_install("playwright==1.42.0", "playwright-stealth==1.0.6", "httpx")
    .run_commands("python -m playwright install --with-deps chromium")
)

app = modal.App(name="lazada-playwright-scraper", image=image)

@app.function(timeout=120)
async def search_lazada_products(keyword: str, max_results: int = 5) -> Dict[str, Any]:
    """
    Fungsi Scraper di Modal.com yang memulangkan data produk ATAU laporan diagnostik lengkap sekiranya disekat.
    TIDAK MENGGUNAKAN SEBARANG DUMMY LINK ATAU GAMBAR FALLBACK.
    """
    from playwright.async_api import async_playwright
    from playwright_stealth import stealth_async

    if not keyword or not keyword.strip():
        return {
            "status": "ERROR",
            "error_code": "EMPTY_KEYWORD",
            "message": "Kata kunci carian tidak boleh kosong."
        }

    encoded_kw = urllib.parse.quote(keyword.strip())
    search_url = f"https://www.lazada.com.my/catalog/?q={encoded_kw}"

    diagnostics = {
        "keyword": keyword,
        "target_url": search_url,
        "http_status": None,
        "page_title": "",
        "window_pagedata_found": False,
        "dom_items_found": 0,
        "is_captcha_detected": False,
        "error_message": ""
    }

    results = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled"
            ]
        )

        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            viewport={"width": 1366, "height": 768},
            locale="en-US",
            timezone_id="Asia/Kuala_Lumpur"
        )

        page = await context.new_page()
        await stealth_async(page)

        try:
            # 1. Melawat Homepage
            await page.goto("https://www.lazada.com.my/", wait_until="domcontentloaded", timeout=20000)
            await page.wait_for_timeout(2000)

            # 2. Melawat Halaman Carian
            response = await page.goto(search_url, wait_until="domcontentloaded", timeout=25000)
            if response:
                diagnostics["http_status"] = response.status

            await page.wait_for_timeout(3000)

            diagnostics["page_title"] = await page.title()

            # Pengesanan CAPTCHA / Sekatan Akamai
            if "security" in diagnostics["page_title"].lower() or "punish" in page.url:
                diagnostics["is_captcha_detected"] = True

            # 3. Semakan window.pageData
            page_data = await page.evaluate("() => window.pageData || null")
            if page_data and "mods" in page_data and "listItems" in page_data["mods"]:
                diagnostics["window_pagedata_found"] = True
                list_items = page_data["mods"]["listItems"]

                for item in list_items[:max_results]:
                    raw_url = item.get("itemUrl", "")
                    if raw_url.startswith("//"):
                        raw_url = "https:" + raw_url
                    elif raw_url and not raw_url.startswith("http"):
                        raw_url = "https://www.lazada.com.my" + raw_url

                    pid_match = re.search(r'-i(\d+)', raw_url) or re.search(r'i(\d+)\.html', raw_url)
                    product_id = pid_match.group(1) if pid_match else str(item.get("itemId", ""))

                    title = str(item.get("name", "")).strip()
                    price = str(item.get("price", "0")).strip()
                    image_url = item.get("image", "")

                    if title and raw_url:
                        results.append({
                            "product_id": product_id,
                            "title": title,
                            "price": price,
                            "image": image_url,
                            "raw_url": raw_url
                        })

            # 4. Fallback DOM Selectors
            if not results:
                await page.evaluate("window.scrollBy(0, 1000);")
                await page.wait_for_timeout(1500)

                items = await page.query_selector_all('div[data-qa-type="product-item"], .BmBOZ, div[data-tracking="product-card"]')
                diagnostics["dom_items_found"] = len(items)

                for item in items[:max_results]:
                    link_elem = await item.query_selector('a[href*="/products/"]')
                    if not link_elem:
                        continue

                    raw_href = await link_elem.get_attribute('href') or ""
                    raw_url = "https:" + raw_href if raw_href.startswith("//") else raw_href
                    if not raw_url.startswith("http"):
                        raw_url = "https://www.lazada.com.my" + raw_href

                    pid_match = re.search(r'-i(\d+)', raw_url) or re.search(r'i(\d+)\.html', raw_url)
                    product_id = pid_match.group(1) if pid_match else ""

                    title = await link_elem.get_attribute('title') or await link_elem.text_content() or ""
                    img_elem = await item.query_selector('img')
                    img_url = ""
                    if img_elem:
                        img_url = await img_elem.get_attribute('src') or await img_elem.get_attribute('data-src') or ""
                        if img_url.startswith("//"):
                            img_url = "https:" + img_url

                    price_elem = await item.query_selector('span[class*="price"]') or await item.query_selector('span[class*="ooA36"]')
                    price_str = await price_elem.text_content() if price_elem else "0"

                    if title and raw_url:
                        results.append({
                            "product_id": product_id,
                            "title": title.strip(),
                            "price": price_str.strip(),
                            "image": img_url,
                            "raw_url": raw_url
                        })

        except Exception as e:
            diagnostics["error_message"] = str(e)
        finally:
            await context.close()
            await browser.close()

    if results:
        return {
            "status": "SUCCESS",
            "count": len(results),
            "products": results,
            "diagnostics": diagnostics
        }
    else:
        return {
            "status": "FAILED",
            "count": 0,
            "products": [],
            "diagnostics": diagnostics
        }