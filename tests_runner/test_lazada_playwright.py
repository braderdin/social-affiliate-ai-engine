import os
import sys
import time
import json
import traceback
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.lazada_api import sign_lazada, generate_tracking_link

load_dotenv('.env.local')

def sanitize_value(val):
    if not val:
        return ""
    val = str(val).strip()
    if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
        val = val[1:-1]
    return val.strip()

def run_playwright_stealth_test():
    print("==================================================")
    print("🚀 [TEST 3B: PLAYWRIGHT STEALTH] Testing Mobile Web & Anti-Bot Bypass")
    print("==================================================")

    app_key = sanitize_value(os.getenv("LAZADA_LiteApp_Key") or os.getenv("LAZADA_APP_KEY"))
    app_secret = sanitize_value(os.getenv("LAZADA_LiteApp_Secret") or os.getenv("LAZADA_APP_SECRET"))
    user_token = sanitize_value(os.getenv("LAZADA_USER_TOKEN"))

    with sync_playwright() as p:
        # 1. Guna Peranti Mobil (iPhone 13 / Android) untuk mengelak Akamai Desktop WAF
        iphone = p.devices['iPhone 13']
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-blink-features=AutomationControlled", # Sorok status automation
                "--disable-web-security"
            ]
        )

        # 2. Buka context dengan tetapan Mobile Stealth
        context = browser.new_context(
            **iphone,
            locale="ms-MY",
            timezone_id="Asia/Kuala_Lumpur",
            extra_http_headers={
                "Accept-Language": "ms-MY,ms;q=0.9,en-US;q=0.8,en;q=0.7",
                "Sec-Ch-Ua-Mobile": "?1",
                "Sec-Fetch-Site": "same-origin",
            }
        )

        # 3. Inject JavaScript untuk padam petunjuk WebDriver
        page = context.new_page()
        page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            window.chrome = { runtime: {} };
        """)

        found_product_id = None

        # 4. Tangkap JSON Response dari Internal Network Request
        def handle_response(response):
            nonlocal found_product_id
            if "search" in response.url or "catalog" in response.url or "api" in response.url:
                try:
                    if "json" in response.headers.get("content-type", ""):
                        data = response.json()
                        # Cari itemId / productId di dalam JSON response
                        json_str = json.dumps(data)
                        import re
                        matches = re.findall(r'"itemId":\s*"(\d+)"', json_str) or re.findall(r'"productId":\s*"(\d+)"', json_str)
                        if matches:
                            found_product_id = matches[0]
                except Exception:
                    pass

        page.on("response", handle_response)

        print("🌐 [Playwright Stealth] Membuka Lazada Mobile Search...")
        # Guna Mobile Search URL
        page.goto("https://m.lazada.com.my/h5/search/index?q=kucing", wait_until="networkidle", timeout=35000)

        # Fallback: Jika network intercept tak jumpa, cuba cari pautan HTML Mobile
        if not found_product_id:
            print("🔍 Mencari pautan produk dari DOM Mobile...")
            links = page.locator("a[href*='i']").all()
            for l in links:
                href = l.get_attribute("href") or ""
                import re
                match = re.search(r"i(\d+)\.html", href) or re.search(r"-i(\d+)", href)
                if match:
                    found_product_id = match.group(1)
                    break

        browser.close()

        if not found_product_id:
            raise Exception("❌ [STEALTH FAILED]: Pelayan Lazada masih mengesan IP Cloud GitHub Actions & menyekat halaman.")

        print(f"✅ Product ID Berjaya Ditemui: {found_product_id}")

        # Penjanaan Tracking Link Affiliate Rasmi
        affiliate_link = generate_tracking_link(app_key, app_secret, user_token, found_product_id)
        print(f"🔗 Link Affiliate Rasmi: {affiliate_link}")
        print("🟢 [SUCCESS: PLAYWRIGHT STEALTH TEST PASSED]")

if __name__ == "__main__":
    try:
        run_playwright_stealth_test()
    except Exception as e:
        print("\n💥 [TEST STEALTH GAGAL] Laporan Ralat Terperinci:")
        traceback.print_exc()
        sys.exit(1)