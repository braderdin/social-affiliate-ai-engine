import os
import random
import requests


def is_image_id_posted(redis_url, redis_token, photo_id):
  """Semak sama ada ID Gambar Unsplash ini pernah digunakan di Redis."""
  if not redis_url or not redis_token or not photo_id:
    return False
  clean_url = redis_url.rstrip("/")
  redis_key = f"posted:unsplash:{photo_id}"
  headers = {
      "Authorization": f"Bearer {redis_token}",
      "Content-Type": "application/json",
  }
  try:
    res = requests.post(
        f"{clean_url}/", json=["GET", redis_key], headers=headers, timeout=5
    )
    return res.status_code == 200 and res.json().get("result") is not None
  except Exception:
    return False


def mark_image_id_posted(redis_url, redis_token, photo_id, ttl=2592000):
  """Simpan ID Gambar Unsplash ke Redis dengan tempoh luput 30 Hari (2,592,000s)."""
  if not redis_url or not redis_token or not photo_id:
    return False
  clean_url = redis_url.rstrip("/")
  redis_key = f"posted:unsplash:{photo_id}"
  headers = {
      "Authorization": f"Bearer {redis_token}",
      "Content-Type": "application/json",
  }
  try:
    requests.post(
        f"{clean_url}/",
        json=["SET", redis_key, "1", "EX", str(ttl)],
        headers=headers,
        timeout=5,
    )
    return True
  except Exception:
    return False


def fetch_candidate_images_from_queries(
    access_key,
    keywords_list,
    redis_url="",
    redis_token="",
    candidates_per_query=2,
):
  """Langkah 2: Mengambil calon-calon gambar real-time dari Unsplash REST API

  berdasarkan senarai kata kunci yang dijana oleh AI.

  Memulangkan: List of dicts [{"photo_id": ..., "image_url": ..., "description":
  ..., "keyword": ...}]
  """
  if not access_key:
    print(
        "❌ [UNSPLASH] Kunci UNSPLASH_ACCESS_KEY tidak ditemui di persekitaran."
    )
    return []

  candidates = []
  used_photo_ids = set()

  url = "https://api.unsplash.com/search/photos"

  for query in keywords_list:
    random_page = random.randint(1, 3)
    params = {
        "query": query,
        "per_page": 20,
        "page": random_page,
        "orientation": "squarish",
        "client_id": access_key,
    }

    try:
      res = requests.get(url, params=params, timeout=12)
      if res.status_code != 200:
        params["page"] = 1
        res = requests.get(url, params=params, timeout=12)

      if res.status_code == 200:
        results = res.json().get("results", [])
        if not results:
          continue

        random.shuffle(results)
        collected_for_this_query = 0

        for photo in results:
          photo_id = photo.get("id")
          img_url = photo.get("urls", {}).get("regular") or photo.get(
              "urls", {}
          ).get("full")
          raw_desc = (
              photo.get("alt_description")
              or photo.get("description")
              or f"Pemandangan bertema {query}"
          )

          if not img_url or not photo_id or photo_id in used_photo_ids:
            continue

          if is_image_id_posted(redis_url, redis_token, photo_id):
            continue

          used_photo_ids.add(photo_id)
          candidates.append({
              "photo_id": photo_id,
              "image_url": img_url,
              "description": raw_desc,
              "keyword": query,
          })

          collected_for_this_query += 1
          if collected_for_this_query >= candidates_per_query:
            break

    except Exception as e:
      print(f"⚠️ [UNSPLASH SEARCH ERROR] Carian '{query}': {e}")
      continue

  return candidates