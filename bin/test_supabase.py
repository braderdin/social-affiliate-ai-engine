import os
import sys
import time
import requests
from dotenv import load_dotenv

# Muat turun pembolehubah persekitaran dari .env.local
load_dotenv(dotenv_path=".env.local")

# Tambah laluan akar projek ke sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def run_supabase_test():
    print("\n" + "="*70)
    print("⚡ [START] MEMULAKAN UJIAN KUNCI & SKEMA SUPABASE")
    print("="*70)

    error_aggregator = []

    # -----------------------------------------------------------------
    # STEP 1: SEMAKAN PEMBOLEHUBAH PERSEKITARAN (.env.local)
    # -----------------------------------------------------------------
    print("\n[STEP 1] Membaca & Menyemak Kunci Supabase dari .env.local...")

    supabase_url = os.getenv("SUPABASE_URL", "").strip() or os.getenv("NEXT_PUBLIC_SUPABASE_URL", "").strip()
    service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip() or os.getenv("SUPABASE_SECRET_KEY", "").strip()
    anon_key = os.getenv("SUPABASE_ANON_KEY", "").strip() or os.getenv("SUPABASE_PUBLISHABLE_KEY", "").strip()
    direct_url = os.getenv("DIRECT_URL", "").strip() or os.getenv("DATABASE_URL", "").strip()

    print(f"  • SUPABASE_URL     : {'✅ Wujud (' + supabase_url[:25] + '...)' if supabase_url else '❌ TIADA'}")
    print(f"  • SERVICE_ROLE_KEY : {'✅ Wujud (' + service_role_key[:15] + '...)' if service_role_key else '❌ TIADA'}")
    print(f"  • ANON_KEY         : {'✅ Wujud (' + anon_key[:15] + '...)' if anon_key else '❌ TIADA'}")
    print(f"  • DIRECT_URL (DB)  : {'✅ Wujud (' + direct_url[:25] + '...)' if direct_url else '❌ TIADA'}")

    if not supabase_url:
        error_aggregator.append("❌ SUPABASE_URL tidak ditemui di dalam .env.local")
    
    api_key_to_use = service_role_key or anon_key
    if not api_key_to_use:
        error_aggregator.append("❌ SUPABASE_SERVICE_ROLE_KEY atau SUPABASE_ANON_KEY tidak ditemui di dalam .env.local")

    if not supabase_url or not api_key_to_use:
        print_error_summary(error_aggregator)
        return

