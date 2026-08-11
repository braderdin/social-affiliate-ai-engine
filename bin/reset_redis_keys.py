import os
import requests
from dotenv import load_dotenv

load_dotenv(dotenv_path=".env.local")

redis_url = os.getenv("UPSTASH_REDIS_REST_URL", "").strip().rstrip('/')
redis_token = os.getenv("UPSTASH_REDIS_REST_TOKEN", "").strip()

if not redis_url or not redis_token:
    print("❌ Kunci Upstash Redis tidak wujud dalam .env.local")
    exit(1)

headers = {
    "Authorization": f"Bearer {redis_token}",
    "Content-Type": "application/json"
}

# 1. Cari kunci dengan awalan posted:sha256:*
res_keys = requests.post(f"{redis_url}/", json=["KEYS", "posted:sha256:*"], headers=headers)
if res_keys.status_code == 200:
    keys = res_keys.json().get("result", [])
    print(f"🔍 Ditemui {len(keys)} kunci penjarakan di Upstash Redis.")
    
    if keys:
        # 2. Padam kunci-kunci tersebut
        for k in keys:
            requests.post(f"{redis_url}/", json=["DEL", k], headers=headers)
        print("🧹 [REDIS RESET SUCCESS] Kesemua kunci ujian penjarakan Redis berjaya dipadam!")
    else:
        print("✨ Redis sudah bersih.")
else:
    print(f"❌ Ralat menghubungi Redis: {res_keys.text}")