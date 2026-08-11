import os
import re
import sys
import random
import requests
from dotenv import load_dotenv

# Muat turun persekitaran tempatan dari .env.local jika wujud
load_dotenv(dotenv_path=".env.local")

# Tambah laluan akar projek
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from playwright_engine.supabase_db import fetch_unused_links, mark_link_as_used, get_supabase_config
from src.redis_db import is_product_posted, mark_product_posted
from src.vector_db import is_similar_product_posted, mark_vector_posted
from src.ai_persona import generate_caption
from src.facebook_ai_persona import generate_facebook_caption
from src.telegram_bot import send_photo_to_telegram
from src.facebook_bot import send_to_facebook_page

def clean_image_url(url):
    """Memperbetulkan extension bertindih seperti .jpg.jpg atau .png.png."""
    if not url:
        return ""
    cleaned = re.sub(r'(\.(jpg|jpeg|png|webp))\.\2$', r'\1', url, flags=re.I)
    cleaned = re.sub(r'(\.(jpg|jpeg|png|webp))\1$', r'\1', cleaned, flags=re.I)
    return cleaned

def is_image_url_valid(url):
    """Memastikan URL gambar sah, wujud, dan boleh dimuat turun (Status HTTP 200)."""
    if not url:
        return False
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        res = requests.get(url, headers=headers, timeout=10)
        return res.status_code == 200 and len(res.content) > 500
    except Exception:
        return False

