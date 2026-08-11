import os
import random
import requests


def is_image_id_posted(redis_url, redis_token, photo_id):
  """Semak sama ada ID Gambar Unsplash ini pernah digunakan di Redis."""
  if not redis_url or not redis_token or not photo_id:
    return False
  clean_url = redis_url.rstrip('/')
  redis_key = f'posted:unsplash:{photo_id}'
  headers = {
      'Authorization': f'Bearer {redis_token}',
      'Content-Type': 'application/json',
  }
  try:
    res = requests.post(
        f'{clean_url}/', json=['GET', redis_key], headers=headers, timeout=5
    )
    return res.status_code == 200 and res.json().get('result') is not None
  except Exception:
    return False


def mark_image_id_posted(redis_url, redis_token, photo_id, ttl=2592000):
  """Simpan ID Gambar Unsplash ke Redis dengan tempoh luput 30 Hari (2,592,000s)."""
  if not redis_url or not redis_token or not photo_id:
    return False
  clean_url = redis_url.rstrip('/')
  redis_key = f'posted:unsplash:{photo_id}'
  headers = {
      'Authorization': f'Bearer {redis_token}',
      'Content-Type': 'application/json',
  }
  try:
    requests.post(
        f'{clean_url}/',
        json=['SET', redis_key, '1', 'EX', str(ttl)],
        headers=headers,
        timeout=5,
    )
    return True
  except Exception:
    return False


def fetch_candidate_images_from_queries(
    access_key,
    keywords_list,
    redis_url='',
    redis_token='',
    candidates_per_query=1,
):
  """Mengambil calon gambar dari Unsplash API dengan HAD KETAT MAXIMUM 5 REQUEST

  HTTP per larian skrip untuk menjaga quota Unsplash Demo Tier (50 req/hour).

  Memulangkan: List of dicts [{"photo_id": ..., "image_url": ..., "description":
  ..., "keyword": ...}]
  """
  if not access_key:
    print(
        '❌ [UNSPLASH] Kunci UNSPLASH_ACCESS_KEY tidak ditemui di persekitaran.'
    )
    return []

  candidates = []
  used_photo_ids = set()
  url = 'https://api.unsplash.com/search/photos'

  # HAD KETAT DEMO TIER: Maksimum 5 panggilan API sahaja
  MAX_API_CALLS = 5
  api_calls_count = 0

  # Pastikan hanya 5 kata kunci diproses
  target_keywords = keywords_list[:5]

  for query in target_keywords:
    if api_calls_count >= MAX_API_CALLS:
      print(f'🛑 [API LIMIT GUARD] Had {MAX_API_CALLS} request Unsplash dicapai.')
      break

    params = {
        'query': query,
        'per_page': 10,
        'page': 1,  # Sentiasa carian muka surat 1 untuk elak empty response
        'orientation': 'squarish',
        'client_id': access_key,
    }

    try:
      api_calls_count += 1
      print(
          f'📡 [UNSPLASH REQ {api_calls_count}/{MAX_API_CALLS}] Carian:'
          f' "{query}"'
      )

      res = requests.get(url, params=params, timeout=10)

      if res.status_code == 200:
        results = res.json().get('results', [])
        if not results:
          continue

        random.shuffle(results)
        collected_for_this_query = 0

        for photo in results:
          photo_id = photo.get('id')
          img_url = photo.get('urls', {}).get('regular') or photo.get(
              'urls', {}
          ).get('full')
          raw_desc = (
              photo.get('alt_description')
              or photo.get('description')
              or f'Pemandangan bertema {query}'
          )

          if not img_url or not photo_id or photo_id in used_photo_ids:
            continue

          if is_image_id_posted(redis_url, redis_token, photo_id):
            continue

          used_photo_ids.add(photo_id)
          candidates.append({
              'photo_id': photo_id,
              'image_url': img_url,
              'description': raw_desc,
              'keyword': query,
          })

          collected_for_this_query += 1
          if collected_for_this_query >= candidates_per_query:
            break
      else:
        print(
            f'⚠️ [UNSPLASH HTTP {res.status_code}] Gagal carian untuk "{query}"'
        )

    except Exception as e:
      print(f'⚠️ [UNSPLASH ERROR] Ralat carian "{query}": {e}')
      continue

  return candidates