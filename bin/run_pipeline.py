import os
import sys
import time
import json
import random
import traceback
import requests
from dotenv import load_dotenv

# Menambah direktori utama ke sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.lazada_api import sign_lazada
from src.redis_db import is_product_posted, mark_product_posted
from src.vector_db import is_similar_product_posted, mark_vector_posted
from src.ai_persona import generate_caption
from src.telegram_bot import send_photo_to_telegram

# Muat turun pemboleh ubah persekitaran (.env.local)
load_dotenv('.env.local')

def sanitize_value(val):
    if not val:
        return ""
    val = str(val).strip()
    if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
        val = val[1:-1]
    return val.strip()

def normalize_image_url(url):
    """Memastikan URL imej mempunyai skema https: yang sah untuk Telegram API."""
    if not url:
        return ""
    url = str(url).strip()
    if url.startswith("//"):
        return f"https:{url}"
    elif not url.startswith("http"):
        return f"https://{url}"
    return url

# Kategori Sasaran Rasmi Kekeluargaan & Surirumah
TARGET_CATEGORIES = [
    "10100539",  # Keperluan Rumah & Pembersihan Dapur
    "1438",      # Penjagaan Kulit & Kecantikan Wanita
    "3752",      # Makanan, Minuman & Barangan Bayi / Kanak-kanak
    "10000343"   # Barangan Dapur & Bekas Makanan
]

# Senarai Hitam Strict (Non-Halal, Alkohol, Promo Fake/GWP, Barangan Mewah/Bukan Persona)
BLACKLIST_KEYWORDS = [
    # Non-Halal / Alkohol / Babi
    "whisky", "whiskey", "liquor", "wine", "vodka", "alcohol", "beer", "rum",
    "pork", "lard", "bacon", "ham", "non-halal", "non halal", "tokek", "arak",
    # Promo Palsu / GWP / Gift
    "gwp", "not for sale", "gift not for sale", "free gift", "sample",
    "blind box", "tester", "prize", "lazland only", "cgwp", "voucher", "e-voucher",
    # Barangan Mewah / Industri / Bukan Persona Surirumah
    "coin", "silver", "gold", "pendant", "caravan", "campervan",
    "machine", "testing", "sneakers", "jade", "watch", "quartz", "automatic",
    "diamond", "luxury", "machinery"
]

def is_title_blacklisted(title):
    """Menyemak sama ada tajuk produk mengandungi sebarang kata kunci disekat."""
    lower_title = str(title or "").lower()
    for kw in BLACKLIST_KEYWORDS:
        if kw in lower_title:
            return True, kw
    return False, ""

def fetch_targeted_lazada_candidates(app_key, app_secret, user_token, max_items=100):
    """
    Menarik calon produk secara khusus daripada Kategori Kekeluargaan / Dapur / Bayi / Wanita
    menggunakan parameter categoryL1 rasmi Lazada API Feed.
    """
    domain = "api.lazada.com.my"
    feed_path = "/marketing/product/feed"
    feed_url = f"https://{domain}/rest{feed_path}"
    
    candidates = []
    seen_ids = set()
    
    # Rawakkan kategori dan halaman untuk kepelbagaian produk
    categories = list(TARGET_CATEGORIES)
    random.shuffle(categories)
    pages = [1, 2, 3]
    random.shuffle(pages)

    for cat_id in categories:
        for page in pages:
            if len(candidates) >= max_items:
                break
                
            timestamp = str(int(time.time() * 1000))
            feed_params = {
                "app_key": str(app_key).strip(),
                "timestamp": timestamp,
                "sign_method": "sha256",
                "offerType": "1",
                "userToken": str(user_token).strip(),
                "categoryL1": str(cat_id),
                "page": str(page),
                "limit": "20"
            }
            feed_params["sign"] = sign_lazada(feed_path, feed_params, app_secret)

            try:
                res = requests.get(feed_url, params=feed_params, timeout=25)
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
                    p_id = str(prod.get("productId") or prod.get("product_id") or prod.get("id") or "").strip()
                    p_name = prod.get("productName") or prod.get("title") or prod.get("name") or ""
                    pics = prod.get("pictures") or prod.get("image_url") or prod.get("image") or prod.get("picUrl")

                    img_url = ""
                    if isinstance(pics, list) and len(pics) > 0:
                        img_url = pics[0]
                    elif isinstance(pics, str):
                        img_url = pics

                    img_url = normalize_image_url(img_url)

                    if p_id and img_url and p_id not in seen_ids:
                        seen_ids.add(p_id)
                        candidates.append({
                            "id": p_id,
                            "title": p_name,
                            "image": img_url,
                            "discountPrice": prod.get("discountPrice"),
                            "price": prod.get("price") or prod.get("originalPrice"),
                            "outOfStock": prod.get("outOfStock"),
                            "categoryL1": cat_id,
                            "desc": f"Promosi khas {p_name} di Lazada."
                        })
                        if len(candidates) >= max_items:
                            break
            except Exception as e:
                print(f"⚠️ [FEED WARN] Gagal menarik feed (Category={cat_id}, Page={page}): {e}")
                continue

    return candidates

