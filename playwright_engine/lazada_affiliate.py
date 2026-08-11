import os
import time
import hmac
import hashlib
import requests

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

def convert_product_to_affiliate(product_dict):
    """
    Menukar pautan asal produk kepada pautan affiliate rasmi mengguna API Lazada Official.
    Mengembalikan mesej ralat rasmi daripada respon Lazada jika gagal.
    """
    app_key = os.getenv("LAZADA_APP_KEY", "").strip()
    app_secret = os.getenv("LAZADA_APP_SECRET", "").strip()
    user_token = os.getenv("LAZADA_USER_TOKEN", "").strip()

    if not app_key or not app_secret or not user_token:
        return False, "Kunci API Lazada (LAZADA_APP_KEY / LAZADA_APP_SECRET / LAZADA_USER_TOKEN) tidak lengkap dalam persekitaran."

    product_id = str(product_dict.get("product_id") or "").strip()
    if not product_id:
        return False, "Product ID tidak sah."

    domain = "api.lazada.com.my"
    base_url = f"https://{domain}/rest"

    # 1. Percubaan Utama: /marketing/product/link
    link_path = "/marketing/product/link"
    link_url = f"{base_url}{link_path}"
    timestamp = str(int(time.time() * 1000))
    
    link_params = {
        "app_key": app_key,
        "timestamp": timestamp,
        "sign_method": "sha256",
        "userToken": user_token,
        "productId": product_id
    }
    link_params["sign"] = sign_lazada(link_path, link_params, app_secret)

    error_reason = ""
    try:
        res = requests.get(link_url, params=link_params, timeout=20)
        if res.status_code == 200:
            link_json = res.json()
            code = str(link_json.get("code", "0"))
            if code == "0":
                res_obj = link_json.get("result", {})
                if isinstance(res_obj, dict):
                    data_obj = res_obj.get("data", {})
                    if isinstance(data_obj, dict):
                        link = data_obj.get("trackingLink") or data_obj.get("link")
                        if link:
                            updated_item = dict(product_dict)
                            updated_item["affiliate_link"] = link
                            updated_item["commission_rate"] = ">=20%"
                            return True, updated_item
            else:
                error_reason = f"Lazada API Code {code}: {link_json.get('message', 'Tiada mesej')}"
        else:
            error_reason = f"HTTP {res.status_code}: {res.text}"
    except Exception as e:
        error_reason = f"Ralat Rangkaian: {str(e)}"

    # 2. Percubaan Sandaran: /marketing/getlink
    getlink_path = "/marketing/getlink"
    getlink_url = f"{base_url}{getlink_path}"
    timestamp_gl = str(int(time.time() * 1000))

    getlink_params = {
        "app_key": app_key,
        "timestamp": timestamp_gl,
        "sign_method": "sha256",
        "userToken": user_token,
        "inputType": "productId",
        "inputValue": product_id,
        "subId1": "telegram_channel"
    }
    getlink_params["sign"] = sign_lazada(getlink_path, getlink_params, app_secret)

    try:
        res_gl = requests.get(getlink_url, params=getlink_params, timeout=20)
        if res_gl.status_code == 200:
            gl_json = res_gl.json()
            code_gl = str(gl_json.get("code", "0"))
            if code_gl == "0":
                res_obj = gl_json.get("result", {})
                if isinstance(res_obj, dict):
                    data_obj = res_obj.get("data", {})
                    if isinstance(data_obj, dict):
                        info_list = data_obj.get("productBatchGetLinkInfoList", [])
                        if info_list and isinstance(info_list, list):
                            link = info_list[0].get("regularPromotionLink") or info_list[0].get("promotionLink")
                            if link:
                                updated_item = dict(product_dict)
                                updated_item["affiliate_link"] = link
                                updated_item["commission_rate"] = ">=20%"
                                return True, updated_item
            else:
                error_reason += f" | Fallback API Code {code_gl}: {gl_json.get('message', '')}"
    except Exception as e:
        error_reason += f" | Fallback Error: {str(e)}"

    return False, f"Gagal tukar link -> {error_reason}"

def convert_batch_to_affiliate(scraped_products):
    """Memproses penukaran affiliate pukal dengan log yang terperinci bagi setiap produk."""
    successful_items = []
    failed_logs = []

    for prod in scraped_products:
        success, result = convert_product_to_affiliate(prod)
        p_id = prod.get("product_id", "UNKNOWN")
        title = prod.get("title", "Tiada Tajuk")

        if success:
            successful_items.append(result)
        else:
            failed_logs.append({
                "product_id": p_id,
                "title": title,
                "reason": result
            })

    return successful_items, failed_logs