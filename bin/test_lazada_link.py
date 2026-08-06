import os
import sys
import time
import hmac
import hashlib
import json
import traceback
import requests
from dotenv import load_dotenv

# 1. Baca fail .env.local
load_dotenv('.env.local')

# 2. Ambil pemboleh ubah persekitaran mengikut .env.example
LAZADA_LITEAPP_KEY = os.getenv("LAZADA_LiteApp_Key") or os.getenv("LAZADA_APP_KEY")
LAZADA_LITEAPP_SECRET = os.getenv("LAZADA_LiteApp_Secret") or os.getenv("LAZADA_APP_SECRET")
LAZADA_USER_TOKEN = os.getenv("LAZADA_USER_TOKEN")
LAZADA_MEMBER_ID = os.getenv("LAZADA_MEMBER_ID")

def sanitize_value(val):
    if not val:
        return ""
    val = str(val).strip()
    if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
        val = val[1:-1]
    return val.strip()

def sign_lazada_request(api_path, params, app_secret):
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

def test_fetch_real_lazada_affiliate():
    print("==================================================")
    print("🔍 [TEST DIAGNOSTIC] Lazada Marketing Feed & GetLink API")
    print("==================================================\n")

    app_key = sanitize_value(LAZADA_LITEAPP_KEY)
    app_secret = sanitize_value(LAZADA_LITEAPP_SECRET)
    user_token = sanitize_value(LAZADA_USER_TOKEN)
    member_id = sanitize_value(LAZADA_MEMBER_ID)

    # Semakan Kunci Wajib (NO DUMMY ALLOWED)
    missing = []
    if not app_key: missing.append("LAZADA_LiteApp_Key / LAZADA_APP_KEY")
    if not app_secret: missing.append("LAZADA_LiteApp_Secret / LAZADA_APP_SECRET")
    if not user_token: missing.append("LAZADA_USER_TOKEN")

    if missing:
        print("🔴 [RALAT KRITIKAL KUNCI API]: Kunci berikut tidak ditemui di dalam .env.local:")
        for k in missing:
            print(f"   ❌ {k}")
        raise ValueError(f"Kunci API Lazada tidak lengkap: {missing}")

    print(f"🟢 [INFO] LiteApp Key : {app_key}")
    print(f"🟢 [INFO] User Token  : {user_token[:6]}...{user_token[-6:]}")
    if member_id:
        print(f"🟢 [INFO] Member ID   : {member_id}")

    domain = "api.lazada.com.my"
    base_url = f"https://{domain}/rest"

    # LANGKAH 1: Get Product Feed (/marketing/product/feed)
    feed_path = "/marketing/product/feed"
    feed_url = f"{base_url}{feed_path}"
    
    found_products = []
    selected_offer_type = None

    for offer_type in ["1", "2", "3"]:
        timestamp = str(int(time.time() * 1000))
        feed_params = {
            "app_key": app_key,
            "timestamp": timestamp,
            "sign_method": "sha256",
            "offerType": offer_type,
            "userToken": user_token,
            "page": "1",
            "limit": "20"
        }
        feed_params["sign"] = sign_lazada_request(feed_path, feed_params, app_secret)

        print(f"\n1️⃣ [STEP 1] Memanggil Feed API (offerType={offer_type}, limit=20)...")
        try:
            res_feed = requests.get(feed_url, params=feed_params, timeout=25)
            print(f"📊 [HTTP STATUS CODE]: {res_feed.status_code}")

            try:
                feed_json = res_feed.json()
            except json.JSONDecodeError:
                print("🔴 [RALAT FORMAT RESPONS]: Response bukan format JSON.")
                continue

            code = feed_json.get("code")
            if res_feed.status_code != 200 or (code is not None and str(code) != "0"):
                print(f"⚠️ [NOTICE offerType={offer_type}] Response Code: {code} | Msg: {feed_json.get('message')}")
                continue

            result_data = feed_json.get("result", {}) or feed_json.get("data", {})
            
            prods = []
            if isinstance(result_data, dict):
                prods = result_data.get("products", []) or result_data.get("data", []) or result_data.get("items", [])
            elif isinstance(result_data, list):
                prods = result_data

            if prods:
                print(f"🟢 [FEED SUCCESS] Ditemui {len(prods)} produk di bawah offerType={offer_type}!")
                found_products = prods
                selected_offer_type = offer_type
                break

        except Exception as e:
            print(f"⚠️ Ralat carian offerType={offer_type}: {e}")

    if not found_products:
        print("\n==================================================")
        print("🔴 [RALAT DATA KOSONG]: Product Feed memulangkan 0 produk.")
        print("==================================================")
        raise Exception("Tiada data produk ditemui di dalam response Product Feed API bagi akaun ini.")

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
                "name": p_name or f"Produk Lazada #{p_id}",
                "image": img_url
            }
            break

    if not target_product:
        print("\n🔴 [RALAT DATA TAK LENGKAP]: Product ID atau Gambar adalah kosong.")
        raise ValueError("Gagal mengekstrak Product ID dan URL Gambar yang sah dari Product Feed.")

    product_id = target_product["id"]
    product_name = target_product["name"]
    real_image = target_product["image"]

    print("\n🟢 [STEP 1 OK] Produk Terpilih:")
    print(f"   📌 Product ID   : {product_id}")
    print(f"   📌 Product Name : {product_name}")
    print(f"   🖼️ Real Image   : {real_image}")

    # LANGKAH 2A: Get Tracking Link (/marketing/product/link)
    tracking_link = ""
    
    link_path = "/marketing/product/link"
    link_url = f"{base_url}{link_path}"
    timestamp_link = str(int(time.time() * 1000))

    link_params = {
        "app_key": app_key,
        "timestamp": timestamp_link,
        "sign_method": "sha256",
        "userToken": user_token,
        "productId": str(product_id)
    }
    link_params["sign"] = sign_lazada_request(link_path, link_params, app_secret)

    print(f"\n2️⃣A [STEP 2A] Memanggil Tracking Link API ({link_url})...")
    try:
        res_link = requests.get(link_url, params=link_params, timeout=25)
        print(f"📊 [HTTP STATUS CODE]: {res_link.status_code}")
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
    except Exception as err2a:
        print(f"⚠️ Method 2A gagal: {err2a}")

    # LANGKAH 2B: Fallback ke Batch Get Link (/marketing/getlink)
    if not tracking_link:
        print("\n2️⃣B [STEP 2B] Mencuba Batch Get Link API (/marketing/getlink)...")
        getlink_path = "/marketing/getlink"
        getlink_url = f"{base_url}{getlink_path}"
        timestamp_gl = str(int(time.time() * 1000))

        getlink_params = {
            "app_key": app_key,
            "timestamp": timestamp_gl,
            "sign_method": "sha256",
            "userToken": user_token,
            "inputType": "productId",
            "inputValue": str(product_id)
        }
        getlink_params["sign"] = sign_lazada_request(getlink_path, getlink_params, app_secret)

        try:
            res_gl = requests.get(getlink_url, params=getlink_params, timeout=25)
            print(f"📊 [HTTP STATUS CODE]: {res_gl.status_code}")
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
        except Exception as err2b:
            print(f"⚠️ Method 2B gagal: {err2b}")

    # Semakan Akhir (NO DUMMY ALLOWED)
    if not tracking_link or not real_image:
        print("\n==================================================")
        print("🔴 [RALAT KRITIKAL]: Tracking Link atau Image URL adalah Kosong / NULL!")
        print("==================================================")
        print(f"Tracking Link : '{tracking_link}'")
        print(f"Real Image    : '{real_image}'")
        raise ValueError("Lazada API tidak memulangkan Link Affiliate atau Imej yang sah. Versi dummy dilarang keras.")

    print("\n==================================================")
    print("🟢 [LULUS 100%] PRODUK & LINK AFFILIATE SEBENAR DIPEROLEHI!")
    print("==================================================")
    print(f"📌 Product ID     : {product_id}")
    print(f"📌 Product Name   : {product_name}")
    print(f"🖼️ Real Image URL : {real_image}")
    print(f"🔗 Real Link Aff  : {tracking_link}")
    print("==================================================\n")

    return {
        "product_id": str(product_id),
        "title": product_name,
        "image": real_image,
        "link": tracking_link
    }

if __name__ == "__main__":
    try:
        test_fetch_real_lazada_affiliate()
    except Exception as e:
        print("\n💥 [UJIAN GAGAL] Skrip dihentikan akibat ralat di atas.")
        print("📜 Full Traceback:")
        traceback.print_exc()
        sys.exit(1)