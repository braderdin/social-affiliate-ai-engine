import os
import hashlib
import unicodedata
import requests

# Masa luput lalai 7 Hari dalam saat (7 * 24 * 60 * 60)
DEFAULT_TTL_SECONDS = int(os.getenv("REDIS_DEDUP_TTL_SECONDS", "604800"))

def generate_sha256_key(product_id, title=""):
    """
    Menjana Kunci Hash SHA-256 yang selamat, tersusun, dan bebas daripada ralat Unicode / Whitespace.
    """
    # 1. Normalisasikan teks Unicode (NFKD) & bersihkan aksara tersirat
    raw_id = str(product_id or "").strip()
    clean_title = unicodedata.normalize('NFKD', str(title or "")).strip().lower()
    
    # 2. Gabungkan ID dan Tajuk untuk menghasilkan input deterministik
    base_str = f"{raw_id}:{clean_title}" if clean_title else raw_id
    
    # 3. Jana Hash SHA-256 64-Hex
    sha256_hash = hashlib.sha256(base_str.encode('utf-8')).hexdigest()
    
    # 4. Tambahkan awalan namespace
    return f"posted:sha256:{sha256_hash}"

def is_product_posted(redis_url, redis_token, product_id, title=""):
    """
    Semak sama ada produk (via Hash SHA-256) pernah dihantar dalam tempoh 7 hari lepas.
    Format Kunci: posted:sha256:<sha256_hex>
    """
    if not redis_url or not redis_token or not product_id:
        return False
    
    clean_url = redis_url.rstrip('/')
    redis_key = generate_sha256_key(product_id, title)
    
    # Gunakan HTTP POST Payload Array ke Upstash REST API untuk keselamatan path URL
    endpoint = f"{clean_url}/"
    headers = {
        "Authorization": f"Bearer {redis_token}",
        "Content-Type": "application/json"
    }
    payload = ["GET", redis_key]
    
    try:
        res = requests.post(endpoint, json=payload, headers=headers, timeout=10)
        if res.status_code == 200:
            res_json = res.json()
            result = res_json.get("result")
            # Jika nilai wujud dan bukan null/None, produk pernah dipos
            if result is not None and str(result) != "null":
                return True
        else:
            print(f"⚠️ [REDIS WARN] HTTP {res.status_code} semasa menyemak kunci: {res.text}")
    except Exception as e:
        print(f"⚠️ [REDIS WARN] Gagal berhubung dengan Upstash Redis API: {e}")
        
    return False

def mark_product_posted(redis_url, redis_token, product_id, title=""):
    """
    Simpan Hash SHA-256 produk ke Redis dengan nilai '1' dan masa luput (TTL) 7 Hari secara atomik.
    Perintah Upstash REST via POST: ["SET", key, "1", "EX", 604800]
    """
    if not redis_url or not redis_token or not product_id:
        return False
    
    clean_url = redis_url.rstrip('/')
    redis_key = generate_sha256_key(product_id, title)
    
    endpoint = f"{clean_url}/"
    headers = {
        "Authorization": f"Bearer {redis_token}",
        "Content-Type": "application/json"
    }
    payload = ["SET", redis_key, "1", "EX", str(DEFAULT_TTL_SECONDS)]
    
    try:
        res = requests.post(endpoint, json=payload, headers=headers, timeout=10)
        if res.status_code == 200:
            res_json = res.json()
            if res_json.get("result") == "OK":
                print(f"💾 [REDIS SUCCESS] Kunci SHA-256 '{redis_key[:22]}...' direkodkan dengan TTL {DEFAULT_TTL_SECONDS}s.")
                return True
        else:
            print(f"⚠️ [REDIS ERROR] Gagal menyimpan kunci SHA-256. HTTP {res.status_code}: {res.text}")
    except Exception as e:
        print(f"⚠️ [REDIS WARN] Gagal menyimpan kunci ke Redis: {e}")
        
    return False

def delete_product_posted(redis_url, redis_token, product_id, title=""):
    """
    Memadam kunci Hash SHA-256 dari Redis sekiranya pemprosesan seterusnya (cth: Telegram) gagal.
    """
    if not redis_url or not redis_token or not product_id:
        return False
        
    clean_url = redis_url.rstrip('/')
    redis_key = generate_sha256_key(product_id, title)
    
    endpoint = f"{clean_url}/"
    headers = {
        "Authorization": f"Bearer {redis_token}",
        "Content-Type": "application/json"
    }
    payload = ["DEL", redis_key]
    
    try:
        res = requests.post(endpoint, json=payload, headers=headers, timeout=10)
        return res.status_code == 200 and res.json().get("result") == 1
    except Exception:
        return False