def fetch_all_links_fallback():
    """Cadangan kecemasan jika pautan unused kosong."""
    supabase_url, api_key, err = get_supabase_config()
    if err or not supabase_url:
        return []
    
    endpoint = f"{supabase_url}/rest/v1/affiliate_links?select=*&order=created_at.desc&limit=100"
    headers = {
        "apikey": api_key,
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    try:
        res = requests.get(endpoint, headers=headers, timeout=15)
        if res.status_code == 200:
            records = res.json()
            return records if isinstance(records, list) else []
    except Exception as e:
        print(f"⚠️ [SUPABASE FALLBACK WARN] {e}")
    return []

def run_auto_posting_job():
    print("\n" + "="*70)
    print("🤖 [START] ENJIN PEMPOSAN AUTOMATIK SOCIAL MEDIA (TG & FB)")
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

    print("\n📦 [STEP 1] Membaca pautan dari Supabase Cloud...")
    ok, candidate_list, err_msg = fetch_unused_links(limit=50)

    if not ok or not candidate_list:
        print("⚠️ Tiada pautan status_used=false. Membaca senarai pautan keseluruhan dari Supabase...")
        candidate_list = fetch_all_links_fallback()

    if not candidate_list:
        print("❌ [ABORT] Tiada produk dijumpai di dalam Supabase DB.")
        return

    print(f"✅ Berjaya menarik {len(candidate_list)} produk calon dari Supabase.")

    random.shuffle(candidate_list)
    selected_product = None

    print("\n🔍 [STEP 2] Menyemak syarat penjarakan & pra-sahkan gambar...")
    for item in candidate_list:
        p_id = str(item.get("product_id") or item.get("id") or "").strip()
        title = str(item.get("title") or item.get("product_name") or "").strip()
        aff_link = str(item.get("affiliate_link") or item.get("promo_short_link") or "").strip()
        raw_img_url = str(item.get("image_url") or item.get("picture_url") or "").strip()
        
        img_url = clean_image_url(raw_img_url)

        if not p_id or not title or not aff_link or not img_url:
            continue

        # A. Semak Upstash Redis (Exact Match)
        if is_product_posted(redis_url, redis_token, p_id, title):
            print(f"  ⏭️ [REDIS SKIP] ID {p_id} ('{title[:30]}...') pernah dipos dalam tempoh bertenang.")
            continue

        # B. Semak Upstash Vector DB (Semantic Similarity)
        if is_similar_product_posted(vector_url, vector_token, title):
            print(f"  ⏭️ [VECTOR SKIP] Tajuk '{title[:30]}...' serupa dengan produk dipos < 48 jam lepas.")
            continue

        # C. Semak Kesahan Gambar (Bypass Produk Gambar Rosak/404)
        if not is_image_url_valid(img_url):
            print(f"  ⏭️ [IMAGE BROKEN SKIP] ID {p_id} Gambar tidak dapat diakses (404/Rosak). Langkau.")
            continue

        selected_product = {
            "product_id": p_id,
            "title": title,
            "affiliate_link": aff_link,
            "image_url": img_url,
            "category": item.get("category", "")
        }
        break

    if not selected_product:
        print("⚠️ Semua calon produk masih dalam tempoh bertenang atau gambar tidak sah. Pemposan dibatalkan.")
        return

    p_id = selected_product["product_id"]
    title = selected_product["title"]
    aff_link = selected_product["affiliate_link"]
    img_url = selected_product["image_url"]

    print(f"\n🎯 [CALON TERPILIH] ID: {p_id}")
    print(f"   Tajuk : {title}")
    print(f"   Gambar: {img_url}")
    print(f"   Link  : {aff_link}")

    tg_success = False
    fb_success = False

    # PROSES TELEGRAM
    if tg_token and tg_chat_id:
        print("\n✈️ [STEP 3] Menjana kapsyen & pos ke Telegram Channel...")
        tg_ok, tg_caption = generate_caption(
            base_url=base_url,
            model=model,
            api_key=api_key,
            product_title=title,
            product_desc=title
        )
        if not tg_ok or not tg_caption:
            tg_caption = f"Haa harini Cikgu nak kongsi barang best: {title}! Memang berbaloi dan jimat sangat."

        sent_tg_ok, res_tg = send_photo_to_telegram(
            token=tg_token,
            chat_id=tg_chat_id,
            caption=tg_caption,
            image_url=img_url,
            affiliate_link=aff_link
        )
        if sent_tg_ok:
            print("  ✅ Berjaya dipos ke Telegram Channel!")
            tg_success = True
        else:
            print(f"  ❌ Gagal pos ke Telegram: {res_tg}")

    # PROSES FACEBOOK
    if fb_page_id and fb_page_token:
        print("\n📘 [STEP 4] Menjana kapsyen AI & pos ke Facebook Page...")
        fb_ai_ok, fb_caption, fb_comment = generate_facebook_caption(
            base_url=base_url,
            model=model,
            api_key=api_key,
            product_title=title,
            product_desc=title
        )
        if not fb_ai_ok or not fb_caption:
            fb_caption = f"Haa harini Cikgu nak bagi barang best untuk rumah: {title}! Geram betul Cikgu tengok benda ni."

        sent_fb_ok, res_fb = send_to_facebook_page(
            page_id=fb_page_id,
            page_token=fb_page_token,
            caption=fb_caption,
            image_url=img_url,
            affiliate_link=aff_link
        )
        if sent_fb_ok:
            print(f"  ✅ Berjaya dipos ke Facebook Page + Komen Link Affiliate! (Post ID: {res_fb.get('post_id')})")
            fb_success = True
        else:
            print(f"  ❌ Gagal pos ke Facebook Page: {res_fb}")

    # REKOD STATUS
    if tg_success or fb_success:
        print("\n💾 [STEP 5] Merekodkan status pemposan ke pangkalan data...")

        if mark_product_posted(redis_url, redis_token, p_id, title):
            print("  ✅ Rekod direkodkan di Upstash Redis.")

        if mark_vector_posted(vector_url, vector_token, p_id, title):
            print("  ✅ Rekod embedding disimpan di Upstash Vector DB.")

        sb_ok, sb_msg = mark_link_as_used(p_id)
        print(f"  ✅ Supabase: {sb_msg}")

        print("\n🎉 [SUCCESS] Seluruh aliran pemposan automatik selesai dengan jayanya!\n")
    else:
        print("\n❌ Pemposan tidak berjaya dilaksanakan di mana-mana platform.")

if __name__ == "__main__":
    run_auto_posting_job()