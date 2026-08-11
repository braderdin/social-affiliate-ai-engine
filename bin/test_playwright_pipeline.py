import os
import sys
import time
from dotenv import load_dotenv

# Muat turun pembolehubah persekitaran dari .env.local
load_dotenv(dotenv_path=".env.local")

# Tambah laluan akar projek ke sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from playwright_engine.ai_keyword_generator import generate_5_keywords
from playwright_engine.lazada_scraper import scrape_lazada_products
from playwright_engine.lazada_affiliate import convert_batch_to_affiliate
from playwright_engine.supabase_db import save_links_to_supabase
from playwright_engine.link_pool_manager import add_links_to_pool
from src.redis_db import mark_product_posted, is_product_posted
from src.telegram_bot import send_photo_to_telegram

def run_test_pipeline(target_link_count=30):
    print("\n" + "="*70)
    print("🚀 [START] MEMULAKAN UJIAN PIPELINE PLAYWRIGHT + LAZADA AFFILIATE")
    print("="*70)
    
    error_aggregator = []
    processed_items = []

    tg_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    tg_chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    redis_url = os.getenv("UPSTASH_REDIS_REST_URL", "").strip()
    redis_token = os.getenv("UPSTASH_REDIS_REST_TOKEN", "").strip()

    # STEP 1: AI Keyword Generator (Pilih Kategori Dinamik)
    print("\n[STEP 1] Menjana 5 Kata Kunci via AI Persona Cikgu Suri Rumah...")
    kw_success, keywords, chosen_cat, kw_msg = generate_5_keywords()
    if not kw_success or not keywords:
        err_str = f"❌ [STEP 1 FAIL] {kw_msg}"
        print(err_str)
        error_aggregator.append(err_str)
        print_error_summary(error_aggregator)
        return

    print(f"🎯 Kategori Terpilih : {chosen_cat}")
    print(f"✅ [STEP 1 SUCCESS] Kata Kunci Dijana: {keywords}")

    # STEP 2: Scrape Produk Lazada via Playwright Local
    print("\n[STEP 2] Memulakan Scraper Playwright Local PC...")
    scraped_products = []
    try:
        scraped_products = scrape_lazada_products(keywords, max_per_keyword=15, headless=True)
        print(f"✅ [STEP 2 SUCCESS] Jumlah produk di-scrape: {len(scraped_products)}")
    except Exception as e:
        err_str = f"❌ [STEP 2 FAIL] Playwright Scraper Ralat: {str(e)}"
        print(err_str)
        error_aggregator.append(err_str)

    if not scraped_products:
        error_aggregator.append("⚠️ Tiada produk berjaya di-scrape dari Lazada.")
        print_error_summary(error_aggregator)
        return

    # STEP 3: Tukar Pautan Rasmi Affiliate API Lazada
    print("\n[STEP 3] Menukar Pautan Asal ke Link Affiliate Lazada API...")
    affiliate_items, conversion_errors = convert_batch_to_affiliate(scraped_products)
    
    print(f"\n--- LAPORAN DETIK PENUKARAN AFFILIATE ({len(affiliate_items)} BERJAYA / {len(conversion_errors)} GAGAL) ---")
    
    # Paparkan Produk Berjaya Ditukar
    for idx, item in enumerate(affiliate_items, 1):
        p_id = item.get("product_id")
        title = item.get("title")[:45]
        comm = item.get("commission_rate", ">=20%")
        link = item.get("affiliate_link")
        item["category"] = chosen_cat
        print(f"  ✅ [{idx:02d}] ID: {p_id} | Komisen: {comm} | Tajuk: {title}... | Link: {link}")

    # Paparkan Produk Gagal Ditukar
    if conversion_errors:
        print("\n--- SENARAI PRODUK GAGAL DITUKAR KE AFFILIATE ---")
        for err_item in conversion_errors:
            p_id = err_item.get("product_id")
            title = err_item.get("title")[:45]
            reason = err_item.get("reason")
            err_msg = f"Product ID {p_id} ('{title}...'): {reason}"
            print(f"  ❌ ID: {p_id} | Sebab: {reason}")
            error_aggregator.append(f"⚠️ [AFFILIATE FAIL] {err_msg}")

    if not affiliate_items:
        error_aggregator.append("❌ [STEP 3 FAIL] Tiada pautan berjaya ditukar ke affiliate.")
        print_error_summary(error_aggregator)
        return

    # STEP 4: Tapis Duplikasi & Rekodkan ke Upstash Redis + Supabase Cloud
    print(f"\n[STEP 4] Menyimpan ke Upstash Redis & Supabase Cloud (Sasaran: {target_link_count} item)...")
    valid_items_to_save = []

    for item in affiliate_items:
        if len(processed_items) >= target_link_count:
            break

        p_id = str(item.get("product_id", "")).strip()
        title = item.get("title", "")

        # Semak duplikasi di Redis
        if is_product_posted(redis_url, redis_token, p_id, title):
            print(f"  ⏭️ [REDIS DUP] ID {p_id} ('{title[:30]}...') pernah diproses. Langkau.")
            continue

        # Tandakan ke Upstash Redis
        mark_product_posted(redis_url, redis_token, p_id, title)
        valid_items_to_save.append(item)
        processed_items.append(item)

    # Simpan pukal ke Supabase Cloud
    if valid_items_to_save:
        supa_ok, supa_count, supa_msg = save_links_to_supabase(valid_items_to_save)
        if supa_ok:
            print(f"✅ [SUPABASE SUCCESS] {supa_msg}")
        else:
            err_str = f"❌ [SUPABASE ERROR] {supa_msg}"
            print(err_str)
            error_aggregator.append(err_str)

    # STEP 5: Simpan ke Local Link Pool JSON
    print("\n[STEP 5] Menyimpan Pautan ke Dalam Link Pool Local JSON...")
    added_count, total_pool = add_links_to_pool(processed_items)
    print(f"✅ [STEP 5 SUCCESS] +{added_count} pautan baharu ditambah. Jumlah dalam Pool: {total_pool}")

    # STEP 6: Hantar Backup Ke Telegram
    print("\n[STEP 6] Menghantar Backup Pautan Affiliate ke Telegram...")
    tg_sent_count = 0
    if tg_token and tg_chat_id:
        for p_item in processed_items[:5]:  # Hantar 5 sampel ujian ke Telegram
            title = p_item.get('title')
            comm = p_item.get('commission_rate', '>=20%')
            kw = p_item.get('keyword')
            caption = f"🛍️ *{title}*\n🏷️ Kategori: {kw}\n💰 Komisen Minima: {comm}"
            img_url = p_item.get("image_url")
            aff_link = p_item.get("affiliate_link")

            try:
                ok, res_tg = send_photo_to_telegram(tg_token, tg_chat_id, caption, img_url, aff_link)
                if ok:
                    tg_sent_count += 1
                else:
                    error_aggregator.append(f"⚠️ [TELEGRAM WARN] Gagal hantar ID {p_item.get('product_id')}: {res_tg}")
            except Exception as e:
                error_aggregator.append(f"❌ [TELEGRAM ERROR] ID {p_item.get('product_id')}: {str(e)}")
            time.sleep(1)
        print(f"✅ [STEP 6 SUCCESS] Berjaya hantar {tg_sent_count} sampel ke Telegram.")
    else:
        error_aggregator.append("⚠️ Kunci Telegram (.env.local) tidak ditetapkan.")

    print_error_summary(error_aggregator)

def print_error_summary(error_list):
    print("\n" + "="*70)
    print("📊 RINGKASAN LAPORAN UJIAN (ERROR AGGREGATOR REPORT)")
    print("="*70)
    if not error_list:
        print("🎉 TIADA RALAT! Keseluruhan pipeline berjalan lancar 100%.")
    else:
        print(f"⚠️ {len(error_list)} isu/ralat dikesan sepanjang larian:")
        for idx, err in enumerate(error_list, 1):
            print(f"  {idx:02d}. {err}")
    print("="*70 + "\n")

if __name__ == "__main__":
    run_test_pipeline(target_link_count=30)