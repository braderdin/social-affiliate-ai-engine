import os
import sys
import json
import requests
from dotenv import load_dotenv

load_dotenv(dotenv_path=".env.local")
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from playwright_engine.link_pool_manager import load_link_pool

def verify_affiliate_redirects(sample_count=5):
    print("\n" + "="*70)
    print("🔍 [START] UJIAN PENGESAHAN LENCONGAN PAUTAN AFFILIATE LAZADA")
    print("="*70)

    pool = load_link_pool()
    if not pool:
        print("❌ [ERROR] Tiada pautan dijumpai di dalam 'data/affiliate_link_pool.json'.")
        return

    sample_items = pool[:sample_count]
    print(f" Menguji {len(sample_items)} pautan affiliate dari simpanan pool...\n")

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }

    for idx, item in enumerate(sample_items, 1):
        p_id = item.get("product_id")
        title = item.get("title")[:40]
        short_link = item.get("affiliate_link")

        print(f" [{idx:02d}] Product ID : {p_id}")
        print(f"      Tajuk      : {title}...")
        print(f"      Link Pendek: {short_link}")

        try:
            # Ikuti lencongan HTTP untuk dapatkan URL panjang penuh
            res = requests.get(short_link, headers=headers, allow_redirects=True, timeout=15)
            final_url = res.url
            
            print(f"      Link Panjang: {final_url[:90]}...")

            # Semak kewujudan parameter tracking
            has_tracking = False
            tracking_params = []
            
            for param in ["t=", "c=", "clk1", "subId1", "laz_token", "p="]:
                if param in final_url or param in short_link:
                    has_tracking = True
                    tracking_params.append(param)

            if has_tracking:
                print(f"      Status Tracking: ✅ Sah Affiliate Link (Parameter Dikesan: {', '.join(tracking_params)})")
            else:
                print(f"      Status Tracking: ⚠️ Tiada parameter tracking dikesan.")

        except Exception as e:
            print(f"      ❌ Ralat Lencongan: {str(e)}")
            
        print("-" * 70)

    print("\n🎉 Ujian pengesahan lencongan pautan selesai!\n")

if __name__ == "__main__":
    verify_affiliate_redirects(sample_count=5)