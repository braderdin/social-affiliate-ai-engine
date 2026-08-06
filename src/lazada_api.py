import time
import hmac
import hashlib
import random
import re
import requests

EXCLUDE_PHRASES = [
    "not for sale", "[not for sale]", "free gift", "gift with purchase"
]
EXCLUDE_WORDS = [
    "foc", "gwp", "sample", "tester"
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

def extract_price_val(val):
    """Mengekstrak nilai float pertama dari pelbagai format data harga JSON."""
    if val is None:
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, dict):
        v = val.get("amount") or val.get("value") or val.get("price") or 0.0
        return extract_price_val(v)
    val_str = str(val).strip()
    match = re.search(r'(\d+(?:\.\d+)?)', val_str)
    if match:
        try:
            return float(match.group(1))
        except (ValueError, TypeError):
            return 0.0
    return 0.0

def get_valid_product_price(prod):
    """
    Menyemak julat harga produk (RM 2.00 - RM 500.00):
    1. Semak harga diskaun/promosi. Jika 2.0 <= discount_price <= 500.0, guna harga diskaun.
    2. Jika harga diskaun tiada ATAU di luar julat (RM < 2 atau RM > 500), langkau harga diskaun 
       dan semak harga asal/normal (tanpa diskaun).
    3. Jika harga asal/normal berada dalam julat 2.0 <= normal_price <= 500.0, guna harga asal.
    4. Jika tiada medan harga dipulangkan oleh Feed API, benarkan sebagai produk sah lalai.
    5. Jika harga eksplisit berada di luar julat, pulangkan 0.0 (ditapis).
    """
    # 1. Kumpul nilai harga diskaun/promosi
    promo_values = []
    for key in ["discountPrice", "salePrice", "special_price", "discount_price", "promotionPrice", "specialPrice"]:
        v = extract_price_val(prod.get(key))
        if v > 0:
            promo_values.append(v)

    if isinstance(prod.get("price"), dict):
        v = extract_price_val(prod.get("price", {}).get("discountPrice")) or extract_price_val(prod.get("price", {}).get("salePrice"))
        if v > 0:
            promo_values.append(v)

    # Semak jika mana-mana harga diskaun berada dalam julat RM 2.00 - RM 500.00
    for p_val in promo_values:
        if 2.0 <= p_val <= 500.0:
            return p_val

    # 2. Jika harga diskaun tiada / luar julat, semak harga normal / asal
    normal_values = []
    for key in ["price", "originalPrice", "priceAmount", "itemPrice", "original_price"]:
        v = extract_price_val(prod.get(key))
        if v > 0:
            normal_values.append(v)

    if isinstance(prod.get("price"), dict):
        v = extract_price_val(prod.get("price", {}).get("amount")) or extract_price_val(prod.get("price", {}).get("value")) or extract_price_val(prod.get("price", {}).get("originalPrice"))
        if v > 0:
            normal_values.append(v)

    for p_val in normal_values:
        if 2.0 <= p_val <= 500.0:
            return p_val

    # 3. Jika tiada sebarang medan harga dipulangkan dalam JSON Feed API
    if not promo_values and not normal_values:
        return 10.0  # Produk dianggap sah dalam julat lalai jika API tidak sertakan medan harga

    return 0.0

def is_valid_product(prod):
    """Semakan kualiti produk: menapis barangan percuma dan harga di luar RM 2.00 - RM 500.00"""
    p_name = str(prod.get("productName") or prod.get("title") or prod.get("name") or "").lower()
    
    # 1. Menapis frasa percuma / cenderahati
    if any(phrase in p_name for phrase in EXCLUDE_PHRASES):
        return False

    # 2. Menapis perkataan percuma secara tepat (\b word boundary)
    for word in EXCLUDE_WORDS:
        if re.search(r'\b' + re.escape(word) + r'\b', p_name):
            return False

    # 3. Semakan julat harga munasabah (RM 2.00 - RM 500.00)
    valid_price = get_valid_product_price(prod)
    if valid_price == 0.0:
        return False

    return True

def get_lazada_product_candidates(app_key, app_secret, user_token, member_id=None):
    """
    Mengumpul sekurang-kurangnya 25-35 produk UNIK dari pelbagai kategori dari Lazada Feed API
    merentasi offerType 1, 2, 3 dan muka surat 1-5.
    """
    domain = "api.lazada.com.my"
    base_url = f"https://{domain}/rest"
    feed_path = "/marketing/product/feed"
    feed_url = f"{base_url}{feed_path}"

    unique_candidates = []
    seen_ids = set()

    # Mula dari Page 1 hingga 5 secara berurutan, semak offerType 1, 2, 3
    for page in range(1, 6):
        for offer_type in ["1", "2", "3"]:
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
                            pics = p.get("pictures") or p.get("image_url") or p.get("image") or p.get("picUrl")
                            
                            img_url = ""
                            if isinstance(pics, list) and len(pics) > 0:
                                img_url = pics[0]
                            elif isinstance(pics, str):
                                img_url = pics

                            if p_id and img_url and p_id not in seen_ids:
                                seen_ids.add(p_id)
                                unique_candidates.append(p)
            except Exception:
                continue

        if len(unique_candidates) >= 25:
            break

    if not unique_candidates:
        return False, {
            "error": "Product Feed API memulangkan 0 produk sah di dalam julat harga RM 2-500 merentasi Page 1-5.",
            "status": "FEED_FILTERED_EMPTY"
        }

    # Rawakkan susunan produk untuk menjamin variasi pelbagai kategori
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
    """Fungsi sokongan terus bagi kegunaan skrip diagnostik"""
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