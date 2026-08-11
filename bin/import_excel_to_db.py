import os
import sys
import glob
import pandas as pd
from dotenv import load_dotenv

load_dotenv(dotenv_path=".env.local")
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from playwright_engine.supabase_db import save_links_to_supabase
from playwright_engine.link_pool_manager import add_links_to_pool

def import_excel_file(file_path=None):
    print("\n" + "="*70)
    print("📊 [START] PENGIMPORT PAUTAN AFFILIATE DARI FAIL EXCEL LAZADA")
    print("="*70)

    if not file_path:
        search_paths = ["link_affiliate_xlsx/*.xlsx", "*.xlsx", "data/*.xlsx"]
        excel_files = []
        for path in search_paths:
            excel_files.extend(glob.glob(path))

        if not excel_files:
            print("❌ Tiada fail Excel (.xlsx) dijumpai di folder 'link_affiliate_xlsx/'.")
            return
        file_path = excel_files[0]

    if not os.path.exists(file_path):
        print(f"❌ Fail tidak wujud di laluan: {file_path}")
        return

    print(f"📁 Membaca fail Excel: {file_path}")

    try:
        df = pd.read_excel(file_path)
    except Exception as e:
        print(f"❌ Ralat membaca fail Excel: {str(e)}")
        return

    items_to_save = []
    seen_ids = set()

    for _, row in df.iterrows():
        p_id = str(row.get('item_id', '')).strip()
        title = str(row.get('product_name', '')).strip()
        aff_link = str(row.get('promo_short_link', '')).strip()
        img_url = str(row.get('picture_url', '')).strip() if pd.notnull(row.get('picture_url')) else ""
        
        try:
            price = float(row.get('discounted_price', 0.0))
        except (ValueError, TypeError):
            price = 0.0

        comm_rate = str(row.get('maximum commission_rate', '>=20%')).strip()
        if comm_rate == 'nan' or not comm_rate:
            comm_rate = ">=20%"

        if not p_id or p_id == 'nan' or not aff_link or aff_link == 'nan' or p_id in seen_ids:
            continue

        seen_ids.add(p_id)
        items_to_save.append({
            "product_id": p_id,
            "title": title,
            "price": price,
            "image_url": img_url,
            "affiliate_link": aff_link,
            "commission_rate": comm_rate,
            "keyword": "Manual Excel Export"
        })

    print(f"🎯 Berjaya mengekstrak {len(items_to_save)} pautan produk bersih dari fail Excel.\n")

    if not items_to_save:
        print("⚠️ Tiada pautan sah ditemui di dalam fail Excel.")
        return

    # 1. Simpan ke Supabase Cloud
    supa_ok, supa_count, supa_msg = save_links_to_supabase(items_to_save)
    if supa_ok:
        print(f"☁️ [SUPABASE SUCCESS] {supa_msg}")
    else:
        print(f"❌ [SUPABASE ERROR] {supa_msg}")

    # 2. Simpan ke Local JSON Pool (data/affiliate_link_pool.json)
    added_count, total_pool = add_links_to_pool(items_to_save)
    print(f"📦 [LOCAL POOL] +{added_count} pautan baharu ditambah. Jumlah keseluruhan dalam Pool: {total_pool}")

    print("\n🎉 SELESAI! Semua pautan dari fail Excel telah dimasukkan ke pangkalan data (Tanpa mengusik Redis).")

if __name__ == "__main__":
    target_file = sys.argv[1] if len(sys.argv) > 1 else None
    import_excel_file(target_file)