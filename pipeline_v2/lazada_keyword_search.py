import time
import requests
from src.lazada_api import sign_lazada

def search_lazada_candidates(app_key, app_secret, user_token, category_l1_ids, keywords, min_commission_rate=20.0):
    """
    Menarik feed produk daripada Kategori Lazada (categoryL1) yang tepat (offerType=1 sahaja)
    dan menapis produk mengikut kata kunci serta kadar komisen minimum.
    """
    domain = "api.lazada.com.my"
    feed_path = "/marketing/product/feed"
    feed_url = f"https://{domain}/rest{feed_path}"

    candidates = []
    seen_ids = set()

    print("\n==================================================")
    print("🔍 [CATEGORY & KEYWORD SEARCH] Fetching Targeted Category Feed")
    print(f"🔑 App Key        : {app_key}")
    print(f"🏷️ Category L1 IDs: {category_l1_ids}")
    print(f"📋 Target Keywords: {keywords}")
    print("==================================================")

    # Hanya guna offerType=1 (Feed Umum Rasmi)
    for cat_id in category_l1_ids:
        for page in ["1", "2", "3"]:
            timestamp = str(int(time.time() * 1000))
            params = {
                "app_key": str(app_key).strip(),
                "timestamp": timestamp,
                "sign_method": "sha256",
                "offerType": "1",  # Strictly offerType=1
                "userToken": str(user_token).strip(),
                "categoryL1": str(cat_id).strip(),
                "page": page,
                "limit": "50"
            }
            params["sign"] = sign_lazada(feed_path, params, app_secret)

            try:
                res = requests.get(feed_url, params=params, timeout=25)
                print(f"📡 [Category L1={cat_id} | Page={page}] HTTP Status: {res.status_code}")

                if res.status_code != 200:
                    continue

                feed_json = res.json()
                if str(feed_json.get("code", "0")) != "0":
                    print(f"⚠️ [API WARN]: {feed_json.get('message')}")
                    continue

                result_data = feed_json.get("result", {}) or feed_json.get("data", {})
                products = []
                if isinstance(result_data, dict):
                    products = result_data.get("products", []) or result_data.get("data", []) or result_data.get("items", [])
                elif isinstance(result_data, list):
                    products = result_data

                print(f"   📦 Menerima {len(products)} produk daripada Category L1 ({cat_id}).")

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

                    # Semakan Padanan Kata Kunci pada Tajuk Produk
                    p_name_lower = p_name.lower()
                    matched_kw = ""
                    for kw in keywords:
                        kw_clean = str(kw).strip().lower()
                        if kw_clean and kw_clean in p_name_lower:
                            matched_kw = kw_clean
                            break

                    img_url = ""
                    if isinstance(pics, list) and len(pics) > 0:
                        img_url = pics[0]
                    elif isinstance(pics, str):
                        img_url = pics

                    if p_id and img_url and p_id not in seen_ids:
                        # Jika ada kata kunci padan ATAU produk dari kategori sasaran ini melepasi komisen
                        seen_ids.add(p_id)
                        candidates.append({
                            "id": p_id,
                            "title": p_name,
                            "image": img_url,
                            "discountPrice": prod.get("discountPrice"),
                            "price": prod.get("price") or prod.get("originalPrice"),
                            "outOfStock": prod.get("outOfStock"),
                            "commissionRate": comm_rate,
                            "matched_keyword": matched_kw or "kategori_sasaran",
                            "desc": f"Promosi pilihan Cikgu Suri Rumah: {p_name}"
                        })

            except Exception as e:
                print(f"⚠️ Ralat carian Category L1={cat_id}: {e}")
                continue

    # Susun calon produk: Keutamaan kepada produk yang padan dengan kata kunci spesifik
    candidates.sort(key=lambda x: (1 if x["matched_keyword"] != "kategori_sasaran" else 0, x["commissionRate"]), reverse=True)

    print(f"\n🎯 [RUMUSAN CARIAN]: Jumlah Keseluruhan Calon Produk = {len(candidates)}")
    return candidates