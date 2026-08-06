import os
import sys
import random
import traceback
from dotenv import load_dotenv

# Menambah direktori utama ke sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.guardrails import evaluate_product
from src.lazada_api import fetch_targeted_lazada_candidates, generate_tracking_link
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