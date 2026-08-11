import os
import sys
import time
from dotenv import load_dotenv

load_dotenv(dotenv_path=".env.local")
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.lifestyle_image_fetcher import fetch_unsplash_lifestyle_image, mark_image_id_posted
from src.lifestyle_ai_persona import generate_story_from_image_description
from src.facebook_bot import send_to_facebook_page
from src.telegram_bot import send_photo_to_telegram
from src.vector_db import is_similar_product_posted, mark_vector_posted
from src.redis_db import mark_product_posted

def run_lifestyle_posting_job():
    print("\n" + "="*70)
    print("📖 [START] ENJIN PEMPOSAN CERITA HARIAN (UN SPLASH DYNAMIC VISION)")
    print("="*70)

    base_url = os.getenv("OPENROUTER_BASE_URL", "").strip()
    model = os.getenv("OPENROUTER_MODEL", "").strip()
    api_key = os.getenv("OPENROUTER_API_KEY", "").strip()

    unsplash_key = os.getenv("UNSPLASH_ACCESS_KEY", "").strip()

    redis_url = os.getenv("UPSTASH_REDIS_REST_URL", "").strip()
    redis_token = os.getenv("UPSTASH_REDIS_REST_TOKEN", "").strip()
    vector_url = os.getenv("UPSTASH_VECTOR_REST_URL", "").strip()
    vector_token = os.getenv("UPSTASH_VECTOR_REST_TOKEN", "").strip()

    tg_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    tg_chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()

    fb_page_id = os.getenv("FACEBOOK_PAGE_ID", "").strip() or os.getenv("META_PAGE_ID", "").strip()
    fb_page_token = (
        os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN", "").strip() or 
        os.getenv("FB_PAGE_ACCESS_TOKEN", "").strip() or 
        os.getenv("META_PAGE_ACCESS_TOKEN", "").strip()
    )

    # 1. TARIK GAMBAR REAL-TIME DARIPADA UN SPLASH REST API
    print("\n🌐 [STEP 1] Menarik gambar real-time dari Unsplash API...")
    ok_img, photo_id, image_url, image_desc, mood_category = fetch_unsplash_lifestyle_image(
        access_key=unsplash_key,
        redis_url=redis_url,
        redis_token=redis_token
    )

    if not ok_img or not image_url:
        print(f"❌ [ABORT] Gagal tarik gambar dari Unsplash API: {image_desc}")
        return

    print(f"✅ [UNSPLASH PHOTO ID] : {photo_id}")
    print(f"📸 [IMAGE URL]        : {image_url}")
    print(f"👁️ [HURAIAN VISUAL]   : {image_desc}")
    print(f"🎭 [MOOD TEMA]        : {mood_category}")

    # 2. JANA CERITA AI BERDASARKAN GAMBAR UN SPLASH
    print("\n✍️ [STEP 2] AI Persona meneliti gambar Unsplash & menjana cerita...")
    selected_story = None

    for attempt in range(1, 4):
        ok_story, story_text = generate_story_from_image_description(
            base_url, model, api_key, image_desc, mood_category
        )
        if not ok_story or not story_text:
            continue

        if vector_url and vector_token:
            if is_similar_product_posted(vector_url, vector_token, story_text):
                print(f"  ⏭️ [VECTOR SKIP] Cerita serupa dikesan di Vector DB. Mencuba semula...")
                continue

        selected_story = story_text
        break

    if not selected_story:
        selected_story = f"Salam sejahtera kawan-kawan sekalian! Cikgu kongsikan pemandangan indah harini. Cikgu doakan semoga hari ini membawa kebahagiaan buat kita semua. Salam mesra dari Cikgu!"

    print(f"\n✅ [CERITA AI SEPADAN GAMBAR UN SPLASH]:\n{selected_story}\n")

    tg_success = False
    fb_success = False

    # 3. POS KE TELEGRAM
    if tg_token and tg_chat_id:
        print("✈️ [STEP 3] Menyiar ke Telegram Channel...")
        sent_tg, res_tg = send_photo_to_telegram(
            token=tg_token,
            chat_id=tg_chat_id,
            caption=selected_story,
            image_url=image_url,
            affiliate_link=""
        )
        if sent_tg:
            print("  ✅ Berjaya dipos ke Telegram Channel!")
            tg_success = True
        else:
            print(f"  ❌ Gagal pos ke Telegram: {res_tg}")

    # 4. POS KE FACEBOOK PAGE
    if fb_page_id and fb_page_token:
        print("\n📘 [STEP 4] Menyiar ke Facebook Page...")
        sent_fb, res_fb = send_to_facebook_page(
            page_id=fb_page_id,
            page_token=fb_page_token,
            caption=selected_story,
            image_url=image_url,
            affiliate_link=""
        )
        if sent_fb:
            print(f"  ✅ Berjaya dipos ke Facebook Page! (Post ID: {res_fb.get('post_id')})")
            fb_success = True
        else:
            print(f"  ❌ Gagal pos ke Facebook Page: {res_fb}")

    # 5. REKOD STATUS KE REDIS & VECTOR DB
    if tg_success or fb_success:
        print("\n💾 [STEP 5] Merekodkan Unsplash Photo ID & cerita ke Redis & Vector DB...")
        unique_id = f"lifestyle_{photo_id}"

        # Tandakan Photo ID Unsplash ini supaya tidak dipos semula dalam tempoh 30 hari
        mark_image_id_posted(redis_url, redis_token, photo_id)
        print(f"  ✅ Unsplash Photo ID '{photo_id}' direkodkan di Upstash Redis (TTL 30 Hari).")

        if vector_url and vector_token:
            mark_vector_posted(vector_url, vector_token, unique_id, selected_story)
            print("  ✅ Embedding cerita disimpan di Upstash Vector DB.")

        if redis_url and redis_token:
            mark_product_posted(redis_url, redis_token, unique_id, selected_story)
            print("  ✅ Rekod cerita disimpan di Upstash Redis.")

        print("\n🎉 [SUCCESS] Hantaran santai Dynamic Unsplash Vision berjaya disiarkan!\n")

if __name__ == "__main__":
    run_lifestyle_posting_job()