def generate_tracking_link(app_key, app_secret, user_token, product_id):
    """Menjana pautan affiliate tracking rasmi untuk Product ID terpilih."""
    domain = "api.lazada.com.my"
    base_url = f"https://{domain}/rest"
    
    # 1. /marketing/product/link
    link_path = "/marketing/product/link"
    link_url = f"{base_url}{link_path}"
    timestamp = str(int(time.time() * 1000))
    
    link_params = {
        "app_key": str(app_key).strip(),
        "timestamp": timestamp,
        "sign_method": "sha256",
        "userToken": str(user_token).strip(),
        "productId": str(product_id)
    }
    link_params["sign"] = sign_lazada(link_path, link_params, app_secret)

    try:
        res = requests.get(link_url, params=link_params, timeout=25)
        if res.status_code == 200:
            link_json = res.json()
            if str(link_json.get("code", "0")) == "0":
                res_obj = link_json.get("result", {})
                if isinstance(res_obj, dict):
                    data_obj = res_obj.get("data", {})
                    if isinstance(data_obj, dict):
                        link = data_obj.get("trackingLink") or data_obj.get("link")
                        if link:
                            return link
                if link_json.get("trackingLink"):
                    return link_json.get("trackingLink")
    except Exception:
        pass

    # 2. Fallback /marketing/getlink
    getlink_path = "/marketing/getlink"
    getlink_url = f"{base_url}{getlink_path}"
    timestamp_gl = str(int(time.time() * 1000))

    getlink_params = {
        "app_key": str(app_key).strip(),
        "timestamp": timestamp_gl,
        "sign_method": "sha256",
        "userToken": str(user_token).strip(),
        "inputType": "productId",
        "inputValue": str(product_id),
        "subId1": "telegram_channel"
    }
    getlink_params["sign"] = sign_lazada(getlink_path, getlink_params, app_secret)

    try:
        res_gl = requests.get(getlink_url, params=getlink_params, timeout=25)
        if res_gl.status_code == 200:
            gl_json = res_gl.json()
            if str(gl_json.get("code", "0")) == "0":
                res_obj = gl_json.get("result", {})
                if isinstance(res_obj, dict):
                    data_obj = res_obj.get("data", {})
                    if isinstance(data_obj, dict):
                        info_list = data_obj.get("productBatchGetLinkInfoList", [])
                        if info_list and isinstance(info_list, list):
                            return info_list[0].get("regularPromotionLink") or info_list[0].get("promotionLink")
    except Exception:
        pass

    return ""

def evaluate_product(prod):
    """
    Menilai kelayakan produk mengikut:
    1. Status outOfStock
    2. Semakan Kata Kunci Disekat (Non-Halal, GWP, dll.)
    3. Julat Harga Idaman RM 10.00 - RM 1000.00
    """
    if prod.get("outOfStock") is True or str(prod.get("outOfStock")).lower() == "true":
        return False, 0.0, "Habis Stok (outOfStock)"

    # 1. Semak kata kunci disekat
    is_blacklisted, kw = is_title_blacklisted(prod.get("title"))
    if is_blacklisted:
        return False, 0.0, f"Ditolak Kata Kunci Disekat ('{kw}')"

    # 2. Semak Harga Mentah (Ringgit Malaysia)
    raw_p = prod.get("discountPrice") if prod.get("discountPrice") is not None else prod.get("price")
    price_val = 0.0
    try:
        price_val = float(raw_p or 0.0)
    except (ValueError, TypeError):
        return False, 0.0, "Format Harga Tidak Sah"

    # Tapis harga dummy penjual (> RM 10,000)
    if price_val >= 10000.0:
        return False, price_val, "Harga Dummy/Out of Stock (> RM 10,000)"

    # Julat Standard RM 10.00 - RM 1000.00
    if 10.0 <= price_val <= 1000.0:
        return True, price_val, "Harga Lulus"

    return False, price_val, "Luar Julat RM10-RM1000"

