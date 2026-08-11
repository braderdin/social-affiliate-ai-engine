import os
import random
import requests

# Kategori kata kunci carian Unsplash untuk kepelbagaian mood harian
UNSPLASH_SEARCH_MOODS = [
    {"query": "cozy coffee tea mug table", "mood": "KOPI_TEH_PANAS"},
    {"query": "home garden green plants flowers", "mood": "POKOK_LAMAN"},
    {"query": "fresh baked bread pastry breakfast", "mood": "SARAPAN_ROTI"},
    {"query": "cozy home living room interior", "mood": "SUASANA_RUMAH"},
    {"query": "rainy window cozy indoor", "mood": "HUJAN_GERIMIS"},
    {"query": "home cooking baking flour table", "mood": "MASAKAN_RUMAH"},
    {"query": "peaceful beach sunset sea", "mood": "KAPANG_TENANG"}
]

def is_image_id_posted(redis_url, redis_token, photo_id):
    """Semak sama ada ID Gambar Unsplash ini pernah digunakan di Redis."""
    if not redis_url or not redis_token or not photo_id:
        return False
    clean_url = redis_url.rstrip('/')
    redis_key = f"posted:unsplash:{photo_id}"
    headers = {"Authorization": f"Bearer {redis_token}", "Content-Type": "application/json"}
    try:
        res = requests.post(f"{clean_url}/", json=["GET", redis_key], headers=headers, timeout=5)
        return res.status_code == 200 and res.json().get("result") is not None
    except Exception:
        return False

def mark_image_id_posted(redis_url, redis_token, photo_id, ttl=2592000):
    """Simpan ID Gambar Unsplash ke Redis dengan tempoh luput 30 Hari (2,592,000s)."""
    if not redis_url or not redis_token or not photo_id:
        return False
    clean_url = redis_url.rstrip('/')
    redis_key = f"posted:unsplash:{photo_id}"
    headers = {"Authorization": f"Bearer {redis_token}", "Content-Type": "application/json"}
    try:
        requests.post(f"{clean_url}/", json=["SET", redis_key, "1", "EX", str(ttl)], headers=headers, timeout=5)
        return True
    except Exception:
        return False

def fetch_unsplash_lifestyle_image(access_key, redis_url="", redis_token=""):
    """
    Menarik gambar fotografi realistik secara dinamik dari Unsplash Search REST API.
    Memulangkan: (success_bool, photo_id, image_url, description, mood_name)
    """
    if not access_key:
        return False, "", "", "Kunci UNSPLASH_ACCESS_KEY tidak ditemui di persekitaran.", ""

    # Pilih mood secara rawak
    category = random.choice(UNSPLASH_SEARCH_MOODS)
    query_term = category["query"]
    mood_name = category["mood"]

    url = "https://api.unsplash.com/search/photos"
    params = {
        "query": query_term,
        "per_page": 30,
        "orientation": "squarish",
        "client_id": access_key
    }

    try:
        res = requests.get(url, params=params, timeout=15)
        if res.status_code == 200:
            results = res.json().get("results", [])
            if not results:
                return False, "", "", f"Tiada gambar dijumpai di Unsplash untuk '{query_term}'", mood_name

            random.shuffle(results)
            for photo in results:
                photo_id = photo.get("id")
                img_url = photo.get("urls", {}).get("regular") or photo.get("urls", {}).get("full")
                
                # Ekstrak huraian visual gambar dari Unsplash
                raw_desc = photo.get("alt_description") or photo.get("description") or f"Pemandangan indah bertema {query_term}"

                if not img_url or not photo_id:
                    continue

                # Semak nyahduplikasi di Redis
                if is_image_id_posted(redis_url, redis_token, photo_id):
                    continue

                return True, photo_id, img_url, raw_desc, mood_name

            return False, "", "", "Semua gambar Unsplash dalam carian ini telah digunakan di Redis.", mood_name
        else:
            return False, "", "", f"Unsplash API Error (HTTP {res.status_code}): {res.text}", mood_name
    except Exception as e:
        return False, "", "", f"Ralat Rangkaian Unsplash API: {str(e)}", mood_name