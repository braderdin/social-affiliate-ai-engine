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

# Kategori sasaran rasmi persona Cikgu / Surirumah (Dapur, Bayi, Wanita)
TARGET_CATEGORIES = {
    "10100539": "Keperluan Rumah & Pembersihan Dapur",
    "1438": "Penjagaan Kulit & Kecantikan Wanita",
    "3752": "Makanan, Minuman & Barangan Bayi",
    "10000343": "Barangan Dapur & Bekas Makanan"
}

# Senarai hitam kata kunci bukan barangan surirumah/dapur
BLACKLIST_KEYWORDS = [
    "coin", "silver", "gold", "pendant", "caravan", "campervan",
    "machine", "testing", "e-voucher", "sneakers", "jade", "voucher",
    "gift not for sale", "prize", "lazland only", "cgwp"
]

def is_title_valid(title):
    """Menyemak sama ada tajuk produk mengandungi kata kunci disekat."""
    lower_title = str(title or "").lower()
    for kw in BLACKLIST_KEYWORDS:
        if kw in lower_title:
            return False, f"Mengandungi kata kunci disekat: '{kw}'"
    return True, "OK"

def test_category_fetch():
    print("==================================================")
    print("🔍 [CATEGORY TEST] Imbasan Kategori Sasaran Cikgu/Surirumah")
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

    total_passed = 0
    total_evaluated = 0

    for cat_id, cat_name in TARGET_CATEGORIES.items():
        print(f"📦 Imbasan Kategori ID [{cat_id}]: {cat_name}...")
        
        timestamp = str(int(time.time() * 1000))
        feed_params = {
            "app_key": app_key,
            "timestamp": timestamp,
            "sign_method": "sha256",
            "offerType": "1",
            "userToken": user_token,
            "categoryL1": str(cat_id),
            "page": "1",
            "limit": "10"
        }
        feed_params["sign"] = sign_lazada(feed_path, feed_params, app_secret)

        try:
            res = requests.get(feed_url, params=feed_params, timeout=25)
            feed_json = res.json()

            if res.status_code != 200 or str(feed_json.get("code", "0")) != "0":
                print(f"   ⚠️ Gagal menarik kategori {cat_id}: {feed_json.get('message')}\n")
                continue

            result_data = feed_json.get("result", {}) or feed_json.get("data", {})
            prods = []
            if isinstance(result_data, dict):
                prods = result_data.get("products", []) or result_data.get("data", []) or result_data.get("items", [])
            elif isinstance(result_data, list):
                prods = result_data

            if not prods:
                print("   ⚠️ Tiada produk dipulangkan untuk kategori ini.\n")
                continue

            print(f"   🟢 Ditemui {len(prods)} produk. Memulakan penilaian harga & tajuk...\n")

            for idx, prod in enumerate(prods, start=1):
                total_evaluated += 1
                p_id = prod.get("productId") or prod.get("product_id") or prod.get("id")
                p_name = prod.get("productName") or prod.get("title") or prod.get("name")
                disc_p = prod.get("discountPrice")
                orig_p = prod.get("price") or prod.get("originalPrice")

                raw_price = disc_p if disc_p is not None else orig_p
                price_val = 0.0
                try:
                    price_val = float(raw_price or 0.0)
                except (ValueError, TypeError):
                    price_val = 0.0

                # 1. Semakan Julat Harga (RM 2.00 - RM 1000.00)
                price_ok = (2.0 <= price_val <= 1000.0)
                price_status = "LULUS" if price_ok else f"DITOLAK (RM {price_val:.2f} luar julat RM2-RM1000)"

                # 2. Semakan Tajuk (Kata Kunci Disekat)
                title_ok, title_msg = is_title_valid(p_name)
                title_status = "LULUS" if title_ok else f"DITOLAK ({title_msg})"

                is_valid = price_ok and title_ok

                if is_valid:
                    total_passed += 1
                    print(f"   ✅ [SANGAT SUITABLE] #{idx} ID {p_id}")
                else:
                    print(f"   ❌ [MELANGKAU]     #{idx} ID {p_id}")

                print(f"      • Tajuk  : {p_name}")
                print(f"      • Harga  : RM {price_val:.2f}")
                print(f"      • Status Harga : {price_status}")
                print(f"      • Status Tajuk : {title_status}\n")

        except Exception as e:
            print(f"   💥 [RALAT EXCEPTION]: {e}\n")

    print("==================================================")
    print(f"📊 SUMMARY: {total_passed} daripada {total_evaluated} produk LULUS tapisan persona & harga.")
    print("==================================================")

if __name__ == "__main__":
    test_category_fetch()