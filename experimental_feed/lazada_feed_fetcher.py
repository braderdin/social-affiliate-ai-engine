import os
import re
import time
import hmac
import hashlib
import requests

def get_lazada_credentials():
    """
    Membaca kunci pengesahan Lazada mengikut struktur .env.example.
    Memulangkan: (app_key, app_secret, user_token, status_dict)
    """
    k_app_key = os.getenv("LAZADA_APP_KEY", "").strip()
    k_lite_app_key = os.getenv("LAZADA_LiteApp_Key", "").strip()
    
    k_app_secret = os.getenv("LAZADA_APP_SECRET", "").strip()
    k_lite_app_secret = os.getenv("LAZADA_LiteApp_Secret", "").strip()
    
    user_token = os.getenv("LAZADA_USER_TOKEN", "").strip()
    member_id = os.getenv("LAZADA_MEMBER_ID", "").strip()

    app_key = k_app_key or k_lite_app_key
    app_secret = k_app_secret or k_lite_app_secret

    status = {
        "LAZADA_APP_KEY": bool(k_app_key),
        "LAZADA_LiteApp_Key": bool(k_lite_app_key),
        "LAZADA_APP_SECRET": bool(k_app_secret),
        "LAZADA_LiteApp_Secret": bool(k_lite_app_secret),
        "LAZADA_USER_TOKEN": bool(user_token),
        "LAZADA_MEMBER_ID": bool(member_id),
    }

    return app_key, app_secret, user_token, status

def generate_lazada_signature(api_path, params, app_secret):
    """
    Menjana tandatangan HMAC-SHA256 mengikut spesifikasi rasmi Gateway Lazada.
    """
    sorted_keys = sorted(params.keys())
    query_string = api_path
    
    for k in sorted_keys:
        v = params[k]
        if k != "sign" and v is not None:
            query_string += f"{k}{v}"

    sign_bytes = hmac.new(
        app_secret.encode("utf-8"),
        query_string.encode("utf-8"),
        hashlib.sha256
    ).digest()

    return sign_bytes.hex().upper()

def extract_items_from_json(data):
    """
    Mengekstrak senarai produk daripada pelbagai struktur respon JSON bertingkat Lazada.
    Menyokong: data['result']['data'], data['data'], data['result'], dll.
    """
    if isinstance(data, list):
        return data

    if isinstance(data, dict):
        # Struktur Utama Lazada Feed: data -> result -> data
        res = data.get("result")
        if isinstance(res, dict):
            if isinstance(res.get("data"), list):
                return res.get("data")
            if isinstance(res.get("products"), list):
                return res.get("products")
            if isinstance(res.get("items"), list):
                return res.get("items")
        elif isinstance(res, list):
            return res

        # Struktur Alternatif: data -> data
        d = data.get("data")
        if isinstance(d, list):
            return d
        if isinstance(d, dict) and isinstance(d.get("products"), list):
            return d.get("products")

        # Struktur Kunci Langsung
        for k in ["products", "items", "feedList"]:
            if isinstance(data.get(k), list):
                return data.get(k)

    return []

def parse_price(val):
    """Mengekstrak dan menukar nilai harga ke bentuk float."""
    if val is None:
        return 0.0
    try:
        cleaned = re.sub(r'[^\d.]', '', str(val))
        return float(cleaned) if cleaned else 0.0
    except ValueError:
        return 0.0

def fetch_products_from_feed(pages=20, limit_per_page=25):
    """
    Mengambil produk mentah daripada Lazada Official Marketing API Feed (Page 1 hingga 20).
    """
    app_key, app_secret, user_token, env_status = get_lazada_credentials()

    if not app_key or not app_secret or not user_token:
        missing_keys = [k for k, v in env_status.items() if not v]
        return [], [f"❌ Kunci Lazada tidak lengkap di .env.local: {missing_keys}"], env_status

    api_path = "/marketing/product/feed"
    endpoint = "https://api.lazada.com.my/rest/marketing/product/feed"

    all_raw_products = []
    errors = []

    for page in range(1, pages + 1):
        params = {
            "app_key": str(app_key),
            "timestamp": str(int(time.time() * 1000)),
            "sign_method": "sha256",
            "offerType": "1",
            "userToken": str(user_token),
            "page": str(page),
            "limit": str(limit_per_page)
        }
        
        params["sign"] = generate_lazada_signature(api_path, params, app_secret)

        try:
            res = requests.get(endpoint, params=params, timeout=15)
            if res.status_code == 200:
                data = res.json()
                items = extract_items_from_json(data)

                if items:
                    all_raw_products.extend(items)
                else:
                    msg = data.get("message") or data.get("msg") or data.get("error_msg") or "Tiada item dalam respon JSON"
                    errors.append(f"⚠️ Page {page}: Respon diterima tetapi 0 item diekstrak ({msg})")
            else:
                errors.append(f"⚠️ Page {page} HTTP {res.status_code}: {res.text[:120]}")
        except Exception as e:
            errors.append(f"⚠️ Page {page} Ralat Rangkaian: {str(e)}")

    return all_raw_products, errors, env_status

