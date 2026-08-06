import os
import sys
import time
import requests
from collections import defaultdict
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

def discover_lazada_categories():
    print("==================================================")
    print("🔍 [CATEGORY DISCOVERY] Imbasan ID Kategori L1 Lazada")
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

    categories_found = defaultdict(list)
    total_products_scanned = 0

    print("📡 Memulakan imbasan merentasi offerType dan halaman feed...\n")

    for offer_type in ["1", "2", "3"]:
        for page in range(1, 4):  # Imbas halaman 1 hingga 3
            timestamp = str(int(time.time() * 1000))
            feed_params = {
                "app_key": app_key,
                "timestamp": timestamp,
                "sign_method": "sha256",
                "offerType": str(offer_type),
                "userToken": user_token,
                "page": str(page),
                "limit": "20"
            }
            feed_params["sign"] = sign_lazada(feed_path, feed_params, app_secret)

            try:
                res = requests.get(feed_url, params=feed_params, timeout=20)
                if res.status_code != 200:
                    continue

                feed_json = res.json()
                if str(feed_json.get("code", "0")) != "0":
                    continue

                result_data = feed_json.get("result", {}) or feed_json.get("data", {})
                prods = []
                if isinstance(result_data, dict):
                    prods = result_data.get("products", []) or result_data.get("data", []) or result_data.get("items", [])
                elif isinstance(result_data, list):
                    prods = result_data

                for prod in prods:
                    total_products_scanned += 1
                    cat_id = str(prod.get("categoryL1") or "Unknown").strip()
                    title = prod.get("productName") or prod.get("title") or "Tiada Tajuk"
                    price = prod.get("discountPrice") or prod.get("price") or 0.0

                    # Simpan maksimum 3 contoh produk per kategori
                    if len(categories_found[cat_id]) < 3:
                        categories_found[cat_id].append({"title": title, "price": price})

            except Exception as e:
                print(f"⚠️ Ralat semasa imbasan (offerType={offer_type}, page={page}): {e}")

    print("==================================================")
    print(f"📊 DAPATAN IMBASAN: {len(categories_found)} Kategori Unik Ditemui (Dari {total_products_scanned} produk)")
    print("==================================================\n")

    for cat_id, items in categories_found.items():
        print(f"🏷️  CategoryL1 ID: [{cat_id}]")
        for idx, item in enumerate(items, 1):
            print(f"    {idx}. RM {item['price']} - {item['title'][:60]}...")
        print("-" * 50)

if __name__ == "__main__":
    discover_lazada_categories()