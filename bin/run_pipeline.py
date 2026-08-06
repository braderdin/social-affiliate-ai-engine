import os
import sys
import json
import traceback
from dotenv import load_dotenv

# Menambah direktori utama ke sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.lazada_api import get_lazada_product_candidates, generate_tracking_link
from src.ai_persona import generate_caption
from src.telegram_bot import send_photo_to_telegram
from src.redis_db import is_product_posted, mark_product_posted
from src.vector_db import is_similar_product_posted, mark_vector_posted

load_dotenv('.env.local')

def sanitize_value(val):
    if not val:
        return ""
    val = str(val).strip()
    if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
        val = val[1:-1]
    return val.strip()

def main():
    print("\n==================================================")
    print("🚀 [FULL PIPELINE] Automasi Produk Real & Telegram")
    print("==================================================")
    
    # Pembacaan Pemboleh Ubah Persekitaran (.env.local / GitHub Secrets)
    TELEGRAM_BOT_TOKEN = sanitize_value(os.getenv("TELEGRAM_BOT_TOKEN"))
    TELEGRAM_CHAT_ID = sanitize_value(os.getenv("TELEGRAM_CHAT_ID"))
    
    OPENROUTER_BASE_URL = sanitize_value(os.getenv("OPENROUTER_BASE_URL"))
    OPENROUTER_MODEL = sanitize_value(os.getenv("OPENROUTER_MODEL"))
    OPENROUTER_API_KEY = sanitize_value(os.getenv("OPENROUTER_API_KEY"))
    
    LAZADA_APP_KEY = sanitize_value(os.getenv("LAZADA_LiteApp_Key") or os.getenv("LAZADA_APP_KEY"))
    LAZADA_APP_SECRET = sanitize_value(os.getenv("LAZADA_LiteApp_Secret") or os.getenv("LAZADA_APP_SECRET"))
    LAZADA_USER_TOKEN = sanitize_value(os.getenv("LAZADA_USER_TOKEN"))
    LAZADA_MEMBER_ID = sanitize_value(os.getenv("LAZADA_MEMBER_ID"))
    
    UPSTASH_REDIS_REST_URL = sanitize_value(os.getenv("UPSTASH_REDIS_REST_URL"))
    UPSTASH_REDIS_REST_TOKEN = sanitize_value(os.getenv("UPSTASH_REDIS_REST_TOKEN"))

    UPSTASH_VECTOR_REST_URL = sanitize_value(
        os.getenv("UPSTASH_VECTOR_REST_URL") or os.getenv("UPSTASH_VECTOR_ENDPOINT_URL")
    )
    UPSTASH_VECTOR_REST_TOKEN = sanitize_value(os.getenv("UPSTASH_VECTOR_REST_TOKEN"))
    
    # Semakan Kunci Wajib
    missing_keys = []
    if not LAZADA_APP_KEY: missing_keys.append("LAZADA_LiteApp_Key / LAZADA_APP_KEY")
    if not LAZADA_APP_SECRET: missing_keys.append("LAZADA_LiteApp_Secret / LAZADA_APP_SECRET")
    if not LAZADA_USER_TOKEN: missing_keys.append("LAZADA_USER_TOKEN")
    
    if missing_keys:
        print(f"🔴 [RALAT KRITIKAL]: Kunci persekitaran tidak lengkap: {missing_keys}")
        sys.exit(1)

    # 1. Menarik Calon Produk dari Lazada API (Smart Page Traversal)
    print("\n1️⃣ Mengambil calon produk dari Lazada Feed (Pages 1-10)...")
    ok, candidates = get_lazada_product_candidates(LAZADA_APP_KEY, LAZADA_APP_SECRET, LAZADA_USER_TOKEN, LAZADA_MEMBER_ID)
    
    if not ok:
        print("\n==================================================")
        print("🔴 [RALAT LAZADA API]: Gagal mendapatkan calon produk real!")
        print("==================================================")
        print(f"Laporan Ralat: {json.dumps(candidates, indent=2)}")
        sys.exit(1)

    # 2. In-Feed Filtering (Semakan Upstash Redis & Vector DB)
    selected_product = None
    print(f"🔍 Menapis {len(candidates)} calon produk menerusi Redis & Vector DB...")

    for prod in candidates:
        p_id = str(prod.get("productId") or prod.get("product_id") or prod.get("id"))
        p_name = prod.get("productName") or prod.get("title") or prod.get("name")
        pics = prod.get("pictures") or prod.get("image_url") or prod.get("image") or prod.get("picUrl")

        img_url = ""
        if isinstance(pics, list) and len(pics) > 0:
            img_url = pics[0]
        elif isinstance(pics, str):
            img_url = pics

        if not p_id or not img_url:
            continue

        # Semakan A: Upstash Redis (Tepat ID Produk dalam 7 Hari)
        if UPSTASH_REDIS_REST_URL and UPSTASH_REDIS_REST_TOKEN:
            if is_product_posted(UPSTASH_REDIS_REST_URL, UPSTASH_REDIS_REST_TOKEN, p_id):
                print(f"⏭️ [REDIS] ID {p_id} ('{p_name}') pernah dipos dalam 7 hari. Mencuba item seterusnya...")
                continue

        # Semakan B: Upstash Vector DB (Keserupaan Makna > 85% dalam 2 Hari)
        if UPSTASH_VECTOR_REST_URL and UPSTASH_VECTOR_REST_TOKEN:
            if is_similar_product_posted(UPSTASH_VECTOR_REST_URL, UPSTASH_VECTOR_REST_TOKEN, p_name):
                print(f"⏭️ [VECTOR DB] Tajuk '{p_name}' serupa dengan produk disiar < 48 jam lepas. Mencuba item seterusnya...")
                continue

        # Jana Pautan Affiliate
        tracking_link = generate_tracking_link(LAZADA_APP_KEY, LAZADA_APP_SECRET, LAZADA_USER_TOKEN, p_id)
        if not tracking_link:
            continue

        selected_product = {
            "id": p_id,
            "title": p_name,
            "desc": prod.get("description", f"Promosi khas {p_name} di Lazada."),
            "image": img_url,
            "link": tracking_link
        }
        print(f"🟢 [PRODUK LULUS TIGA LAPISAN]: '{p_name}' (ID: {p_id})")
        break

    if not selected_product:
        print("\n==================================================")
        print("🔴 [RALAT PIPELINE]: Tiada produk baharu yang lulus semakan Redis/Vector.")
        print("==================================================")
        print("❌ Versi dummy / fallback dilarang keras. Skrip dihentikan.")
        sys.exit(1)

    # 3. Jana AI Caption
    print("\n2️⃣ Menjana AI Caption Dinamik...")
    ai_ok, caption = generate_caption(OPENROUTER_BASE_URL, OPENROUTER_MODEL, OPENROUTER_API_KEY, selected_product["title"], selected_product["desc"])
    
    if not ai_ok:
        print(f"🔴 [AI ERROR]: Gagal menjana caption: {caption}")
        sys.exit(1)

    print(f"\n--- [CAPTION GENERATED] ---\n{caption}\n---------------------------\n")

    # 4. Hantar ke Telegram
    print("3️⃣ Menghantar ke Telegram...")
    tg_ok, tg_res = send_photo_to_telegram(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, caption, selected_product["image"], selected_product["link"])
    
    if tg_ok:
        print("🟢 [SUCCESS] Berjaya dipost ke Telegram!")
        
        # Merekod ke Upstash Redis (TTL 7 Hari)
        if UPSTASH_REDIS_REST_URL and UPSTASH_REDIS_REST_TOKEN:
            mark_product_posted(UPSTASH_REDIS_REST_URL, UPSTASH_REDIS_REST_TOKEN, selected_product["id"])
            print("💾 [REDIS] ID produk disimpan dengan TTL 7 Hari.")

        # Merekod ke Upstash Vector DB (Memory Embedding 2 Hari)
        if UPSTASH_VECTOR_REST_URL and UPSTASH_VECTOR_REST_TOKEN:
            mark_vector_posted(UPSTASH_VECTOR_REST_URL, UPSTASH_VECTOR_REST_TOKEN, selected_product["id"], selected_product["title"])
    else:
        print(f"🔴 [TELEGRAM FAIL]: {tg_res}")
        sys.exit(1)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("\n💥 [PIPELINE ERROR]: Ralat tidak dijangka berlaku.")
        traceback.print_exc()
        sys.exit(1)