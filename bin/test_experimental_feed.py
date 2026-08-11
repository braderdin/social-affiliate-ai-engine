import os
import sys
import time
from dotenv import load_dotenv

load_dotenv(dotenv_path=".env.local")
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from playwright_engine.ai_keyword_generator import generate_5_keywords
from experimental_feed.lazada_feed_fetcher import (
    get_lazada_credentials,
    fetch_products_from_feed,
    filter_products_by_keywords_and_price,
    batch_convert_to_affiliate
)

def run_experimental_feed_test():
    print("\n" + "="*70)
    print("🧪 [START] UJIAN LAZADA OFFICIAL API FEED + PENAPIS HARGA & KEYWORD")
    print("="*70)

    error_aggregator = []

    # -----------------------------------------------------------------
    # SEMAKAN PEMBOLEHUBAH LAZADA DARI .env.local
    # -----------------------------------------------------------------
    _, _, _, env_status = get_lazada_credentials()
    print("\n📋 Semakan Pembolehubah Lazada (.env.local):")
    for k, v in env_status.items():
        print(f"  • {k:22s}: {'✅ Wujud' if v else '❌ TIADA'}")

    # -----------------------------------------------------------------
    # STEP 1: AI KEYWORD GENERATION
    # -----------------------------------------------------------------
    print("\n[STEP 1] Menjana 5 Kata Kunci via AI Persona Cikgu Suri Rumah...")
    kw_ok, keywords, category, kw_msg = generate_5_keywords()
    
    if not kw_ok or not keywords:
        err_str = f"❌ [STEP 1 FAIL] {kw_msg}"
        print(err_str)
        error_aggregator.append(err_str)
        print_error_summary(error_aggregator)
        return

    print(f"🎯 Kategori Terpilih : {category}")
    print(f"✅ [STEP 1 SUCCESS] Kata Kunci Dijana: {keywords}")

    # -----------------------------------------------------------------
    # STEP 2: FETCH 500 PRODUK DARI LAZADA OFFICIAL API FEED (PAGE 1-20)
    # -----------------------------------------------------------------
    print("\n[STEP 2] Mengambil Produk dari Lazada API Feed (Page 1 hingga 20)...")
    start_time = time.time()
    
    raw_products, fetch_errors, _ = fetch_products_from_feed(pages=20, limit_per_page=25)
    elapsed = round(time.time() - start_time, 2)

    print(f"📊 Jumlah produk mentah berjaya ditarik: {len(raw_products)} items ({elapsed}s)")
    if fetch_errors:
        for err in fetch_errors[:5]:
            error_aggregator.append(err)

    if not raw_products:
        error_aggregator.append("❌ [STEP 2 FAIL] Tiada produk diterima daripada Lazada API Feed.")
        print_error_summary(error_aggregator)
        return

    # -----------------------------------------------------------------
    # STEP 3: TAPIS PRODUK MENGGUNAKAN HARGA (RM10-RM500) & KEYWORD AI
    # -----------------------------------------------------------------
    print("\n[STEP 3] Menapis Produk Mentah (Harga: RM10 - RM500 + Kata Kunci AI)...")
    matched_items, price_rejected = filter_products_by_keywords_and_price(
        raw_products, keywords, min_price=10.0, max_price=500.0
    )

    print(f" 🚫 Produk Ditolak (Luar Julat Harga RM10-RM500) : {price_rejected} items")
    print(f" 🎯 Jumlah Produk Lulus Penapis Harga & Keyword AI: {len(matched_items)} items")

    if not matched_items:
        print("\n⚠️ Tiada produk dalam Feed yang sepadan dengan kata kunci AI dan harga RM10-RM500.")
        print(" Sampel 3 produk mentah dari Feed:")
        for sample in raw_products[:3]:
            p_name = sample.get('productName') or sample.get('title') or 'N/A'
            p_price = sample.get('discountPrice') or sample.get('price') or '0'
            print(f"  • ID: {sample.get('productId')} | Harga: RM{p_price} | Tajuk: {p_name[:50]}...")
        error_aggregator.append("⚠️ Tiada padanan produk untuk syarat harga & kata kunci AI.")
        print_error_summary(error_aggregator)
        return

    # -----------------------------------------------------------------
    # STEP 4: TUKAR KE LINK AFFILIATE RASMI VIA API
    # -----------------------------------------------------------------
    print("\n[STEP 4] Menukar Produk Padan ke Link Affiliate Rasmi...")
    converted_items, convert_errors = batch_convert_to_affiliate(matched_items)

    if convert_errors:
        for c_err in convert_errors:
            error_aggregator.append(c_err)

    print(f"\n✅ [STEP 4 SUCCESS] Berjaya menukar {len(converted_items)} pautan affiliate rasmi!\n")
    for idx, item in enumerate(converted_items, 1):
        print(f"  [{idx:02d}] ID: {item['product_id']} | Harga: RM{item['price']:.2f} | Keyword: '{item['keyword']}'")
        print(f"       Tajuk: {item['title'][:55]}...")
        print(f"       Link : {item.get('affiliate_link')}\n")

    print_error_summary(error_aggregator)

def print_error_summary(error_list):
    print("\n" + "="*70)
    print("📊 RINGKASAN LAPORAN UJIAN EXPERIMENTAL FEED (ERROR AGGREGATOR REPORT)")
    print("="*70)
    if not error_list:
        print("🎉 TIADA RALAT! Pendekatan API Feed + Local Filter lulus 100%!")
    else:
        print(f"⚠️ {len(error_list)} isu/ralat dikesan semasa ujian:")
        for idx, err in enumerate(error_list, 1):
            print(f"  {idx:02d}. {err}")
    print("="*70 + "\n")

if __name__ == "__main__":
    run_experimental_feed_test()