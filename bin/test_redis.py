import os
import sys
import json
import traceback
import requests
from dotenv import load_dotenv

# Menambah direktori utama ke sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Muat turun pemboleh ubah dari .env.local
load_dotenv('.env.local')

def sanitize_value(val):
    if not val:
        return ""
    val = str(val).strip()
    if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
        val = val[1:-1]
    return val.strip()

def mask_string(s):
    if not s or len(s) < 8:
        return "***"
    return s[:6] + "..." + s[-4:]

def test_upstash_redis():
    print("==================================================")
    print("🧪 [DIAGNOSTIC TEST] Upstash Redis REST API Connection")
    print("==================================================\n")

    # 1. Semakan Kunci Persekitaran (.env.local)
    redis_url = sanitize_value(os.getenv("UPSTASH_REDIS_REST_URL"))
    redis_token = sanitize_value(os.getenv("UPSTASH_REDIS_REST_TOKEN"))

    print(f"📌 UPSTASH_REDIS_REST_URL   : {redis_url or '❌ [KOSONG / MISSING]'}")
    print(f"📌 UPSTASH_REDIS_REST_TOKEN : {mask_string(redis_token)}")

    if not redis_url or not redis_token:
        print("\n🔴 [RALAT KRITIKAL]: Pemboleh ubah UPSTASH_REDIS_REST_URL atau UPSTASH_REDIS_REST_TOKEN tidak ditemui di dalam .env.local!")
        sys.exit(1)

    clean_url = redis_url.rstrip('/')
    headers = {"Authorization": f"Bearer {redis_token}"}
    test_key = "posted:product:diagnostic_test_99999"
    ttl_7_days = 604800  # 7 Hari dalam saat

    # ==================================================
    # UJIAN 1: Simpan Key dengan TTL (SETEX / SET ... EX)
    # ==================================================
    print(f"\n1️⃣ [STEP 1] Menguji Ujian SET Key '{test_key}' dengan TTL 7 Hari...")
    set_endpoint = f"{clean_url}/set/{test_key}/1/EX/{ttl_7_days}"
    print(f"   Target URL: {clean_url}/set/{test_key}/1/EX/{ttl_7_days}")

    try:
        res_set = requests.get(set_endpoint, headers=headers, timeout=15)
        print(f"📊 [HTTP STATUS CODE]: {res_set.status_code}")
        print(f"📜 [RAW RESPONSE BODY]: {res_set.text}")

        if res_set.status_code != 200:
            print(f"\n🔴 [REDIS SET FAIL]: Gagal membuat perintah SET ke Redis!")
            sys.exit(1)

        set_json = res_set.json()
        if set_json.get("result") == "OK":
            print("🟢 [REDIS SET SUCCESS]: Key ujian berjaya disimpan!")
        else:
            print(f"⚠️ [REDIS SET WARN]: Respons tidak mengembalikan 'OK': {set_json}")

    except Exception as e:
        print(f"\n💥 [EXCEPTION ERROR ON REDIS SET]: {e}")
        traceback.print_exc()
        sys.exit(1)

    # ==================================================
    # UJIAN 2: Semak Kewujudan Key (GET)
    # ==================================================
    print(f"\n2️⃣ [STEP 2] Menguji Ujian GET Key '{test_key}'...")
    get_endpoint = f"{clean_url}/get/{test_key}"

    try:
        res_get = requests.get(get_endpoint, headers=headers, timeout=15)
        print(f"📊 [HTTP STATUS CODE]: {res_get.status_code}")
        print(f"📜 [RAW RESPONSE BODY]: {res_get.text}")

        if res_get.status_code == 200:
            get_json = res_get.json()
            if get_json.get("result") is not None and str(get_json.get("result")) != "null":
                print("🟢 [REDIS GET SUCCESS]: Key ujian wujud dan dibaca dengan sempurna!")
            else:
                print("🔴 [REDIS GET FAIL]: Key tidak ditemui (Memulangkan NULL).")
        else:
            print(f"🔴 [REDIS GET FAIL]: Status HTTP {res_get.status_code}")

    except Exception as e:
        print(f"\n💥 [EXCEPTION ERROR ON REDIS GET]: {e}")
        traceback.print_exc()
        sys.exit(1)

    # ==================================================
    # UJIAN 3: Semak Masa Luput Key (TTL)
    # ==================================================
    print(f"\n3️⃣ [STEP 3] Menguji Ujian TTL (Masa Luput Saat) Key '{test_key}'...")
    ttl_endpoint = f"{clean_url}/ttl/{test_key}"

    try:
        res_ttl = requests.get(ttl_endpoint, headers=headers, timeout=15)
        print(f"📊 [HTTP STATUS CODE]: {res_ttl.status_code}")
        print(f"📜 [RAW RESPONSE BODY]: {res_ttl.text}")

        if res_ttl.status_code == 200:
            ttl_val = res_ttl.json().get("result")
            print(f"🟢 [REDIS TTL SUCCESS]: Baki TTL Key ialah {ttl_val} saat (~{round(ttl_val/86400, 2)} hari).")

    except Exception as e:
        print(f"\n💥 [EXCEPTION ERROR ON REDIS TTL]: {e}")
        traceback.print_exc()

    print("\n==================================================")
    print("🟢 [LULUS 100%] UJIAN UPSTASH REDIS BERJAYA SEPENUHNYA!")
    print("==================================================\n")

if __name__ == "__main__":
    test_upstash_redis()