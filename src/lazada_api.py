import time
import hmac
import hashlib
import random
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

def is_valid_product(prod):
    """Semakan kualiti produk: menapis barangan percuma dan harga tidak munasabah"""
    p_name = str(prod.get("productName") or prod.get("title") or prod.get("name") or "").lower()
    
    # 1. Menapis barangan percuma / sampel / cenderahati
    if any(kw in p_name for kw in EXCLUDE_KEYWORDS):
        return False

    # 2. Menapis harga di luar julat RM 0.00 - RM 500.00
    raw_price = (
        prod.get("discountPrice") 
        or prod.get("price") 
        or prod.get("salePrice") 
        or prod.get("priceAmount") 
        or 0
    )
    try:
        price = float(raw_price)
    except (ValueError, TypeError):
        price = 0.0

    if price < 0.0 or price > 500.0:
        return False

    return True

def get_lazada_product(app_key, app_secret, user_token, member_id=None, redis_url=None, redis_token=None):
    """
    Menarik produk real-time dan menjana pautan affiliate sebenar dari Lazada API.
    Melakukan pemilihan secara dinamik dan menapis barangan percuma / harga melampau.
    """
    domain = "api.lazada.com.my"
    base_url = f"https://{domain}/rest"

    feed_path = "/marketing/product/feed"
    feed_url = f"{base_url}{feed_path}"
    
    found_products = []
    
    # Rawak helaian muka surat (page 1 hingga 3) untuk variasi produk dinamik
    random_page = str(random.randint(1, 3))
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
            "page": random_page,
            "limit": "20"
        }
        feed_params["sign"] = sign_lazada(feed_path, feed_params, app_secret)

        try:
            res_feed = requests.get(feed_url, params=feed_params, timeout=25)
            feed_json = res_feed.json()

            code = feed_json.get("code")
            if res_feed.status_code == 200 and (code is None or str(code) == "0"):
                result_data = feed_json.get("result", {}) or feed_json.get("data", {})
                
                prods = []
                if isinstance(result_data, dict):
                    prods = result_data.get("products", []) or result_data.get("data", []) or result_data.get("items", [])
                elif isinstance(result_data, list):
                    prods = result_data

                if prods:
                    # Tapis produk yang sah sahaja (RM 0 - RM 500 & Bukan Not For Sale)
                    valid_prods = [p for p in prods if is_valid_product(p)]
                    if valid_prods:
                        # Rawakkan susunan produk supaya sentiasa dinamik
                        random.shuffle(valid_prods)
                        found_products = valid_prods
                        break
        except Exception:
            continue

    if not found_products:
        return False, {
            "error": "Product Feed API memulangkan 0 produk sah di dalam julat RM 0-500 (atau semua item tergolong sebagai sampel/Not For Sale).",
            "status": "FEED_FILTERED_EMPTY"
        }

    # Ekstrak produk pertama dari senarai yang telah dirawakkan
    target_product = None
    for prod in found_products:
        p_id = prod.get("productId") or prod.get("product_id") or prod.get("id")
        p_name = prod.get("productName") or prod.get("title") or prod.get("name")
        pics = prod.get("pictures") or prod.get("image_url") or prod.get("image") or prod.get("picUrl")

        img_url = ""
        if isinstance(pics, list) and len(pics) > 0:
            img_url = pics[0]
        elif isinstance(pics, str):
            img_url = pics

        if p_id and img_url:
            target_product = {
                "id": str(p_id),
                "title": p_name or f"Produk Lazada #{p_id}",
                "image": img_url
            }
            break

    if not target_product:
        return False, {"error": "Gagal mengekstrak Product ID dan URL Gambar yang sah daripada Product Feed."}

    product_id = target_product["id"]
    product_name = target_product["title"]
    real_image = target_product["image"]

    # ==================================================
    # LANGKAH 2A: Generate Tracking Link (/marketing/product/link)
    # ==================================================
    tracking_link = ""
    link_path = "/marketing/product/link"
    link_url = f"{base_url}{link_path}"
    timestamp_link = str(int(time.time() * 1000))

    link_params = {
        "app_key": str(app_key).strip(),
        "timestamp": timestamp_link,
        "sign_method": "sha256",
        "userToken": str(user_token).strip(),
        "productId": str(product_id)
    }
    link_params["sign"] = sign_lazada(link_path, link_params, app_secret)

    try:
        res_link = requests.get(link_url, params=link_params, timeout=25)
        link_json = res_link.json()
        link_code = link_json.get("code")

        if res_link.status_code == 200 and (link_code is None or str(link_code) == "0"):
            res_obj = link_json.get("result", {})
            if isinstance(res_obj, dict):
                data_obj = res_obj.get("data", {})
                if isinstance(data_obj, dict):
                    tracking_link = data_obj.get("trackingLink") or data_obj.get("link") or ""
            if not tracking_link:
                tracking_link = link_json.get("trackingLink", "")
    except Exception:
        pass

    # ==================================================
    # LANGKAH 2B: Fallback ke Batch Get Link (/marketing/getlink)
    # ==================================================
    if not tracking_link:
        getlink_path = "/marketing/getlink"
        getlink_url = f"{base_url}{getlink_path}"
        timestamp_gl = str(int(time.time() * 1000))

        getlink_params = {
            "app_key": str(app_key).strip(),
            "timestamp": timestamp_gl,
            "sign_method": "sha256",
            "userToken": str(user_token).strip(),
            "inputType": "productId",
            "inputValue": str(product_id)
        }
        getlink_params["sign"] = sign_lazada(getlink_path, getlink_params, app_secret)

        try:
            res_gl = requests.get(getlink_url, params=getlink_params, timeout=25)
            gl_json = res_gl.json()
            gl_code = gl_json.get("code")

            if res_gl.status_code == 200 and (gl_code is None or str(gl_code) == "0"):
                res_obj = gl_json.get("result", {})
                if isinstance(res_obj, dict):
                    data_obj = res_obj.get("data", {})
                    if isinstance(data_obj, dict):
                        info_list = data_obj.get("productBatchGetLinkInfoList", [])
                        if info_list and isinstance(info_list, list):
                            item_info = info_list[0]
                            tracking_link = item_info.get("regularPromotionLink") or item_info.get("promotionLink") or ""
        except Exception:
            pass

    # Semakan Ketat (NO DUMMY ALLOWED)
    if not tracking_link or not real_image:
        return False, {
            "error": "Lazada API tidak memulangkan Link Affiliate atau Imej yang sah. Versi dummy dilarang keras.",
            "product_id": product_id,
            "image": real_image,
            "link": tracking_link
        }

    return True, {
        "id": product_id,
        "title": product_name,
        "desc": f"Promosi khas {product_name} di Lazada.",
        "image": real_image,
        "link": tracking_link
    }