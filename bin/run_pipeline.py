import os
import sys
from dotenv import load_dotenv

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.lazada_api import get_lazada_product
from src.ai_persona import generate_caption
from src.telegram_bot import send_photo_to_telegram
from src.redis_db import is_product_posted, mark_product_posted

load_dotenv('.env.local')

def main():
    print("\n==================================================")
    print("🚀 [FULL PIPELINE] Memulakan Automasi Modular")
    print("==================================================")
    
    # Environment Variables
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
    
    OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL")
    OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL")
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
    
    LAZADA_APP_KEY = os.getenv("LAZADA_APP_KEY")
    LAZADA_APP_SECRET = os.getenv("LAZADA_APP_SECRET")
    LAZADA_MEMBER_ID = os.getenv("LAZADA_MEMBER_ID")
    
    UPSTASH_REDIS_REST_URL = os.getenv("UPSTASH_REDIS_REST_URL")
    UPSTASH_REDIS_REST_TOKEN = os.getenv("UPSTASH_REDIS_REST_TOKEN")
    
    # 1. Ambil Produk Lazada
    print("\n1️⃣ Mengambil produk dari Lazada API...")
    lazada_ok, product = get_lazada_product(LAZADA_APP_KEY, LAZADA_APP_SECRET, LAZADA_MEMBER_ID, keyword="dapur")
    
    if not lazada_ok:
        print(f"⚠️ Lazada API tidak bersedia. Menggunakan fallback item.")
        product = {
            "id": "fallback_001",
            "title": "Periuk Cooking Pot Seramik Anti-Lekat Dapur Moden",
            "desc": "Bebas PTFE & PFOA, pemanasan sekata, pemegang kalis haba, mudah dicuci.",
            "image": "[https://images.unsplash.com/photo-1556911220-e15b29be8c8f?auto=format&fit=crop&w=800&q=80](https://images.unsplash.com/photo-1556911220-e15b29be8c8f?auto=format&fit=crop&w=800&q=80)",
            "link": f"[https://s.lazada.com.my/s.CikguAff?site=](https://s.lazada.com.my/s.CikguAff?site=){LAZADA_MEMBER_ID}"
        }

    # 2. Semak Duplikasi via Upstash Redis
    if is_product_posted(UPSTASH_REDIS_REST_URL, UPSTASH_REDIS_REST_TOKEN, product["id"]):
        print(f"⏭️ [REDIS] Produk ID {product['id']} sudah pernah dihantar sebelum ini. Melangkaui proses...")
        return

    # 3. Jana AI Caption
    print("2️⃣ Menjana AI Caption...")
    ai_ok, caption = generate_caption(OPENROUTER_BASE_URL, OPENROUTER_MODEL, OPENROUTER_API_KEY, product["title"], product["desc"])
    
    if not ai_ok:
        print(f"🔴 AI Error: {caption}")
        return

    print(f"\n--- [CAPTION GENERATED] ---\n{caption}\n---------------------------\n")

    # 4. Hantar ke Telegram
    print("3️⃣ Menghantar ke Telegram...")
    tg_ok, tg_res = send_photo_to_telegram(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, caption, product["image"], product["link"])
    
    if tg_ok:
        print("🟢 [SUCCESS] Berjaya dipost ke Telegram!")
        mark_product_posted(UPSTASH_REDIS_REST_URL, UPSTASH_REDIS_REST_TOKEN, product["id"])
    else:
        print(f"🔴 [TELEGRAM FAIL]: {tg_res}")

if __name__ == "__main__":
    main()