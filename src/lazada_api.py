import time
import hmac
import hashlib
import random
import requests
from src.guardrails import normalize_image_url, TARGET_CATEGORIES

def sign_lazada(api_path, params, app_secret):
    """Menjana HMAC-SHA256 Signature mengikut piawaian Lazada Open Platform"""
    sorted_params = sorted(params.items())
    sign_str = api_path
    for k, v in sorted_params:
        sign_str += f"{k}{v}"
    
    return hmac.new(
        app_secret.encode('utf-8'),
        sign_str.encode('utf-8'),
        hashlib.sha256
    ).hexdigest().upper()

def fetch_targeted_lazada_candidates(app_key, app_secret, user_token, max_items=100):
    """
    Menarik calon produk secara khusus daripada Kategori Kekeluargaan / Dapur / Bayi / Wanita
    menggunakan parameter categoryL1 rasmi Lazada API Feed.
    """
    domain = "api.lazada.com.my"
    feed_path = "/marketing/product/feed"
    feed_url = f"https://{domain}/rest{feed_path}"
    
    candidates = []
    seen_ids = set()
    
    # Rawakkan kategori dan halaman untuk kepelbagaian produk
    categories = list(TARGET_CATEGORIES)
    random.shuffle(categories)
    pages = [1, 2, 3]
    random.shuffle(pages)

    for cat_id in categories:
        for page in pages:
            if len(candidates) >= max_items:
                break
                
            timestamp = str(int(time.time() * 1000))
            feed_params = {
                "app_key": str(app_key).strip(),
                "timestamp": timestamp,
                "sign_method": "sha256",
                "offerType": "1",
                "userToken": str(user_token).strip(),
                "categoryL1": str(cat_id),
                "page": str(page),
                "limit": "20"
            }
            feed_params["sign"] = sign_lazada(feed_path, feed_params, app_secret)

            try:
                res = requests.get(feed_url, params=feed_params, timeout=25)
                if res.status_code != 200:
                    continue
                
                feed_json = res.json()
                if str(feed_json.get("code", "0")) != "0":
                    continue

                result_data = feed_json.get("result", {}) or feed_json.get("data", {})
                prods = []
                if isinstance(result_data, dict):
                    prods = result_data.get("products", []) or result_data.get("data", []) or result_data.get("items", [])
                elif isinstance(result_data, list):
                    prods = result_data

                for prod in prods:
                    p_id = str(prod.get("productId") or prod.get("product_id") or prod.get("id") or "").strip()
                    p_name = prod.get("productName") or prod.get("title") or prod.get("name") or ""
                    pics = prod.get("pictures") or prod.get("image_url") or prod.get("image") or prod.get("picUrl")

                    img_url = ""
                    if isinstance(pics, list) and len(pics) > 0:
                        img_url = pics[0]
                    elif isinstance(pics, str):
                        img_url = pics

                    img_url = normalize_image_url(img_url)

                    if p_id and img_url and p_id not in seen_ids:
                        seen_ids.add(p_id)
                        candidates.append({
                            "id": p_id,
                            "title": p_name,
                            "image": img_url,
                            "discountPrice": prod.get("discountPrice"),
                            "price": prod.get("price") or prod.get("originalPrice"),
                            "outOfStock": prod.get("outOfStock"),
                            "categoryL1": cat_id,
                            "desc": f"Promosi khas {p_name} di Lazada."
                        })
                        if len(candidates) >= max_items:
                            break
            except Exception as e:
                print(f"⚠️ [FEED WARN] Gagal menarik feed (Category={cat_id}, Page={page}): {e}")
                continue

    return candidates

def generate_tracking_link(app_key, app_secret, user_token, product_id):
    """Menjana pautan affiliate tracking rasmi untuk Product ID terpilih."""
    domain = "api.lazada.com.my"
    base_url = f"https://{domain}/rest"
    
    # 1. /marketing/product/link
    link_path = "/marketing/product/link"
    link_url = f"{base_url}{link_path}"
    timestamp = str(int(time.time() * 1000))
    
    link_params = {
        "app_key": str(app_key).strip(),
        "timestamp": timestamp,
        "sign_method": "sha256",
        "userToken": str(user_token).strip(),
        "productId": str(product_id)
    }
    link_params["sign"] = sign_lazada(link_path, link_params, app_secret)

    try:
        res = requests.get(link_url, params=link_params, timeout=25)
        if res.status_code == 200:
            link_json = res.json()
            if str(link_json.get("code", "0")) == "0":
                res_obj = link_json.get("result", {})
                if isinstance(res_obj, dict):
                    data_obj = res_obj.get("data", {})
                    if isinstance(data_obj, dict):
                        link = data_obj.get("trackingLink") or data_obj.get("link")
                        if link:
                            return link
                if link_json.get("trackingLink"):
                    return link_json.get("trackingLink")
    except Exception:
        pass

    # 2. Fallback /marketing/getlink
    getlink_path = "/marketing/getlink"
    getlink_url = f"{base_url}{getlink_path}"
    timestamp_gl = str(int(time.time() * 1000))

    getlink_params = {
        "app_key": str(app_key).strip(),
        "timestamp": timestamp_gl,
        "sign_method": "sha256",
        "userToken": str(user_token).strip(),
        "inputType": "productId",
        "inputValue": str(product_id),
        "subId1": "telegram_channel"
    }
    getlink_params["sign"] = sign_lazada(getlink_path, getlink_params, app_secret)

    try:
        res_gl = requests.get(getlink_url, params=getlink_params, timeout=25)
        if res_gl.status_code == 200:
            gl_json = res_gl.json()
            if str(gl_json.get("code", "0")) == "0":
                res_obj = gl_json.get("result", {})
                if isinstance(res_obj, dict):
                    data_obj = res_obj.get("data", {})
                    if isinstance(data_obj, dict):
                        info_list = data_obj.get("productBatchGetLinkInfoList", [])
                        if info_list and isinstance(info_list, list):
                            return info_list[0].get("regularPromotionLink") or info_list[0].get("promotionLink")
    except Exception:
        pass

    return ""

def get_lazada_product(app_key, app_secret, user_token, member_id=None):
    """
    Fungsi legasi pencarian 1 produk real-time dari Lazada API.
    """
    candidates = fetch_targeted_lazada_candidates(app_key, app_secret, user_token, max_items=1)
    if not candidates:
        return False, {"error": "Product Feed API memulangkan 0 produk."}

    prod = candidates[0]
    link = generate_tracking_link(app_key, app_secret, user_token, prod["id"])

    if not link or not prod["image"]:
        return False, {"error": "Gagal menjana tracking link atau gambar."}

    return True, {
        "id": prod["id"],
        "title": prod["title"],
        "desc": prod["desc"],
        "image": prod["image"],
        "link": link
    }