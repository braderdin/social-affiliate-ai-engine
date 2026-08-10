import modal
import urllib.parse
import re
import json
from typing import List, Dict, Any

image = (
    modal.Image.debian_slim(python_version="3.10")
    .pip_install("playwright==1.42.0", "playwright-stealth==1.0.6", "httpx")
    .run_commands("python -m playwright install --with-deps chromium")
)

app = modal.App(name="lazada-playwright-scraper", image=image)

@app.function(timeout=120)
async def search_lazada_products(keyword: str, max_results: int = 5) -> Dict[str, Any]:
    """
    Scraper Playwright Lazada di Modal.com.
    MENGESTRAK DATA SEBENAR TANPA SEBARANG DATA DUMMY ATAU PAUTAN PALSU.
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
        "extraction_source": "none",
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
            locale="ms-MY",
            timezone_id="Asia/Kuala_Lumpur",
            extra_http_headers={
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                "Accept-Language": "ms-MY,ms;q=0.9,en-US;q=0.8,en;q=0.7",
                "Sec-Ch-Ua": '"Not-A.Brand";v="99", "Chromium";v="124", "Google Chrome";v="124"',
                "Sec-Ch-Ua-Mobile": "?0",
                "Sec-Ch-Ua-Platform": '"Windows"',
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
                "Upgrade-Insecure-Requests": "1"
            }
        )

        page = await context.close_page() if hasattr(context, 'close_page') else await context.new_page()
        await stealth_async(page)

        try:
            # 1. Melawat Homepage Lazada untuk mendapatkan Session Cookie sah
            try:
                await page.goto("https://www.lazada.com.my/", wait_until="domcontentloaded", timeout=20000)
                await page.wait_for_timeout(2500)
            except Exception as hp_err:
                print(f"⚠️ Warning Homepage: {hp_err}")

            # 2. Navigasi ke Halaman Carian
            response = await page.goto(search_url, wait_until="domcontentloaded", timeout=25000)
            if response:
                diagnostics["http_status"] = response.status

            await page.wait_for_timeout(3000)
            diagnostics["page_title"] = await page.title()

            # Semakan Sekatan Akamai / CAPTCHA
            if "security" in diagnostics["page_title"].lower() or "punish" in page.url or "deny" in diagnostics["page_title"].lower():
                diagnostics["is_captcha_detected"] = True

            # Scroll ke bawah untuk trigger lazy loading
            await page.evaluate("window.scrollBy(0, 800);")
            await page.wait_for_timeout(1500)

            # 3. Menganalisis & Mengestrakan Data Produk Menggunakan JavaScript Evaluator Terus Di Dalam Pelayar
            extraction_script = """
            () => {
                let items = [];
                let source = 'none';

                // A. Semakan window.pageData
                if (window.pageData && window.pageData.mods && window.pageData.mods.listItems) {
                    source = 'window.pageData';
                    items = window.pageData.mods.listItems.map(item => {
                        let rawUrl = item.itemUrl || '';
                        if (rawUrl.startsWith('//')) rawUrl = 'https:' + rawUrl;
                        else if (rawUrl && !rawUrl.startsWith('http')) rawUrl = 'https://www.lazada.com.my' + rawUrl;

                        let pid = String(item.itemId || '');
                        if (!pid && rawUrl) {
                            let m = rawUrl.match(/-i(\\d+)/) || rawUrl.match(/i(\\d+)\\.html/);
                            if (m) pid = m[1];
                        }

                        return {
                            product_id: pid,
                            title: (item.name || '').trim(),
                            price: String(item.price || '0').trim(),
                            image: item.image || '',
                            raw_url: rawUrl
                        };
                    }).filter(x => x.title && x.raw_url);
                }

                // B. Fallback DOM Parsing
                if (items.length === 0) {
                    source = 'dom_parsing';
                    const cards = document.querySelectorAll('div[data-qa-type="product-item"], div[data-tracking="product-card"], .BmBOZ, div[class*="item-card"]');
                    
                    cards.forEach(card => {
                        const aTag = card.querySelector('a[href*="/products/"]') || card.querySelector('a');
                        if (!aTag) return;

                        let href = aTag.getAttribute('href') || '';
                        if (!href) return;
                        if (href.startsWith('//')) href = 'https:' + href;
                        else if (href.startsWith('/')) href = 'https://www.lazada.com.my' + href;

                        // Ekstrak Tajuk
                        let title = aTag.getAttribute('title') || '';
                        if (!title) {
                            const img = card.querySelector('img');
                            if (img) title = img.getAttribute('alt') || '';
                        }
                        if (!title) {
                            const titleEl = card.querySelector('div[class*="title"], div[class*="Name"], div.Rf31n, ._17mR_');
                            if (titleEl) title = titleEl.innerText || titleEl.textContent || '';
                        }
                        if (!title) {
                            title = aTag.innerText || aTag.textContent || '';
                        }
                        title = title.replace(/\\s+/g, ' ').trim();

                        // Ekstrak Harga
                        let price = '0';
                        const priceEl = card.querySelector('span[class*="price"], div[class*="price"], span.ooA36');
                        if (priceEl) price = (priceEl.innerText || priceEl.textContent || '0').trim();

                        // Ekstrak Imej
                        let imgUrl = '';
                        const imgEl = card.querySelector('img');
                        if (imgEl) {
                            imgUrl = imgEl.getAttribute('src') || imgEl.getAttribute('data-src') || imgEl.getAttribute('data-ks-lazyload') || '';
                            if (imgUrl.startsWith('//')) imgUrl = 'https:' + imgUrl;
                        }

                        let pidMatch = href.match(/-i(\\d+)/) || href.match(/i(\\d+)\\.html/);
                        let pid = pidMatch ? pidMatch[1] : '';

                        if (title && href && title.length > 3) {
                            items.push({
                                product_id: pid,
                                title: title,
                                price: price,
                                image: imgUrl,
                                raw_url: href
                            });
                        }
                    });
                }

                return {
                    source: source,
                    items: items
                };
            }
            """

            extracted = await page.evaluate(extraction_script)
            diagnostics["extraction_source"] = extracted.get("source", "none")
            raw_items = extracted.get("items", [])
            diagnostics["dom_items_found"] = len(raw_items)

            for item in raw_items[:max_results]:
                results.append(item)

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