def filter_products_by_keywords_and_price(raw_products, keywords, min_price=10.0, max_price=500.0):
    """
    Menapis produk mentah mengikut:
    1. Julat harga RM 10.00 hingga RM 500.00 sahaja.
    2. Kata kunci AI (padanan perkataan di dalam tajuk produk).
    """
    if not raw_products or not keywords:
        return [], 0

    matched_products = []
    seen_ids = set()
    price_filtered_count = 0

    for item in raw_products:
        p_id = str(item.get("productId") or item.get("id") or "").strip()
        p_name = item.get("productName") or item.get("title") or ""

        if not p_id or not p_name or p_id in seen_ids:
            continue

        raw_price_val = item.get("discountPrice") or item.get("price") or item.get("salesPrice") or 0.0
        price = parse_price(raw_price_val)

        # Tapisan harga RM 10 - RM 500
        if price < min_price or price > max_price:
            price_filtered_count += 1
            continue

        p_name_lower = p_name.lower()
        matched_kw = None

        for kw in keywords:
            kw_clean = str(kw).strip().lower()
            if not kw_clean:
                continue
            
            kw_tokens = kw_clean.split()
            if all(token in p_name_lower for token in kw_tokens):
                matched_kw = kw
                break

        if matched_kw:
            pictures = item.get("pictures") or []
            img_url = ""
            if isinstance(pictures, list) and len(pictures) > 0:
                img_url = pictures[0]
            elif isinstance(pictures, str):
                img_url = pictures

            commission_rate = item.get("totalCommissionRate") or item.get("sameProductTotalCommissionRate") or ">=20%"

            seen_ids.add(p_id)
            matched_products.append({
                "product_id": p_id,
                "title": p_name,
                "price": price,
                "image_url": img_url,
                "commission_rate": str(commission_rate),
                "keyword": matched_kw,
                "original_url": f"https://www.lazada.com.my/products/-i{p_id}.html"
            })

    return matched_products, price_filtered_count

def batch_convert_to_affiliate(product_items):
    """
    Menukar Product ID yang ditapis kepada pautan affiliate rasmi via API /marketing/getlink.
    """
    app_key, app_secret, user_token, _ = get_lazada_credentials()

    if not product_items or not app_key or not app_secret or not user_token:
        return [], ["❌ Tiada produk untuk ditukar atau kunci Lazada tidak lengkap."]

    product_ids = [item["product_id"] for item in product_items]
    ids_payload = ",".join(product_ids[:100])

    api_path = "/marketing/getlink"
    endpoint = "https://api.lazada.com.my/rest/marketing/getlink"

    converted_items = []
    errors = []

    params = {
        "app_key": str(app_key),
        "timestamp": str(int(time.time() * 1000)),
        "sign_method": "sha256",
        "userToken": str(user_token),
        "inputType": "productId",
        "inputValue": ids_payload
    }
    params["sign"] = generate_lazada_signature(api_path, params, app_secret)

    try:
        res = requests.get(endpoint, params=params, timeout=20)
        if res.status_code == 200:
            res_data = res.json()
            data_obj = res_data.get("data") or res_data.get("result") or {}
            if isinstance(data_obj, dict):
                info_list = data_obj.get("productBatchGetLinkInfoList") or []
            else:
                info_list = []

            link_map = {}
            for info in info_list:
                pid = str(info.get("productId") or "").strip()
                aff_link = info.get("regularPromotionLink") or info.get("mmPromotionLink") or ""
                if pid and aff_link:
                    link_map[pid] = aff_link

            for p in product_items:
                pid = p["product_id"]
                if pid in link_map:
                    p["affiliate_link"] = link_map[pid]
                    converted_items.append(p)
                else:
                    errors.append(f"⚠️ Product ID {pid} ('{p['title'][:30]}...'): API getlink tidak memulangkan pautan.")
        else:
            errors.append(f"⚠️ Convert HTTP {res.status_code}: {res.text[:120]}")
    except Exception as e:
        errors.append(f"⚠️ Convert Error: {str(e)}")

    return converted_items, errors