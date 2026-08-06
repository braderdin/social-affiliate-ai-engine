import os
import sys
import time
import json
import requests
from dotenv import load_dotenv

# Menambah direktori utama ke sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.lazada_api import sign_lazada

# Muat turun pemboleh ubah persekitaran (.env.local)
load_dotenv('.env.local')

def sanitize_value(val):
    if not val:
        return ""
    val = str(val).strip()
    if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
        val = val[1:-1]
    return val.strip()

def inspect_raw_lazada_feed():
    print("==================================================")
    print("🔍 [RAW DIAGNOSTIC] Inspecting Lazada Product Feed JSON")
    print("==================================================\n")

    app_key = sanitize_value(os.getenv("LAZADA_LiteApp_Key") or os.getenv("LAZADA_APP_KEY"))
    app_secret = sanitize_value(os.getenv("LAZADA_LiteApp_Secret") or os.getenv("LAZADA_APP_SECRET"))
    user_token = sanitize_value(os.getenv("LAZADA_USER_TOKEN"))

    if not app_key or not app_secret or not user_token:
        print("🔴 [RALAT]: Kredensial Lazada tidak lengkap di dalam .env.local!")
        sys.exit(1)

    domain = "api.lazada.com.my"
    feed_path = "/marketing/product/feed"
    feed_url = f"https://{domain}/rest{feed_path}"

    timestamp = str(int(time.time() * 1000))
    feed_params = {
        "app_key": app_key,
        "timestamp": timestamp,
        "sign_method": "sha256",
        "offerType": "1",
        "userToken": user_token,
        "page": "1",
        "limit": "15"
    }
    feed_params["sign"] = sign_lazada(feed_path, feed_params, app_secret)

    print(f"📡 Memanggil Lazada Feed API (offerType=1, limit=15)...")
    try:
        res = requests.get(feed_url, params=feed_params, timeout=25)
        print(f"📊 HTTP Status Code : {res.status_code}")

        feed_json = res.json()
        print(f"📜 API Response Code: {feed_json.get('code')}\n")

        result_data = feed_json.get("result", {}) or feed_json.get("data", {})
        prods = []
        if isinstance(result_data, dict):
            prods = result_data.get("products", []) or result_data.get("data", []) or result_data.get("items", [])
        elif isinstance(result_data, list):
            prods = result_data

        if not prods:
            print("⚠️ API memulangkan 0 produk mentah.")
            return

        print(f"🟢 Ditemui {len(prods)} produk mentah. Berikut analisis medan penting:\n")

        for idx, prod in enumerate(prods, start=1):
            p_id = prod.get("productId") or prod.get("product_id") or prod.get("id")
            p_name = prod.get("productName") or prod.get("title") or prod.get("name")
            disc_p = prod.get("discountPrice")
            orig_p = prod.get("price") or prod.get("originalPrice")
            cat_l1 = prod.get("categoryL1")
            stock_status = prod.get("outOfStock")

            print(f"--------------------------------------------------")
            print(f"📌 Produk #{idx}")
            print(f"   • Product ID    : {p_id}")
            print(f"   • Tajuk Produk  : {p_name}")
            print(f"   • discountPrice : {disc_p} (Tipe Data: {type(disc_p).__name__})")
            print(f"   • price/orig    : {orig_p} (Tipe Data: {type(orig_p).__name__})")
            print(f"   • categoryL1    : {cat_l1} (Tipe Data: {type(cat_l1).__name__})")
            print(f"   • outOfStock    : {stock_status}")
            print(f"--------------------------------------------------")

    except Exception as e:
        print(f"💥 [RALAT EXCEPTION]: {e}")

if __name__ == "__main__":
    inspect_raw_lazada_feed()