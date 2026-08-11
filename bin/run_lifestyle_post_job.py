import os
import sys
from dotenv import load_dotenv

load_dotenv(dotenv_path=".env.local")
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.lifestyle_ai_persona import generate_lifestyle_story
from src.lifestyle_image_fetcher import get_lifestyle_image_url
from src.facebook_bot import send_to_facebook_page
from src.telegram_bot import send_photo_to_telegram

def run_lifestyle_posting_job():
    print("\n" + "="*70)
    print("📖 [START] ENJIN PEMPOSAN CERITA HARIAN (REAL HUMAN MODE)")
    print("="*70)

    base_url = os.getenv("OPENROUTER_BASE_URL", "").strip()
    model = os.getenv("OPENROUTER_MODEL", "").strip()
    api_key = os.getenv("OPENROUTER_API_KEY", "").strip()

    tg_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    tg_chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()

    fb_page_id = os.getenv("FACEBOOK_PAGE_ID", "").strip() or os.getenv("META_PAGE_ID", "").strip()
    fb_page_token = (
        os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN", "").strip() or 
        os.getenv("FB_PAGE_ACCESS_TOKEN", "").strip() or 
        os.getenv("META_PAGE_ACCESS_TOKEN", "").strip()
    )

    # 1. JANA CERITA HUMAN AI PERSONA
    print("\n✍️ [STEP 1] Menjana cerita harian gaya Cikgu Suri Rumah...")
    ok_story, story_text, category_theme = generate_lifestyle_story(base_url, model, api_key)

    if not ok_story or not story_text:
        story_text = "Salam sejahtera kawan-kawan sekalian! Harini cuaca damai betul di luar. Cikgu doakan semoga hari ini membawa sejuta kebahagiaan buat kita semua. Salam mesra dari Cikgu!"

    print(f"✅ [STORY GENERATED]:\n{story_text}\n")

    # 2. DAPATKAN GAMBAR REALISTIK BERTEMA
    print(f"🖼️ [STEP 2] Memilih gambar bertema '{category_theme}'...")
    image_url = get_lifestyle_image_url(category_theme)
    print(f"✅ [IMAGE URL]: {image_url}")

    tg_success = False
    fb_success = False

    # 3. POS KE TELEGRAM (PAUTAN AFFILIATE = KOSONG)
    if tg_token and tg_chat_id:
        print("\n✈️ [STEP 3] Menyiar cerita harian ke Telegram Channel...")
        sent_tg, res_tg = send_photo_to_telegram(
            token=tg_token,
            chat_id=tg_chat_id,
            caption=story_text,
            image_url=image_url,
            affiliate_link=""  # Kosongkan pautan supaya tiada teks Lazada
        )
        if sent_tg:
            print("  ✅ Berjaya dipos ke Telegram Channel!")
            tg_success = True
        else:
            print(f"  ❌ Gagal pos ke Telegram: {res_tg}")

    # 4. POS KE FACEBOOK PAGE (PAUTAN AFFILIATE = KOSONG, SIFAR KOMEN)
    if fb_page_id and fb_page_token:
        print("\n📘 [STEP 4] Menyiar cerita harian ke Facebook Page...")
        sent_fb, res_fb = send_to_facebook_page(
            page_id=fb_page_id,
            page_token=fb_page_token,
            caption=story_text,
            image_url=image_url,
            affiliate_link=""  # Kosongkan pautan supaya Facebook SIFAR KOMEN
        )
        if sent_fb:
            print(f"  ✅ Berjaya dipos ke Facebook Page! (Post ID: {res_fb.get('post_id')})")
            fb_success = True
        else:
            print(f"  ❌ Gagal pos ke Facebook Page: {res_fb}")

    if tg_success or fb_success:
        print("\n🎉 [SUCCESS] Hantaran santai harian (Real Human Mode) berjaya disiarkan!\n")
    else:
        print("\n❌ Hantaran santai tidak berjaya disiarkan.")

if __name__ == "__main__":
    run_lifestyle_posting_job()