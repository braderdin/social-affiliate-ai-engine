import requests

def is_product_posted(redis_url, redis_token, product_id):
    """Semak sama ada ID produk pernah dihantar"""
    if not redis_url or not redis_token:
        return False
    
    url = f"{redis_url.rstrip('/')}/sismember/posted_products/{product_id}"
    headers = {"Authorization": f"Bearer {redis_token}"}
    
    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            return res.json().get("result") == 1
    except Exception as e:
        print(f"⚠️ [REDIS WARN] Gagal semak Redis: {e}")
    return False

def mark_product_posted(redis_url, redis_token, product_id):
    """Simpan ID produk ke dalam senarai Redis"""
    if not redis_url or not redis_token:
        return False
    
    url = f"{redis_url.rstrip('/')}/sadd/posted_products/{product_id}"
    headers = {"Authorization": f"Bearer {redis_token}"}
    
    try:
        res = requests.get(url, headers=headers, timeout=10)
        return res.status_code == 200
    except Exception as e:
        print(f"⚠️ [REDIS WARN] Gagal simpan ke Redis: {e}")
    return False