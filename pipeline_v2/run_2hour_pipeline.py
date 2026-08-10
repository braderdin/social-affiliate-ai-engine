import os
import sys
import json
import traceback
from dotenv import load_dotenv

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.guardrails import evaluate_product, normalize_image_url
from src.redis_db import is_product_posted, mark_product_posted
from src.vector_db import is_similar_product_posted, mark_vector_posted
from src.lazada_api import generate_tracking_link
from src.facebook_ai_persona import generate_facebook_caption
from src.ai_persona import generate_caption as generate_telegram_caption
from src.facebook_bot import send_to_facebook_page
from src.telegram_bot import send_photo_to_telegram

from pipeline_v2.ai_cikgu_persona import generate_search_keywords
from pipeline_v2.lazada_keyword_search import search_lazada_candidates_by_keywords

load_dotenv('.env.local')

def sanitize(val):
    if not val:
        return ""
    val = str(val).strip()
    if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
        val = val[1:-1]
    return val.strip()

def run_pipeline():
    print("==================================================")
    print("🚀 [PIPELINE V2] Executing DuckDuckGo Keyword Search Pipeline")
    print("==================================================")

    # 1. Baca Kunci Persekitaran (Zero Hardcoding)
    openrouter_url = sanitize(os.getenv("OPENROUTER_BASE_URL"))
    openrouter_model = sanitize(os.getenv("OPENROUTER_MODEL"))
    openrouter_key = sanitize(os.getenv("OPENROUTER_API_KEY"))

    lazada_app_key = sanitize(os.getenv("LAZADA_LiteApp_Key") or os.getenv("LAZADA_APP_KEY"))
    lazada_app_secret = sanitize(os.getenv("LAZADA_LiteApp_Secret") or os.getenv("LAZADA_APP_SECRET"))
    lazada_token = sanitize(os.getenv("LAZADA_USER_TOKEN"))

    redis_url = sanitize(os.getenv("UPSTASH_REDIS_REST_URL"))
    redis_token = sanitize(os.getenv("UPSTASH_REDIS_REST_TOKEN"))

    vector_url = sanitize(os.getenv("UPSTASH_VECTOR_REST_URL") or os.getenv("UPSTASH_VECTOR_ENDPOINT_URL"))
    vector_token = sanitize(os.getenv("UPSTASH_VECTOR_REST_TOKEN"))

    fb_page_id = sanitize(os.getenv("FACEBOOK_PAGE_ID") or os.getenv("FB_PAGE_ID") or os.getenv("META_PAGE_ID"))
    fb_page_token = sanitize(os.getenv("FB_PAGE_ACCESS_TOKEN") or os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN") or os.getenv("META_PAGE_ACCESS_TOKEN"))

    tg_token = sanitize(os.getenv("TELEGRAM_BOT_TOKEN"))
    tg_chat_id = sanitize(os.getenv("TELEGRAM_CHAT_ID"))

    if not lazada_app_key or not lazada_app_secret or not lazada_token:
        raise ValueError("🔴 [KRITIKAL] Kunci API Lazada tidak ditemui di dalam Environment Secrets!")

    # 2. AI Persona Jana 5 Keyword Pendek
    cat_name, keywords = generate_search_keywords(openrouter_url, openrouter_model, openrouter_key)

    # 3. DuckDuckGo Search Keyword
    candidates = search_lazada_candidates_by_keywords(keywords)

    if not candidates:
        print("\n🔴 [PIPELINE STOPPED]: DuckDuckGo Search tidak memulangkan sebarang produk.")
        return

    selected_product = None
    selected_image = ""

    print("\n🛡️ [MEMULAKAN TAPISAN GUARDRAIL & DEDUP]...")
    for prod in candidates:
        p_id = prod["id"]
        p_title = prod["title"]
        matched_kw = prod.get("matched_keyword", "")

        # A. Guardrails (Harga RM10-RM500, Status Stok, Blacklist)
        is_ok, price, reason = evaluate_product(prod)
        if not is_ok:
            print(f"   ⏭️ [GUARDRAIL DITOLAK] ID {p_id} ('{matched_kw}'): {reason} (Harga: RM{price})")
            continue

        # B. Redis SHA-256 Deduplication (7 Hari)
        if is_product_posted(redis_url, redis_token, p_id, p_title):
            print(f"   ⏭️ [REDIS DUP] Produk ID {p_id} pernah dipos dalam 7 hari lepas. Langkau.")
            continue

        # C. Upstash Vector DB Semantic Duplication (48 Jam)
        if is_similar_product_posted(vector_url, vector_token, p_title):
            print(f"   ⏭️ [VECTOR DUP] Produk serupa dengan '{p_title}' pernah dipos dalam 48 jam lepas. Langkau.")
            continue

        selected_image = normalize_image_url(prod["image"])
        if not selected_image:
            continue

        selected_product = prod
        break

    if not selected_product:
        print("\n🔴 [PIPELINE WARN]: Semua calon produk ditolak oleh Guardrails/Redis/Vector DB.")
        return

    p_id = selected_product["id"]
    p_title = selected_product["title"]
    p_desc = selected_product["desc"]

    print(f"\n🟢 [PRODUK TERPILIH ID: {p_id}] {p_title}")

    # 4. Penjanaan Link Affiliate Rasmi Akaun Anda via Official Lazada API
    affiliate_link = generate_tracking_link(lazada_app_key, lazada_app_secret, lazada_token, p_id)
    if not affiliate_link:
        raise Exception(f"❌ Gagal menjana link affiliate rasmi untuk produk ID {p_id}")

    print(f"🔗 Link Affiliate Rasmi Anda: {affiliate_link}")

    # 5. Post ke Facebook Page (Gambar + Komen Link)
    if fb_page_id and fb_page_token:
        fb_ok, fb_caption, fb_comment_text = generate_facebook_caption(openrouter_url, openrouter_model, openrouter_key, p_title, p_desc)
        if fb_ok:
            print("📤 Menghantar hantaran ke Facebook Page...")
            fb_success, fb_res = send_to_facebook_page(fb_page_id, fb_page_token, fb_caption, selected_image, affiliate_link)
            if fb_success:
                print(f"🟢 [FACEBOOK BERJAYA] Post ID: {fb_res.get('post_id')}")
            else:
                print(f"⚠️ [FACEBOOK WARN] {fb_res}")

    # 6. Post ke Telegram Channel
    if tg_token and tg_chat_id:
        tg_ok, tg_caption = generate_telegram_caption(openrouter_url, openrouter_model, openrouter_key, p_title, p_desc)
        if tg_ok:
            print("📤 Menghantar hantaran ke Telegram Channel...")
            tg_success, tg_res = send_photo_to_telegram(tg_token, tg_chat_id, tg_caption, selected_image, affiliate_link)
            if tg_success:
                print("🟢 [TELEGRAM BERJAYA] Mesej & Gambar dihantar.")
            else:
                print(f"⚠️ [TELEGRAM WARN] {tg_res}")

    # 7. Rekodkan ke Redis & Vector DB
    mark_product_posted(redis_url, redis_token, p_id, p_title)
    mark_vector_posted(vector_url, vector_token, p_id, p_title)

    print("\n==================================================")
    print("🟢 [SUCCESS] PIPELINE DUCKDUCKGO SEARCH COMPLETED!")
    print("==================================================")

if __name__ == "__main__":
    try:
        run_pipeline()
    except Exception as e:
        print("\n💥 [PIPELINE GAGAL] Laporan Ralat Terperinci:")
        traceback.print_exc()
        sys.exit(1)