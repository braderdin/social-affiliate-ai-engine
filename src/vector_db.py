import time
import requests

SIMILARITY_THRESHOLD = 0.85
TIME_WINDOW_2_DAYS = 172800  # 2 Hari dalam saat (2 * 24 * 3600)

def is_similar_product_posted(vector_url, vector_token, product_title):
    """
    Semak sama ada terdapat produk dengan makna/fungsi serupa (Cosine Similarity > 0.85)
    yang pernah dipos dalam tempoh 2 hari (172,800 saat) menggunakan Upstash Vector.
    """
    if not vector_url or not vector_token or not product_title:
        return False

    clean_url = vector_url.rstrip('/')
    query_url = f"{clean_url}/query"
    headers = {
        "Authorization": f"Bearer {vector_token}",
        "Content-Type": "application/json"
    }

    payload = {
        "data": str(product_title),
        "topK": 3,
        "includeMetadata": True
    }

    try:
        res = requests.post(query_url, json=payload, headers=headers, timeout=10)
        if res.status_code == 200:
            results = res.json().get("result", [])
            current_time = int(time.time())

            for match in results:
                score = match.get("score", 0.0)
                metadata = match.get("metadata", {}) or {}
                posted_at = metadata.get("posted_at", 0)

                # Jika skor keserupaan >= 0.85 dan perbezaan masa < 2 hari (172,800s)
                if score >= SIMILARITY_THRESHOLD and (current_time - posted_at) < TIME_WINDOW_2_DAYS:
                    matched_title = metadata.get('title', 'Produk Serupa')
                    print(f"⏭️ [VECTOR DB] Tajuk '{product_title}' serupa ({score*100:.1f}%) dengan '{matched_title}' (Disiar < 48 jam lepas). Langkau.")
                    return True
    except Exception as e:
        print(f"⚠️ [VECTOR WARN] Gagal semak Upstash Vector DB: {e}")

    return False

def mark_vector_posted(vector_url, vector_token, product_id, product_title):
    """
    Simpan embedding tajuk produk ke dalam Upstash Vector DB beserta metadata posted_at.
    """
    if not vector_url or not vector_token or not product_id or not product_title:
        return False

    clean_url = vector_url.rstrip('/')
    upsert_url = f"{clean_url}/upsert"
    headers = {
        "Authorization": f"Bearer {vector_token}",
        "Content-Type": "application/json"
    }

    current_time = int(time.time())
    payload = {
        "id": str(product_id),
        "data": str(product_title),
        "metadata": {
            "title": str(product_title),
            "posted_at": current_time
        }
    }

    try:
        res = requests.post(upsert_url, json=payload, headers=headers, timeout=10)
        if res.status_code == 200:
            return True
    except Exception as e:
        print(f"⚠️ [VECTOR WARN] Gagal simpan vector ke Upstash Vector DB: {e}")

    return False