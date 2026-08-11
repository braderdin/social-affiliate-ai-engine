import os
import requests
from datetime import datetime
from src.redis_db import mark_product_posted, is_product_posted
from src.vector_db import mark_vector_posted, is_similar_product_posted

def upload_image_to_b2(image_url, product_id):
    """
    Muat turun gambar produk dan simpan ke Backblaze B2 Storage.
    Menyediakan log ralat spesifik jika muat naik gagal.
    """
    bucket_name = os.getenv("B2_ACC1_BUCKET_NAME", "").strip()
    s3_endpoint = os.getenv("B2_ACC1_S3_API_ENDPOINT", "").strip()
    key_id = os.getenv("B2_ACC1_KEY_ID", "").strip() or os.getenv("B2_ACC1_ACCOUNT_KEY_ID", "").strip()
    app_key = os.getenv("B2_ACC1_APPLICATION_KEY", "").strip()

    if not bucket_name or not s3_endpoint or not key_id or not app_key:
        return False, "Pengesahan B2 Storage (.env.local) tidak lengkap. Semak B2_ACC1_BUCKET_NAME, S3_ENDPOINT, KEY_ID & APPLICATION_KEY."

    if not image_url:
        return False, "URL gambar asal tidak wujud."

    # 1. Muat turun gambar dari URL asal
    img_bytes = None
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        res = requests.get(image_url, headers=headers, timeout=15)
        if res.status_code == 200:
            img_bytes = res.content
        else:
            return False, f"Gagal muat turun gambar asal dari Lazada (HTTP {res.status_code})."
    except Exception as e:
        return False, f"Ralat rangkaian muat turun gambar: {str(e)}"

    # 2. Sediakan Path & Nama Fail B2
    today_str = datetime.now().strftime("%Y-%m-%d")
    object_key = f"lazada_products/{today_str}/{product_id}.jpg"

    # 3. Muat naik ke B2 Storage menggunakan boto3 S3 Client
    try:
        import boto3
        from botocore.client import Config

        # Bersihkan format endpoint
        clean_s3_endpoint = s3_endpoint.replace("https://", "").replace("http://", "").rstrip("/")
        endpoint_url = f"https://{clean_s3_endpoint}"
        
        s3_client = boto3.client(
            's3',
            endpoint_url=endpoint_url,
            aws_access_key_id=key_id,
            aws_secret_access_key=app_key,
            config=Config(signature_version='s3v4')
        )

        s3_client.put_object(
            Bucket=bucket_name,
            Key=object_key,
            Body=img_bytes,
            ContentType='image/jpeg'
        )

        b2_public_url = f"https://{bucket_name}.{clean_s3_endpoint}/{object_key}"
        return True, b2_public_url

    except ImportError:
        return False, "Pustaka 'boto3' belum dipasang dalam venv. Sila jalankan: pip install boto3 botocore"
    except Exception as e:
        return False, f"Ralat muat naik B2 API (S3): {str(e)}"

def process_and_index_product(product_item):
    """
    Memproses muat naik gambar ke B2 Storage dan merekodkan ke Upstash Redis & Vector DB.
    Memulangkan status B2 dan status Indeks yang jelas.
    """
    redis_url = os.getenv("UPSTASH_REDIS_REST_URL", "").strip()
    redis_token = os.getenv("UPSTASH_REDIS_REST_TOKEN", "").strip()
    vector_url = os.getenv("UPSTASH_VECTOR_REST_URL", "").strip()
    vector_token = os.getenv("UPSTASH_VECTOR_REST_TOKEN", "").strip()

    product_id = str(product_item.get("product_id") or "").strip()
    title = str(product_item.get("title") or "").strip()
    image_url = product_item.get("image_url", "")

    # 1. Semak Duplikasi Redis / Vector
    if is_product_posted(redis_url, redis_token, product_id, title):
        return False, "Produk pernah diproses dalam Upstash Redis (Duplicate).", product_item

    if is_similar_product_posted(vector_url, vector_token, title):
        return False, "Produk serupa pernah diproses dalam Upstash Vector DB.", product_item

    # 2. Muat naik gambar ke B2 Storage
    b2_success, b2_res = upload_image_to_b2(image_url, product_id)
    
    updated_item = dict(product_item)
    if b2_success:
        updated_item["b2_image_url"] = b2_res
        b2_msg = f"BERJAYA Simpan B2: {b2_res}"
    else:
        updated_item["b2_image_url"] = image_url  # Fallback ke Lazada URL
        b2_msg = f"GAGAL B2 ({b2_res}) -> Guna URL Asal Lazada"

    # 3. Merekodkan ke Upstash Redis & Vector DB
    mark_product_posted(redis_url, redis_token, product_id, title)
    mark_vector_posted(vector_url, vector_token, product_id, title)

    return b2_success, b2_msg, updated_item