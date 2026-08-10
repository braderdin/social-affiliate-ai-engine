import time
import json
import requests
from src.lazada_api import sign_lazada

def search_lazada_candidates(app_key, app_secret, user_token, keywords, min_commission_rate=20.0):
    """
    Mencari produk di Lazada API mengikut kata kunci carian pendek
    dengan paparan MESEJ RALAT TERPERINCI (Full Diagnostic Logging).
    """
    domain = "api.lazada.com.my"
    feed_path = "/marketing/product/feed"
    feed_url = f"https://{domain}/rest{feed_path}"

    candidates = []
    seen_ids = set()

    print("\n==================================================")
    print("🔍 [DIAGNOSTIC SEARCH] Starting Keyword Search & Full Log Trace")
    print(f"🔑 App Key     : {app_key}")
    print(f"📋 Keywords    : {keywords}")
    print("==================================================")

    for kw in keywords:
        kw_clean = str(kw).strip().lower()
        if not kw_clean:
            continue

        print(f"\n📡 [SEARCHING KEYWORD]: '{kw_clean}'")

        # Buat panggilan untuk offerType 1, 2, dan 3
        for offer_type in ["1", "2", "3"]:
            timestamp = str(int(time.time() * 1000))
            
            # Hantar parameter carian keyword ke Lazada Feed API
            params = {
                "app_key": str(app_key).strip(),
                "timestamp": timestamp,
                "sign_method": "sha256",
                "offerType": offer_type,
                "userToken": str(user_token).strip(),
                "keyword": kw_clean,
                "page": "1",
                "limit": "50"
            }
            params["sign"] = sign_lazada(feed_path, params, app_secret)

            try:
                res = requests.get(feed_url, params=params, timeout=25)
                print(f"   📊 [offerType={offer_type}] HTTP Status Code: {res.status_code}")

                if res.status_code != 200:
                    print(f"   🔴 [RALAT HTTP]: {res.status_code} | Raw Text: {res.text[:300]}")
                    continue

                try:
                    feed_json = res.json()
                except Exception as err_json:
                    print(f"   🔴 [RALAT JSON DECODE]: {err_json} | Raw Text: {res.text[:300]}")
                    continue

                code = str(feed_json.get("code", "-1"))
                message = feed_json.get("message") or feed_json.get("msg") or "Tiada Mesej Ralat"

                if code != "0":
                    print(f"   ⚠️ [LAZADA API CODE {code}]: Mesej Ralat API -> {message}")
                    # Cetak perincian penuh JSON ralat jika ada ralat kebenaran/parameter
                    print(f"      📄 Raw Error Payload: {json.dumps(feed_json)}")
                    continue

                result_data = feed_json.get("result", {}) or feed_json.get("data", {})
                products = []
                if isinstance(result_data, dict):
                    products = result_data.get("products", []) or result_data.get("data", []) or result_data.get("items", [])
                elif isinstance(result_data, list):
                    products = result_data

                print(f"   📦 [MEMANGGIL FEED SUKSES]: Menerima {len(products)} produk dari pelayan Lazada.")

                matches_for_this_kw = 0
                for prod in products:
                    p_id = str(prod.get("productId") or prod.get("product_id") or prod.get("id") or "").strip()
                    p_name = prod.get("productName") or prod.get("title") or prod.get("name") or ""
                    pics = prod.get("pictures") or prod.get("image_url") or prod.get("image") or prod.get("picUrl")

                    # Semakan Kadar Komisen
                    raw_comm = prod.get("commissionRate") or prod.get("commCommissionRate") or prod.get("commission") or 0
                    try:
                        comm_rate = float(str(raw_comm).replace("%", ""))
                        if 0 < comm_rate < 1.0:
                            comm_rate *= 100
                    except (ValueError, TypeError):
                        comm_rate = 0.0

                    # Padanan Kata Kunci Pada Tajuk Produk
                    is_matched = any(w in p_name.lower() for w in kw_clean.split())

                    img_url = ""
                    if isinstance(pics, list) and len(pics) > 0:
                        img_url = pics[0]
                    elif isinstance(pics, str):
                        img_url = pics

                    if p_id and img_url and p_id not in seen_ids:
                        if is_matched:
                            seen_ids.add(p_id)
                            matches_for_this_kw += 1
                            candidates.append({
                                "id": p_id,
                                "title": p_name,
                                "image": img_url,
                                "discountPrice": prod.get("discountPrice"),
                                "price": prod.get("price") or prod.get("originalPrice"),
                                "outOfStock": prod.get("outOfStock"),
                                "commissionRate": comm_rate,
                                "matched_keyword": kw_clean,
                                "desc": f"Promosi pilihan Cikgu Suri Rumah ({kw_clean}): {p_name}"
                            })

                print(f"   ✅ Ditemui {matches_for_this_kw} produk yang tepat dengan kata kunci '{kw_clean}'.")

                # Jika sudah jumpa calon produk untuk kata kunci ini, teruskan ke kata kunci seterusnya
                if matches_for_this_kw > 0:
                    break

            except Exception as e:
                print(f"   💥 [EXCEPTIONAL ERROR] Ralat semasa membuat carian API: {e}")
                continue

    print(f"\n🎯 [RUMUSAN CARIAN]: Jumlah Keseluruhan Calon Produk Keyword = {len(candidates)}")
    return candidates