def main():
    print("\n==================================================")
    print("🚀 [FULL PIPELINE] Automasi Produk Real, Guardrails & Telegram")
    print("==================================================")

    # 1. Pembacaan Pemboleh Ubah Persekitaran
    TELEGRAM_BOT_TOKEN = sanitize_value(os.getenv("TELEGRAM_BOT_TOKEN"))
    TELEGRAM_CHAT_ID = sanitize_value(os.getenv("TELEGRAM_CHAT_ID"))

    OPENROUTER_BASE_URL = sanitize_value(os.getenv("OPENROUTER_BASE_URL"))
    OPENROUTER_MODEL = sanitize_value(os.getenv("OPENROUTER_MODEL"))
    OPENROUTER_API_KEY = sanitize_value(os.getenv("OPENROUTER_API_KEY"))

    LAZADA_APP_KEY = sanitize_value(os.getenv("LAZADA_LiteApp_Key") or os.getenv("LAZADA_APP_KEY"))
    LAZADA_APP_SECRET = sanitize_value(os.getenv("LAZADA_LiteApp_Secret") or os.getenv("LAZADA_APP_SECRET"))
    LAZADA_USER_TOKEN = sanitize_value(os.getenv("LAZADA_USER_TOKEN"))

    UPSTASH_REDIS_REST_URL = sanitize_value(os.getenv("UPSTASH_REDIS_REST_URL"))
    UPSTASH_REDIS_REST_TOKEN = sanitize_value(os.getenv("UPSTASH_REDIS_REST_TOKEN"))

    UPSTASH_VECTOR_REST_URL = sanitize_value(os.getenv("UPSTASH_VECTOR_REST_URL") or os.getenv("UPSTASH_VECTOR_ENDPOINT_URL"))
    UPSTASH_VECTOR_REST_TOKEN = sanitize_value(os.getenv("UPSTASH_VECTOR_REST_TOKEN"))

    # Validasi Kunci Asas
    missing_keys = []
    if not LAZADA_APP_KEY: missing_keys.append("LAZADA_LiteApp_Key / LAZADA_APP_KEY")
    if not LAZADA_APP_SECRET: missing_keys.append("LAZADA_LiteApp_Secret / LAZADA_APP_SECRET")
    if not LAZADA_USER_TOKEN: missing_keys.append("LAZADA_USER_TOKEN")
    if not TELEGRAM_BOT_TOKEN: missing_keys.append("TELEGRAM_BOT_TOKEN")
    if not TELEGRAM_CHAT_ID: missing_keys.append("TELEGRAM_CHAT_ID")

    if missing_keys:
        print(f"🔴 [RALAT KRITIKAL]: Kunci persekitaran tidak lengkap di .env.local: {missing_keys}")
        sys.exit(1)

    # 2. Tarik Calon Produk Daripada Kategori Sasaran Kekeluargaan
    print("\n1️⃣ Meminta calon produk dari Kategori Dapur, Bayi, Wanita & Rumah...")
    candidates = fetch_targeted_lazada_candidates(LAZADA_APP_KEY, LAZADA_APP_SECRET, LAZADA_USER_TOKEN, max_items=100)

    if not candidates:
        print("🔴 [RALAT KRITIKAL]: Lazada Feed API memulangkan 0 produk merentasi kategori sasaran.")
        sys.exit(1)

    print(f"🟢 [FEED OK]: Berjaya menarik {len(candidates)} calon produk untuk dinilai.")

    # Rawakkan senarai calon produk
    random.shuffle(candidates)

    stats = {
        "skipped_guardrails": 0,
        "skipped_redis": 0,
        "skipped_vector": 0,
        "skipped_link": 0,
        "skipped_ai": 0,
        "total_evaluated": 0
    }

    selected_product = None
    affiliate_link = ""
    ai_caption = ""

    # 3. Gelung Iterasi & Penapisan 3 Lapisan
    print("\n2️⃣ Memulakan Gelung Semakan 3 Lapisan (Guardrails -> Redis -> Vector DB)...")
    for prod in candidates:
        stats["total_evaluated"] += 1
        p_id = prod["id"]
        p_title = prod["title"]

        # LAPISAN 1: Semakan Guardrails (Harga RM10-RM1000, Non-Halal, GWP Check)
        is_valid, active_price, reason = evaluate_product(prod)
        if not is_valid:
            stats["skipped_guardrails"] += 1
            print(f"  ⏩ [GUARDRAIL FILTER] #{stats['total_evaluated']} ID {p_id}: RM {active_price:.2f} ({reason}). Langkau.")
            continue

        # LAPISAN 2: Semakan Upstash Redis (Duplikasi Produk Tepat 7 Hari)
        if UPSTASH_REDIS_REST_URL and UPSTASH_REDIS_REST_TOKEN:
            if is_product_posted(UPSTASH_REDIS_REST_URL, UPSTASH_REDIS_REST_TOKEN, p_id, p_title):
                stats["skipped_redis"] += 1
                print(f"  ⏩ [REDIS FILTER] #{stats['total_evaluated']} ID {p_id}: Pernah dipos dalam 7 hari. Langkau.")
                continue

        # LAPISAN 3: Semakan Upstash Vector DB (Keserupaan Semantik 48 Jam)
        if UPSTASH_VECTOR_REST_URL and UPSTASH_VECTOR_REST_TOKEN:
            if is_similar_product_posted(UPSTASH_VECTOR_REST_URL, UPSTASH_VECTOR_REST_TOKEN, p_title):
                stats["skipped_vector"] += 1
                print(f"  ⏩ [VECTOR FILTER] #{stats['total_evaluated']} ID {p_id}: Kategori/fungsi serupa dipos < 48 jam. Langkau.")
                continue

        # Penjanaan Tracking Link Sebenar
        print(f"\n  🎯 [LULUS TAPISAN] #{stats['total_evaluated']} ID {p_id} ('{p_title[:40]}...') Harga: RM {active_price:.2f}")
        print("  🔗 Menjana Affiliate Tracking Link...")
        aff_link = generate_tracking_link(LAZADA_APP_KEY, LAZADA_APP_SECRET, LAZADA_USER_TOKEN, p_id)

        if not aff_link:
            stats["skipped_link"] += 1
            print(f"  ⚠️ Gagal mendapat tracking link untuk ID {p_id}. Mencuba produk seterusnya...")
            continue

        # Penjanaan AI Caption
        print("  📝 Menjana Ayat Promosi AI Persona...")
        ai_ok, caption = generate_caption(OPENROUTER_BASE_URL, OPENROUTER_MODEL, OPENROUTER_API_KEY, p_title, prod["desc"])

        if not ai_ok or not caption:
            stats["skipped_ai"] += 1
            print(f"  ⚠️ Gagal menjana AI Caption: {caption}. Mencuba produk seterusnya...")
            continue

        # Jika semua langkah lulus
        selected_product = prod
        affiliate_link = aff_link
        ai_caption = caption
        break

    # 4. Semakan Jika Tiada Produk Lulus
    if not selected_product:
        print("\n==================================================")
        print("🔴 [RALAT PIPELINE]: Tiada produk lulus dari calon produk!")
        print("==================================================")
        print(f"📊 Laporan Penapisan:")
        print(f"   • Jumlah Dinilai         : {stats['total_evaluated']}")
        print(f"   • Ditolak Guardrails     : {stats['skipped_guardrails']}")
        print(f"   • Ditolak Redis (7 Hari) : {stats['skipped_redis']}")
        print(f"   • Ditolak Vector DB (48h): {stats['skipped_vector']}")
        print(f"   • Gagal Link Affiliate   : {stats['skipped_link']}")
        print(f"   • Gagal AI Caption       : {stats['skipped_ai']}")
        sys.exit(1)

    # 5. Penghantaran ke Telegram Bot
    print("\n3️⃣ Menghantar Gambar + Caption + Link ke Telegram...")
    tg_ok, tg_res = send_photo_to_telegram(
        TELEGRAM_BOT_TOKEN,
        TELEGRAM_CHAT_ID,
        ai_caption,
        selected_product["image"],
        affiliate_link
    )

    if tg_ok:
        print("\n==================================================")
        print("🟢 [SUCCESS 100%] PRODUK SEBENAR BERJAYA DIPOS KE TELEGRAM!")
        print("==================================================")
        print(f"📌 Product ID     : {selected_product['id']}")
        print(f"📌 Tajuk Produk   : {selected_product['title']}")
        print(f"🖼️ URL Gambar     : {selected_product['image']}")
        print(f"🔗 Link Affiliate : {affiliate_link}")
        print("==================================================\n")

        # 6. Rekod Kunci Baharu ke Redis & Vector DB
        if UPSTASH_REDIS_REST_URL and UPSTASH_REDIS_REST_TOKEN:
            mark_product_posted(UPSTASH_REDIS_REST_URL, UPSTASH_REDIS_REST_TOKEN, selected_product["id"], selected_product["title"])

        if UPSTASH_VECTOR_REST_URL and UPSTASH_VECTOR_REST_TOKEN:
            mark_vector_posted(UPSTASH_VECTOR_REST_URL, UPSTASH_VECTOR_REST_TOKEN, selected_product["id"], selected_product["title"])

    else:
        print(f"\n🔴 [TELEGRAM FAIL]: Gagal menghantar ke Telegram: {tg_res}")
        sys.exit(1)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("\n💥 [PIPELINE ERROR]: Ralat tidak dijangka berlaku.")
        traceback.print_exc()
        sys.exit(1)