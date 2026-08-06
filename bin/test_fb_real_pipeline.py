import os
import sys
import random
from dotenv import load_dotenv

# Menambah direktori utama ke sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Muat turun pemboleh ubah persekitaran (.env.local)
load_dotenv('.env.local')

from src.guardrails import evaluate_product
from src.lazada_api import fetch_targeted_lazada_candidates, generate_tracking_link
from src.redis_db import is_product_posted, mark_product_posted
from src.vector_db import is_similar_product_posted, mark_vector_posted
from src.facebook_ai_persona import generate_facebook_caption
from src.facebook_bot import send_to_facebook_page

def sanitize_value(val):
    if not val:
        return ""
    val = str(val).strip()
    if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
        val = val[1:-1]
    return val.strip()

def main():
    print("==================================================")
    print("🚀 [TEST REAL PIPELINE] Lazada -> Guardrails -> Redis -> Vector DB -> FB AI Persona -> FB Page")
    print("==================================================\n")

    # 1. Pembacaan Kunci Asas dari .env.local
    openrouter_url = sanitize_value(os.getenv("OPENROUTER_BASE_URL"))
    openrouter_model = sanitize_value(os.getenv("OPENROUTER_MODEL"))
    openrouter_key = sanitize_value(os.getenv("OPENROUTER_API_KEY"))

    fb_page_id = sanitize_value(
        os.getenv("FACEBOOK_PAGE_ID") or 
        os.getenv("FB_PAGE_ID") or 
        os.getenv("META_PAGE_ID")
    )
    fb_token = sanitize_value(
        os.getenv("FB_PAGE_ACCESS_TOKEN") or 
        os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN") or 
        os.getenv("META_PAGE_ACCESS_TOKEN")
    )

    lazada_app_key = sanitize_value(os.getenv("LAZADA_LiteApp_Key") or os.getenv("LAZADA_APP_KEY"))
    lazada_app_secret = sanitize_value(os.getenv("LAZADA_LiteApp_Secret") or os.getenv("LAZADA_APP_SECRET"))
    lazada_user_token = sanitize_value(os.getenv("LAZADA_USER_TOKEN"))

    redis_url = sanitize_value(os.getenv("UPSTASH_REDIS_REST_URL"))
    redis_token = sanitize_value(os.getenv("UPSTASH_REDIS_REST_TOKEN"))

    vector_url = sanitize_value(os.getenv("UPSTASH_VECTOR_REST_URL") or os.getenv("UPSTASH_VECTOR_ENDPOINT_URL"))
    vector_token = sanitize_value(os.getenv("UPSTASH_VECTOR_REST_TOKEN"))

    # Validasi Kehadiran Kunci
    if not all([lazada_app_key, lazada_app_secret, lazada_user_token, fb_page_id, fb_token, openrouter_key]):
        print("🔴 [RALAT KRITIKAL]: Kunci persekitaran .env.local tidak lengkap!")
        sys.exit(1)

    # 2. Tarik Produk Live Daripada Lazada API
    print("1️⃣ Menarik calon produk LIVE dari Lazada Feed API...")
    candidates = fetch_targeted_lazada_candidates(lazada_app_key, lazada_app_secret, lazada_user_token, max_items=100)

    if not candidates:
        print("🔴 [RALAT]: Lazada Feed API memulangkan 0 produk.")
        sys.exit(1)

    print(f"🟢 Berjaya menarik {len(candidates)} produk live dari Lazada.\n")
    random.shuffle(candidates)

    selected_product = None
    affiliate_link = ""
    ai_caption = ""
    ai_comment_text = ""

    # 3. Penapisan Strict 3 Lapisan (Guardrails -> Upstash Redis -> Vector DB)
    print("2️⃣ Mula menyemak calon produk merentasi Guardrails, Redis & Vector DB...")
    evaluated_count = 0

    for prod in candidates:
        evaluated_count += 1
        p_id = prod["id"]
        p_title = prod["title"]

        # LAPISAN 1: Guardrails (Harga & Non-Halal/GWP)
        is_valid, active_price, reason = evaluate_product(prod)
        if not is_valid:
            print(f"  ⏩ #{evaluated_count} ID {p_id}: Gagal Guardrail ({reason}). Langkau.")
            continue

        # LAPISAN 2: Upstash Redis Check (Duplikasi Tepat 7 Hari)
        if redis_url and redis_token:
            if is_product_posted(redis_url, redis_token, p_id, p_title):
                print(f"  ⏩ #{evaluated_count} ID {p_id}: Pernah dipos dalam 7 hari (Redis). Langkau.")
                continue

        # LAPISAN 3: Upstash Vector DB Check (Semantik Similar < 48 Jam)
        if vector_url and vector_token:
            if is_similar_product_posted(vector_url, vector_token, p_title):
                print(f"  ⏩ #{evaluated_count} ID {p_id}: Produk serupa pernah dipos < 48 jam (Vector). Langkau.")
                continue

        # Lulus Semua Tapisan -> Jana Link Affiliate Sebenar
        print(f"\n🎯 [PRODUK PILIHAN LULUS TAPISAN] ID: {p_id}")
        print(f"   Tajuk: {p_title}")
        print(f"   Harga: RM {active_price:.2f}")

        print("\n🔗 Menjana Lazada Affiliate Tracking Link Sebenar...")
        aff_link = generate_tracking_link(lazada_app_key, lazada_app_secret, lazada_user_token, p_id)
        if not aff_link:
            print("  ⚠️ Gagal menjana tracking link. Mencuba produk berikutnya...")
            continue

        # Penjanaan AI Caption Facebook & Ayat Komen (Cikgu Suri Rumah Persona)
        print("\n📝 Menjana AI Persona Caption Facebook & Komen (Watak Cikgu Suri Rumah)...")
        ai_ok, caption, comment_text = generate_facebook_caption(
            openrouter_url,
            openrouter_model,
            openrouter_key,
            p_title,
            prod.get("desc", "")
        )

        if not ai_ok or not caption:
            print(f"  ⚠️ Gagal menjana AI Caption: {caption}. Mencuba produk berikutnya...")
            continue

        selected_product = prod
        affiliate_link = aff_link
        ai_caption = caption
        ai_comment_text = comment_text
        break

    if not selected_product:
        print("\n🔴 [RALAT]: Tiada produk yang lulus dari senarai calon Lazada!")
        sys.exit(1)

    print(f"\n📏 Panjang Caption Facebook Dijana: {len(ai_caption)} Aksara/Abjad")
    print("---------------- TEKS CAPTION AI ----------------")
    print(ai_caption)
    print("-------------------------------------------------")
    print("---------------- TEKS KOMEN AI ------------------")
    print(f"{ai_comment_text}\n👉 {affiliate_link}")
    print("-------------------------------------------------\n")

    # 4. Hantar Ke Facebook Page + Komen Pertama (Gabungan Ayat Komen AI + Link Affiliate)
    print("3️⃣ Menghantar Gambar, Caption AI & Komen Affiliate ke Facebook Page...")
    full_comment = f"{ai_comment_text}\n👉 {affiliate_link}"
    
    fb_ok, fb_res = send_to_facebook_page(
        fb_page_id,
        fb_token,
        ai_caption,
        selected_product["image"],
        full_comment
    )

    if not fb_ok:
        print(f"🔴 [FACEBOOK FAIL]: {fb_res}")
        sys.exit(1)

    print("🟢 [FACEBOOK SUCCESS] Berjaya Dipos ke Facebook Page!")
    print(f"   📌 Post ID    : {fb_res.get('post_id')}")
    print(f"   📌 Comment ID : {fb_res.get('comment_id')}\n")

    # 5. Merekodkan Rekod Baharu ke Upstash Redis & Vector DB
    print("4️⃣ Merekodkan ID Produk ke Upstash Redis & Vector DB...")
    if redis_url and redis_token:
        mark_product_posted(redis_url, redis_token, selected_product["id"], selected_product["title"])

    if vector_url and vector_token:
        mark_vector_posted(vector_url, vector_token, selected_product["id"], selected_product["title"])

    print("\n==================================================")
    print("🟢 [TEST REAL PIPELINE 100% LULUS] Facebook Page Berjaya Dipos!")
    print("==================================================")

if __name__ == "__main__":
    main()