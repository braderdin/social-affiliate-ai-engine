import time
import hmac
import hashlib
import random
import re
import requests

EXCLUDE_KEYWORDS = [
    "not for sale", "[not for sale]", "gwp", "free gift", 
    "sample", "tester", "foc", "gift with purchase"
]

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

def parse_price(prod):
    """Membaca dan membersihkan pelbagai format harga dari Lazada Feed API secara tepat"""
    price_keys = [
        "discountPrice", "price", "salePrice", "priceAmount", 
        "originalPrice", "itemPrice", "special_price"
    ]
    for key in price_keys:
        val = prod.get(key)
        if val is None and isinstance(prod.get("price"), dict):
            val = prod.get("price", {}).get("amount") or prod.get("price", {}).get("value")

        if val is not None:
            try:
                # Bersihkan teks harga (Contoh: "RM 45.00" -> "45.00")
                clean_str = re.sub(r'[^0-9.]', '', str(val))
                if clean_str:
                    parsed = float(clean_str)
                    if parsed >= 0:
                        return parsed
            except (ValueError, TypeError):
                continue
    return 0.0

def is_valid_product(prod):
    """Semakan kualiti produk: menapis barangan percuma dan harga tidak munasabah"""
    p_name = str(prod.get("productName") or prod.get("title") or prod.get("name") or "").lower()
    
    # 1. Menapis barangan percuma / sampel / cenderahati
    if any(kw in p_name for kw in EXCLUDE_KEYWORDS):
        return False

    # 2. Semakan harga anjal (RM 0.00 - RM 500.00)
    price = parse_price(prod)
    if price > 500.0:
        return False

    return True

def get_lazada_product_candidates(app_key, app_secret, user_token, member_id=None):
    """
    Melakukan Smart Page Traversal (Page 1 hingga 10) dan mengumpul
    sekurang-kurangnya 15-20 produk UNIK melepasi penapis kualiti.
    """
    domain = "api.lazada.com.my"
    base_url = f"https://{domain}/rest"
    feed_path = "/marketing/product/feed"
    feed_url = f"{base_url}{feed_path}"

    unique_candidates = []
    seen_ids = set()

    pages = list(range(1, 11))
    random.shuffle(pages)

    for page in pages:
        offer_types = ["1", "2", "3"]
        random.shuffle(offer_types)

        for offer_type in offer_types:
            timestamp = str(int(time.time() * 1000))
            feed_params = {
                "app_key": str(app_key).strip(),
                "timestamp": timestamp,
                "sign_method": "sha256",
                "offerType": offer_type,
                "userToken": str(user_token).strip(),
                "page": str(page),
                "limit": "20"
            }
            feed_params["sign"] = sign_lazada(feed_path, feed_params, app_secret)

            try:
                res_feed = requests.get(feed_url, params=feed_params, timeout=20)
                feed_json = res_feed.json()

                code = feed_json.get("code")
                if res_feed.status_code == 200 and (code is None or str(code) == "0"):
                    result_data = feed_json.get("result", {}) or feed_json.get("data", {})
                    
                    prods = []
                    if isinstance(result_data, dict):
                        prods = result_data.get("products", []) or result_data.get("data", []) or result_data.get("items", [])
                    elif isinstance(result_data, list):
                        prods = result_data

                    for p in prods:
                        if is_valid_product(p):
                            p_id = str(p.get("productId") or p.get("product_id") or p.get("id") or "")
                            if p_id and p_id not in seen_ids:
                                seen_ids.add(p_id)
                                unique_candidates.append(p)
            except Exception:
                continue

        # Berhenti jika kolam calon unik sudah mencukupi (>= 15 produk)
        if len(unique_candidates) >= 15:
            break

    if not unique_candidates:
        return False, {
            "error": "Product Feed API memulangkan 0 produk sah di dalam julat RM 0-500 merentasi Page 1-10.",
            "status": "FEED_FILTERED_EMPTY"
        }

    random.shuffle(unique_candidates)
    return True, unique_candidates

def generate_tracking_link(app_key, app_secret, user_token, product_id):
    """Jana pautan affiliate rasmi dari Lazada API"""
    domain = "api.lazada.com.my"
    base_url = f"https://{domain}/rest"

    # Method 2A: /marketing/product/link
    link_path = "/marketing/product/link"
    link_url = f"{base_url}{link_path}"
    link_params = {
        "app_key": str(app_key).strip(),
        "timestamp": str(int(time.time() * 1000)),
        "sign_method": "sha256",
        "userToken": str(user_token).strip(),
        "productId": str(product_id)
    }
    link_params["sign"] = sign_lazada(link_path, link_params, app_secret)

    try:
        res_link = requests.get(link_url, params=link_params, timeout=20)
        link_json = res_link.json()
        if res_link.status_code == 200 and (link_json.get("code") is None or str(link_json.get("code")) == "0"):
            res_obj = link_json.get("result", {})
            if isinstance(res_obj, dict):
                data_obj = res_obj.get("data", {})
                if isinstance(data_obj, dict):
                    link = data_obj.get("trackingLink") or data_obj.get("link") or ""
                    if link: return link
    except Exception:
        pass

    # Method 2B: Fallback /marketing/getlink
    getlink_path = "/marketing/getlink"
    getlink_url = f"{base_url}{getlink_path}"
    getlink_params = {
        "app_key": str(app_key).strip(),
        "timestamp": str(int(time.time() * 1000)),
        "sign_method": "sha256",
        "userToken": str(user_token).strip(),
        "inputType": "productId",
        "inputValue": str(product_id)
    }
    getlink_params["sign"] = sign_lazada(getlink_path, getlink_params, app_secret)

    try:
        res_gl = requests.get(getlink_url, params=getlink_params, timeout=20)
        gl_json = res_gl.json()
        if res_gl.status_code == 200 and (gl_json.get("code") is None or str(gl_json.get("code")) == "0"):
            res_obj = gl_json.get("result", {})
            if isinstance(res_obj, dict):
                data_obj = res_obj.get("data", {})
                if isinstance(data_obj, dict):
                    info_list = data_obj.get("productBatchGetLinkInfoList", [])
                    if info_list and isinstance(info_list, list):
                        return info_list[0].get("regularPromotionLink") or info_list[0].get("promotionLink") or ""
    except Exception:
        pass

    return ""

def get_lazada_product(app_key, app_secret, user_token, member_id=None):
    """Fungsi sokongan langsung untuk pipeline"""
    ok, candidates = get_lazada_product_candidates(app_key, app_secret, user_token, member_id)
    if not ok:
        return False, candidates

    for prod in candidates:
        p_id = prod.get("productId") or prod.get("product_id") or prod.get("id")
        p_name = prod.get("productName") or prod.get("title") or prod.get("name")
        pics = prod.get("pictures") or prod.get("image_url") or prod.get("image") or prod.get("picUrl")

        img_url = ""
        if isinstance(pics, list) and len(pics) > 0:
            img_url = pics[0]
        elif isinstance(pics, str):
            img_url = pics

        if p_id and img_url:
            tracking_link = generate_tracking_link(app_key, app_secret, user_token, p_id)
            if tracking_link:
                return True, {
                    "id": str(p_id),
                    "title": p_name or f"Produk Lazada #{p_id}",
                    "desc": f"Promosi khas {p_name} di Lazada.",
                    "image": img_url,
                    "link": tracking_link
                }

    return False, {"error": "Gagal menjana pautan affiliate bagi senarai calon produk Feed API."}