import os
import sys
import time
import json
import traceback
import requests
from dotenv import load_dotenv

# Menambah root path untuk import fungsi dari src/lazada_api.py
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.lazada_api import sign_lazada, generate_tracking_link

# Read local .env.local if available (Fallback to CI Secrets)
load_dotenv('.env.local')

def sanitize_value(val):
    if not val:
        return ""
    val = str(val).strip()
    if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
        val = val[1:-1]
    return val.strip()

def run_fetch_test(keyword="kucing"):
    print("==================================================")
    print("🚀 [TEST 1: FETCH / API DIRECT] Searching Lazada Product & Generating Affiliate Link")
    print("==================================================")

    app_key = sanitize_value(os.getenv("LAZADA_LiteApp_Key") or os.getenv("LAZADA_APP_KEY"))
    app_secret = sanitize_value(os.getenv("LAZADA_LiteApp_Secret") or os.getenv("LAZADA_APP_SECRET"))
    user_token = sanitize_value(os.getenv("LAZADA_USER_TOKEN"))

    if not app_key or not app_secret or not user_token:
        raise ValueError("❌ [RALAT KUNCI API]: Kunci LAZADA_APP_KEY/SECRET/USER_TOKEN tidak ditemui!")

    domain = "api.lazada.com.my"
    feed_path = "/marketing/product/feed"
    feed_url = f"https://{domain}/rest{feed_path}"

    timestamp = str(int(time.time() * 1000))
    params = {
        "app_key": app_key,
        "timestamp": timestamp,
        "sign_method": "sha256",
        "offerType": "1",
        "userToken": user_token,
        "page": "1",
        "limit": "50"
    }
    params["sign"] = sign_lazada(feed_path, params, app_secret)

    print(f"📡 Memanggil Feed API Lazada...")
    res = requests.get(feed_url, params=params, timeout=25)
    print(f"📊 HTTP Status: {res.status_code}")
    
    if res.status_code != 200:
        raise Exception(f"HTTP Error {res.status_code}: {res.text}")

    feed_json = res.json()
    if str(feed_json.get("code", "0")) != "0":
        raise Exception(f"Lazada API Error: {json.dumps(feed_json, indent=2)}")

    result_data = feed_json.get("result", {}) or feed_json.get("data", {})
    products = []
    if isinstance(result_data, dict):
        products = result_data.get("products", []) or result_data.get("data", []) or result_data.get("items", [])
    elif isinstance(result_data, list):
        products = result_data

    print(f"📦 Ditemui {len(products)} produk dari API Feed.")

    eligible_product = None
    for prod in products:
        p_id = str(prod.get("productId") or prod.get("product_id") or prod.get("id") or "")
        p_name = prod.get("productName") or prod.get("title") or prod.get("name") or ""
        
        # Semakan Kadar Komisen (Mesti >= 20%)
        raw_comm = prod.get("commissionRate") or prod.get("commCommissionRate") or prod.get("commission") or 0
        try:
            comm_rate = float(str(raw_comm).replace("%", ""))
            if comm_rate < 1.0:  # Contoh 0.20 = 20%
                comm_rate *= 100
        except ValueError:
            comm_rate = 0.0

        if comm_rate >= 20.0 and p_id:
            eligible_product = {
                "id": p_id,
                "title": p_name,
                "commission_rate": comm_rate
            }
            break

    if not eligible_product:
        print("⚠️ Tiada produk ditemui dengan komisen >= 20% dalam sampel feed ini. Memilih produk komisen tertinggi...")
        if products:
            prod = products[0]
            eligible_product = {
                "id": str(prod.get("productId") or prod.get("product_id") or prod.get("id")),
                "title": prod.get("productName") or prod.get("title") or "Produk Lazada",
                "commission_rate": 0.0
            }
        else:
            raise Exception("❌ [RALAT DATA]: Tiada produk yang dipulangkan oleh API Lazada.")

    print(f"✅ Produk Terpilih: {eligible_product['title']} (ID: {eligible_product['id']})")
    print(f"💰 Kadar Komisen: {eligible_product['commission_rate']}%")

    # Tukar kepada Tracking Link Affiliate Rasmi
    affiliate_link = generate_tracking_link(app_key, app_secret, user_token, eligible_product['id'])
    if not affiliate_link:
        raise Exception("❌ Gagal menjana Tracking Link Affiliate dari Lazada API!")

    print(f"🔗 Link Affiliate Rasmi: {affiliate_link}")
    print("🟢 [SUCCESS: FETCH TEST PASSED]")

if __name__ == "__main__":
    try:
        run_fetch_test()
    except Exception as e:
        print("\n💥 [TEST 1 GAGAL] Laporan Ralat Terperinci:")
        traceback.print_exc()
        sys.exit(1)