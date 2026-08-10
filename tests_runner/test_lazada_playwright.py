import os
import sys
import time
import json
import traceback
import requests
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

def run_playwright_test():
    print("==================================================")
    print("🚀 [TEST 3: PLAYWRIGHT] Python Browser Automation & Affiliate Link")
    print("==================================================")

    app_key = sanitize_value(os.getenv("LAZADA_LiteApp_Key") or os.getenv("LAZADA_APP_KEY"))
    app_secret = sanitize_value(os.getenv("LAZADA_LiteApp_Secret") or os.getenv("LAZADA_APP_SECRET"))
    user_token = sanitize_value(os.getenv("LAZADA_USER_TOKEN"))

    if not app_key or not app_secret or not user_token:
        raise ValueError("❌ [RALAT KUNCI API]: Kunci LAZADA_APP_KEY/SECRET/USER_TOKEN tidak ditemui!")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-setuid-sandbox"])
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        print("🌐 [Playwright] Navigasi ke Lazada...")
        page.goto("https://www.lazada.com.my/catalog/?q=kucing", wait_until="domcontentloaded", timeout=30000)

        # Cari pautan produk
        links = page.locator("a[href*='-i']").all()
        found_product_id = None

        for l in links:
            href = l.get_attribute("href") or ""
            if "lazada.com.my/products/" in href and "-i" in href:
                import re
                match = re.search(r"-i(\d+)", href)
                if match:
                    found_product_id = match.group(1)
                    break

        browser.close()

        if not found_product_id:
            raise Exception("❌ Playwright gagal menjumpai sebarang Product ID dari carian web Lazada!")

        print(f"✅ Product ID Ditemui melalui Playwright: {found_product_id}")

        # Penjanaan Tracking Link Affiliate
        affiliate_link = generate_tracking_link(app_key, app_secret, user_token, found_product_id)
        if not affiliate_link:
            raise Exception("❌ Gagal menjana Tracking Link Affiliate untuk produk Playwright!")

        print(f"🔗 Link Affiliate Rasmi: {affiliate_link}")
        print("🟢 [SUCCESS: PLAYWRIGHT TEST PASSED]")

if __name__ == "__main__":
    try:
        run_playwright_test()
    except Exception as e:
        print("\n💥 [TEST 3 GAGAL] Laporan Ralat Terperinci:")
        traceback.print_exc()
        sys.exit(1)