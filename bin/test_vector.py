import os
import sys
import json
import time
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

def test_upstash_vector():
    print("==================================================")
    print("🧪 [DIAGNOSTIC TEST] Upstash Vector REST API Connection")
    print("==================================================\n")

    # 1. Semakan Kunci Persekitaran (.env.local / .env.example)
    vector_url = sanitize_value(
        os.getenv("UPSTASH_VECTOR_REST_URL") or os.getenv("UPSTASH_VECTOR_ENDPOINT_URL")
    )
    vector_token = sanitize_value(os.getenv("UPSTASH_VECTOR_REST_TOKEN"))

    print(f"📌 UPSTASH_VECTOR_REST_URL   : {vector_url or '❌ [KOSONG / MISSING]'}")
    print(f"📌 UPSTASH_VECTOR_REST_TOKEN : {mask_string(vector_token)}")

    if not vector_url or not vector_token:
        print("\n🔴 [RALAT KRITIKAL]: Pemboleh ubah UPSTASH_VECTOR_REST_URL atau UPSTASH_VECTOR_REST_TOKEN tidak ditemui di dalam .env.local!")
        sys.exit(1)

    clean_url = vector_url.rstrip('/')
    headers = {
        "Authorization": f"Bearer {vector_token}",
        "Content-Type": "application/json"
    }

    test_id = "test_vector_diagnostic_99999"
    test_title = "Periuk Seramik Anti Lekat Dapur Moden Premium"
    current_time = int(time.time())

    # ==================================================
    # UJIAN 1: Memasukkan Embedding Teks ke Vector DB (/upsert-data)
    # ==================================================
    print(f"\n1️⃣ [STEP 1] Menguji Perintah /upsert-data Tajuk '{test_title}'...")
    upsert_endpoint = f"{clean_url}/upsert-data"

    upsert_payload = {
        "id": test_id,
        "data": test_title,
        "metadata": {
            "title": test_title,
            "posted_at": current_time,
            "test_flag": True
        }
    }

    print(f"   Target URL: {upsert_endpoint}")
    print(f"   Payload   : {json.dumps(upsert_payload, indent=2)}")

    try:
        res_upsert = requests.post(upsert_endpoint, json=upsert_payload, headers=headers, timeout=20)
        print(f"📊 [HTTP STATUS CODE]: {res_upsert.status_code}")
        print(f"📜 [RAW RESPONSE BODY]: {res_upsert.text}")

        if res_upsert.status_code != 200:
            print(f"\n🔴 [VECTOR UPSERT FAIL]: Gagal menyimpan data ke Vector DB!")
            print("📜 Laporan Ralat Penuh dari Upstash Vector:")
            try:
                print(json.dumps(res_upsert.json(), indent=2))
            except Exception:
                print(res_upsert.text)
            sys.exit(1)

        print("🟢 [VECTOR UPSERT SUCCESS]: Data vector embedding + metadata berjaya disimpan!")

    except Exception as e:
        print(f"\n💥 [EXCEPTION ERROR ON VECTOR UPSERT]: {e}")
        traceback.print_exc()
        sys.exit(1)

    # ==================================================
    # UJIAN 2: Membuat Carian Keserupaan Semantik (/query-data)
    # ==================================================
    print(f"\n2️⃣ [STEP 2] Menguji Perintah /query-data Carian Keserupaan Semantik...")
    query_endpoint = f"{clean_url}/query-data"

    query_payload = {
        "data": "Periuk Dapur Seramik",
        "topK": 3,
        "includeMetadata": True
    }

    print(f"   Target URL : {query_endpoint}")
    print(f"   Query Text : 'Periuk Dapur Seramik'")

    try:
        res_query = requests.post(query_endpoint, json=query_payload, headers=headers, timeout=20)
        print(f"📊 [HTTP STATUS CODE]: {res_query.status_code}")
        print(f"📜 [RAW RESPONSE BODY]: {res_query.text}")

        if res_query.status_code == 200:
            query_json = res_query.json()
            results = query_json.get("result", [])
            print(f"🟢 [VECTOR QUERY SUCCESS]: Ditemui {len(results)} padanan keserupaan!")

            for idx, item in enumerate(results, start=1):
                score = item.get("score", 0.0)
                meta = item.get("metadata", {})
                print(f"   📌 Padanan #{idx}: ID='{item.get('id')}' | Skor Cosine={score*100:.2f}% | Tajuk='{meta.get('title')}'")
        else:
            print(f"🔴 [VECTOR QUERY FAIL]: Status HTTP {res_query.status_code}")

    except Exception as e:
        print(f"\n💥 [EXCEPTION ERROR ON VECTOR QUERY]: {e}")
        traceback.print_exc()
        sys.exit(1)

    print("\n==================================================")
    print("🟢 [LULUS 100%] UJIAN UPSTASH VECTOR DB BERJAYA SEPENUHNYA!")
    print("==================================================\n")

if __name__ == "__main__":
    test_upstash_vector()