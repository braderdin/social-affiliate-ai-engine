import time
import hmac
import hashlib
import requests

def sign_lazada(api_path, params, app_secret):
    sorted_params = sorted(params.items())
    sign_str = api_path
    for k, v in sorted_params:
        sign_str += f"{k}{v}"
    
    return hmac.new(
        app_secret.encode('utf-8'),
        sign_str.encode('utf-8'),
        hashlib.sha256
    ).hexdigest().upper()

def get_lazada_product(app_key, app_secret, member_id, keyword="dapur"):
    domain = "api.lazada.com.my"
    # Baiki API Path mengikut struktur Open Platform rasmi Lazada
    api_path = "/affiliate/product/query"
    url = f"https://{domain}/rest{api_path}"
    
    params = {
        "app_key": app_key,
        "timestamp": str(int(time.time() * 1000)),
        "sign_method": "sha256",
        "keywords": keyword,
        "limit": "5"
    }
    
    params["sign"] = sign_lazada(api_path, params, app_secret)
    
    try:
        response = requests.get(url, params=params, timeout=15)
        res_json = response.json()
        
        if response.status_code == 200 and res_json.get("code") == "0":
            products = res_json.get("result", {}).get("products", [])
            if products:
                prod = products[0]
                return True, {
                    "id": str(prod.get("item_id")),
                    "title": prod.get("title"),
                    "desc": prod.get("description", "Barangan berkualiti untuk kegunaan harian."),
                    "image": prod.get("image_url"),
                    "link": prod.get("click_url")
                }
        return False, res_json
    except Exception as e:
        return False, str(e)