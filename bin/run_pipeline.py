import os
import sys
import json
import traceback
from dotenv import load_dotenv

# Menambah direktori utama ke sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.lazada_api import get_lazada_product
from src.ai_persona import generate_caption
from src.telegram_bot import send_photo_to_telegram
from src.redis_db import is_product_posted, mark_product_posted

# Muat turun tetapan dari .env.local
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
    
    # 1. Pembacaan Pemboleh Ubah Persekitaran (.env.local)
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
    
    # Semakan Kunci Wajib Lazada
    missing_keys = []
    if not LAZADA_APP_KEY: missing_keys.append("LAZADA_LiteApp_Key / LAZADA_APP_KEY")
    if not LAZADA_APP_SECRET: missing_keys.append("LAZADA_LiteApp_Secret / LAZADA_APP_SECRET")
    if not LAZADA_USER_TOKEN: missing_keys.append("LAZADA_USER_TOKEN")
    
    if missing_keys:
        print(f"🔴 [RALAT KRITIKAL]: Kunci persekitaran tidak lengkap: {missing_keys}")
        sys.exit(1)

    # 2. Ambil Produk Real dari Lazada API (NO DUMMY ALLOWED)
    print("\n1️⃣ Mengambil produk real dari Lazada API...")
    lazada_ok, product = get_lazada_product(LAZADA_APP_KEY, LAZADA_APP_SECRET, LAZADA_USER_TOKEN, LAZADA_MEMBER_ID)
    
    if not lazada_ok:
        print("\n==================================================")
        print("🔴 [RALAT KRITIKAL LAZADA API]: Gagal mendapatkan produk real!")
        print("==================================================")
        print(f"Laporan Ralat: {json.dumps(product, indent=2)}")
        print("❌ Versi dummy / fallback dilarang keras. Skrip dihentikan.")
        sys.exit(1)

    print(f"🟢 [LAZADA OK]: Ditemui produk '{product['title']}' (ID: {product['id']})")

    # 3. Semak Duplikasi via Upstash Redis
    if UPSTASH_REDIS_REST_URL and UPSTASH_REDIS_REST_TOKEN:
        if is_product_posted(UPSTASH_REDIS_REST_URL, UPSTASH_REDIS_REST_TOKEN, product["id"]):
            print(f"⏭️ [REDIS] Produk ID {product['id']} sudah pernah dihantar sebelum ini. Melangkaui pipeline.")
            return
    else:
        print("⚠️ [REDIS NOTICE]: Tetapan Redis tiada, melangkau semakan duplikasi.")

    # 4. Jana AI Caption
    print("\n2️⃣ Menjana AI Caption...")
    ai_ok, caption = generate_caption(OPENROUTER_BASE_URL, OPENROUTER_MODEL, OPENROUTER_API_KEY, product["title"], product["desc"])
    
    if not ai_ok:
        print(f"🔴 [AI ERROR]: Gagal menjana caption: {caption}")
        sys.exit(1)

    print(f"\n--- [CAPTION GENERATED] ---\n{caption}\n---------------------------\n")

    # 5. Hantar ke Telegram
    print("3️⃣ Menghantar ke Telegram...")
    tg_ok, tg_res = send_photo_to_telegram(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, caption, product["image"], product["link"])
    
    if tg_ok:
        print("🟢 [SUCCESS] Berjaya dipost ke Telegram!")
        if UPSTASH_REDIS_REST_URL and UPSTASH_REDIS_REST_TOKEN:
            mark_product_posted(UPSTASH_REDIS_REST_URL, UPSTASH_REDIS_REST_TOKEN, product["id"])
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