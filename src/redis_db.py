import requests

# Masa luput 7 Hari dalam saat (7 * 24 * 60 * 60)
TTL_7_DAYS = 604800

def is_product_posted(redis_url, redis_token, product_id):
    """
    Semak sama ada ID produk pernah dihantar dalam tempoh 7 hari lepas.
    Format Kunci Redis: posted:product:<product_id>
    """
    if not redis_url or not redis_token or not product_id:
        return False
    
    clean_url = redis_url.rstrip('/')
    key = f"posted:product:{product_id}"
    url = f"{clean_url}/get/{key}"
    headers = {"Authorization": f"Bearer {redis_token}"}
    
    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            result = res.json().get("result")
            # Jika kunci wujud dan tidak null, bermakna produk disiar dalam tempoh 7 hari
            return result is not None and str(result) != "null"
    except Exception as e:
        print(f"⚠️ [REDIS WARN] Gagal semak status kunci Redis: {e}")
    return False

def mark_product_posted(redis_url, redis_token, product_id):
    """
    Simpan ID produk ke dalam Redis dengan nilai '1' dan masa luput (TTL) 7 Hari.
    Perintah Upstash REST: SET posted:product:<product_id> 1 EX 604800
    """
    if not redis_url or not redis_token or not product_id:
        return False
    
    clean_url = redis_url.rstrip('/')
    key = f"posted:product:{product_id}"
    url = f"{clean_url}/set/{key}/1/EX/{TTL_7_DAYS}"
    headers = {"Authorization": f"Bearer {redis_token}"}
    
    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            return res.json().get("result") == "OK"
    except Exception as e:
        print(f"⚠️ [REDIS WARN] Gagal simpan kunci ke Redis dengan TTL: {e}")
    return False