# -----------------------------------------------------------------
    # STEP 2: MENCIPTA SKEMA JADUAL VIA POSTGRES DIRECT URL (psycopg2)
    # -----------------------------------------------------------------
    print("\n[STEP 2] Memeriksa & Mencipta Skema Jadual 'affiliate_links' via Postgres Connection...")

    sql_create_table = """
    CREATE TABLE IF NOT EXISTS public.affiliate_links (
        id BIGSERIAL PRIMARY KEY,
        product_id VARCHAR(100) UNIQUE NOT NULL,
        title TEXT,
        category VARCHAR(200),
        keyword VARCHAR(200),
        original_url TEXT,
        affiliate_link TEXT NOT NULL,
        image_url TEXT,
        b2_image_url TEXT,
        commission_rate VARCHAR(50) DEFAULT '>=20%',
        status_used BOOLEAN DEFAULT FALSE,
        created_at TIMESTAMPTZ DEFAULT NOW(),
        updated_at TIMESTAMPTZ DEFAULT NOW()
    );
    """

    if direct_url:
        try:
            import psycopg2
            
            db_conn_str = direct_url
            if db_conn_str.startswith("postgres://"):
                db_conn_str = db_conn_str.replace("postgres://", "postgresql://", 1)

            conn = psycopg2.connect(db_conn_str, connect_timeout=15)
            conn.autocommit = True
            cursor = conn.cursor()
            
            # 1. Cipta Jadual
            cursor.execute(sql_create_table)
            
            # 2. Paksa PostgREST reload schema cache
            cursor.execute("NOTIFY pgrst, 'reload schema';")
            
            cursor.close()
            conn.close()
            print("✅ [SKEMA SUCCESS] Jadual 'affiliate_links' berjaya dicipta & cache PostgREST dikemas kini!")
            
            # Sela masa 2 saat untuk pangkalan data selesai reload cache
            time.sleep(2)

        except ImportError:
            err_msg = "Pustaka 'psycopg2' belum dipasang. Sila jalankan: pip install psycopg2-binary"
            print(f"⚠️  [SKEMA WARN] {err_msg}")
            error_aggregator.append(f"⚠️ [SCHEMA WARN] {err_msg}")
        except Exception as e:
            err_msg = f"Ralat sambungan Direct Postgres DB: {str(e)}"
            print(f"❌ [SKEMA ERROR] {err_msg}")
            error_aggregator.append(f"❌ [SCHEMA FAIL] {err_msg}")
    else:
        error_aggregator.append("❌ DIRECT_URL/DATABASE_URL tidak dijumpai di dalam .env.local")

    # -----------------------------------------------------------------
    # STEP 3: UJIAN SAMBUNGAN REST API SUPABASE (POSTGREST)
    # -----------------------------------------------------------------
    print("\n[STEP 3] Menguji Sambungan REST API ke Jadual 'affiliate_links'...")

    rest_endpoint = f"{supabase_url.rstrip('/')}/rest/v1/affiliate_links"
    headers = {
        "apikey": api_key_to_use,
        "Authorization": f"Bearer {api_key_to_use}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }

    try:
        res_get = requests.get(f"{rest_endpoint}?select=id&limit=1", headers=headers, timeout=15)
        if res_get.status_code == 200:
            print("✅ [REST CONNECTION OK] Berjaya berhubung dengan REST API Supabase!")
        else:
            err_msg = f"HTTP {res_get.status_code}: {res_get.text}"
            print(f"❌ [REST ERROR] {err_msg}")
            error_aggregator.append(f"❌ [REST FAIL] {err_msg}")
            print_error_summary(error_aggregator)
            return
    except Exception as e:
        err_msg = f"Ralat Rangkaian REST API: {str(e)}"
        print(f"❌ [REST ERROR] {err_msg}")
        error_aggregator.append(f"❌ [REST FAIL] {err_msg}")
        print_error_summary(error_aggregator)
        return

    # -----------------------------------------------------------------
    # STEP 4: UJIAN SIMPAN DATA (INSERT TEST RECORD)
    # -----------------------------------------------------------------
    print("\n[STEP 4] Memasukkan Data Ujian ke Supabase (INSERT)...")

    test_product_id = f"test_id_{int(time.time())}"
    sample_payload = {
        "product_id": test_product_id,
        "title": "Produk Ujian Supabase Terminal",
        "category": "Barangan Dapur",
        "keyword": "periuk seramik",
        "original_url": f"https://www.lazada.com.my/products/pdp-i{test_product_id}.html",
        "affiliate_link": f"https://s.lazada.com.my/s.test_{test_product_id}",
        "image_url": "https://img.lazcdn.com/g/p/test_image.jpg",
        "b2_image_url": "https://f000.backblazeb2.com/file/test_image.jpg",
        "commission_rate": ">=20%",
        "status_used": False
    }

    try:
        res_insert = requests.post(rest_endpoint, json=sample_payload, headers=headers, timeout=15)
        if res_insert.status_code in [200, 201]:
            print(f"✅ [INSERT SUCCESS] Data berjaya disimpan di Supabase Cloud!")
            print(f"   • Product ID    : {sample_payload['product_id']}")
            print(f"   • Affiliate Link: {sample_payload['affiliate_link']}")
        else:
            err_msg = f"HTTP {res_insert.status_code}: {res_insert.text}"
            print(f"❌ [INSERT ERROR] {err_msg}")
            error_aggregator.append(f"❌ [INSERT FAIL] {err_msg}")
    except Exception as e:
        err_msg = f"Ralat Rangkaian INSERT: {str(e)}"
        print(f"❌ [INSERT ERROR] {err_msg}")
        error_aggregator.append(f"❌ [INSERT FAIL] {err_msg}")

    # -----------------------------------------------------------------
    # STEP 5: UJIAN MEMBACA DATA (READ RECORD)
    # -----------------------------------------------------------------
    print("\n[STEP 5] Membaca Data Ujian dari Supabase (SELECT)...")

    try:
        res_read = requests.get(f"{rest_endpoint}?product_id=eq.{test_product_id}", headers=headers, timeout=15)
        if res_read.status_code == 200:
            records = res_read.json()
            if records and len(records) > 0:
                print(f"✅ [READ SUCCESS] Rekod ditemui di DB cloud: '{records[0].get('title')}' (ID: {records[0].get('product_id')})")
            else:
                error_aggregator.append("⚠️ [READ WARN] Rekod ujian tidak ditemui selepas dimasukkan.")
        else:
            error_aggregator.append(f"❌ [READ FAIL] HTTP {res_read.status_code}: {res_read.text}")
    except Exception as e:
        error_aggregator.append(f"❌ [READ FAIL] Ralat: {str(e)}")

    # -----------------------------------------------------------------
    # STEP 6: CLEANUP (MEMADAM DATA UJIAN)
    # -----------------------------------------------------------------
    print("\n[STEP 6] Memadam Data Ujian (DELETE CLEANUP)...")

    try:
        res_del = requests.delete(f"{rest_endpoint}?product_id=eq.{test_product_id}", headers=headers, timeout=15)
        if res_del.status_code in [200, 204]:
            print("✅ [CLEANUP SUCCESS] Data sampel ujian berjaya dipadam dari cloud.")
        else:
            error_aggregator.append(f"⚠️ [CLEANUP WARN] HTTP {res_del.status_code}: {res_del.text}")
    except Exception as e:
        error_aggregator.append(f"⚠️ [CLEANUP WARN] {str(e)}")

    print_error_summary(error_aggregator)

def print_error_summary(error_list):
    print("\n" + "="*70)
    print("📊 RINGKASAN LAPORAN UJIAN SUPABASE (ERROR AGGREGATOR REPORT)")
    print("="*70)
    if not error_list:
        print("🎉 TIADA RALAT! Kunci Supabase sah 100% dan skema DB dicipta dengan sempurna!")
    else:
        print(f"⚠️ {len(error_list)} isu/ralat dikesan semasa ujian:")
        for idx, err in enumerate(error_list, 1):
            print(f"  {idx:02d}. {err}")
    print("="*70 + "\n")

if __name__ == "__main__":
    run_supabase_test()