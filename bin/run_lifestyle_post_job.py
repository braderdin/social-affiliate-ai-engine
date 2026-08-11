import os
import sys
import time
from dotenv import load_dotenv

load_dotenv(dotenv_path=".env.local")
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.lifestyle_ai_persona import generate_lifestyle_story
from src.lifestyle_image_fetcher import get_lifestyle_image_url
from src.facebook_bot import send_to_facebook_page
from src.telegram_bot import send_photo_to_telegram
from src.vector_db import is_similar_product_posted, mark_vector_posted
from src.redis_db import mark_product_posted

def run_lifestyle_posting_job():
    print("\n" + "="*70)
    print("📖 [START] ENJIN PEMPOSAN CERITA HARIAN (REAL HUMAN MODE + MEMORI VECTOR)")
    print("="*70)

    base_url = os.getenv("OPENROUTER_BASE_URL", "").strip()
    model = os.getenv("OPENROUTER_MODEL", "").strip()
    api_key = os.getenv("OPENROUTER_API_KEY", "").strip()

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

    selected_story = None
    selected_category = "LIVING_ROOM"

    # PERCUBAAN HINGGA 3 KALI UNTUK ELAK CERITA DUKLIKASI (SEMANTIK VECTOR DB)
    print("\n✍️ [STEP 1] Menjana & menyemak nyahduplikasi cerita di Upstash Vector DB...")
    for attempt in range(1, 4):
        ok_story, story_text, category_theme = generate_lifestyle_story(base_url, model, api_key)
        
        if not ok_story or not story_text:
            continue

        # Semak keserupaan makna cerita di Upstash Vector DB (>85% serupa = SKIP & RETRY)
        if vector_url and vector_token:
            if is_similar_product_posted(vector_url, vector_token, story_text):
                print(f"  ⏭️ [VECTOR SKIP - ATTEMPT {attempt}] Cerita serupa dikesan di Vector DB. Menjana tema baharu...")
                continue

        selected_story = story_text
        selected_category = category_theme
        break

    if not selected_story:
        selected_story = "Salam sejahtera kawan-kawan sekalian! Harini cuaca damai betul di luar. Cikgu doakan semoga hari ini membawa sejuta kebahagiaan buat kita semua. Salam mesra dari Cikgu!"

    print(f"\n✅ [STORY TERPILIH - BERSIH & SEGAR]:\n{selected_story}\n")

    # 2. DAPATKAN GAMBAR REALISTIK BERTEMA
    print(f"🖼️ [STEP 2] Memilih gambar bertema '{selected_category}'...")
    image_url = get_lifestyle_image_url(selected_category)
    print(f"✅ [IMAGE URL]: {image_url}")

    tg_success = False
    fb_success = False

    # 3. POS KE TELEGRAM (CERITA + GAMBAR CLEAN)
    if tg_token and tg_chat_id:
        print("\n✈️ [STEP 3] Menyiar cerita harian ke Telegram Channel...")
        sent_tg, res_tg = send_photo_to_telegram(
            token=tg_token,
            chat_id=tg_chat_id,
            caption=selected_story,
            image_url=image_url,
            affiliate_link=""  # Sifar teks Lazada
        )
        if sent_tg:
            print("  ✅ Berjaya dipos ke Telegram Channel!")
            tg_success = True
        else:
            print(f"  ❌ Gagal pos ke Telegram: {res_tg}")

    # 4. POS KE FACEBOOK PAGE (CERITA + GAMBAR CLEAN, SIFAR KOMEN)
    if fb_page_id and fb_page_token:
        print("\n📘 [STEP 4] Menyiar cerita harian ke Facebook Page...")
        sent_fb, res_fb = send_to_facebook_page(
            page_id=fb_page_id,
            page_token=fb_page_token,
            caption=selected_story,
            image_url=image_url,
            affiliate_link=""  # Sifar komen
        )
        if sent_fb:
            print(f"  ✅ Berjaya dipos ke Facebook Page! (Post ID: {res_fb.get('post_id')})")
            fb_success = True
        else:
            print(f"  ❌ Gagal pos ke Facebook Page: {res_fb}")

    # 5. SIMPAN REKOD CERITA KE VECTOR DB & REDIS
    if tg_success or fb_success:
        print("\n💾 [STEP 5] Merekodkan memori cerita ke Upstash Vector DB & Redis...")
        unique_id = f"lifestyle_{int(time.time())}"

        if vector_url and vector_token:
            mark_vector_posted(vector_url, vector_token, unique_id, selected_story)
            print("  ✅ Embedding cerita disimpan di Upstash Vector DB.")

        if redis_url and redis_token:
            mark_product_posted(redis_url, redis_token, unique_id, selected_story)
            print("  ✅ Rekod cerita disimpan di Upstash Redis.")

        print("\n🎉 [SUCCESS] Hantaran santai harian (Real Human + Memori Vector) berjaya disiarkan!\n")
    else:
        print("\n❌ Hantaran santai tidak berjaya disiarkan.")

if __name__ == "__main__":
    run_lifestyle_posting_job()