import time
import requests
from src.lazada_api import sign_lazada

def search_lazada_candidates(app_key, app_secret, user_token, keywords, min_commission_rate=20.0):
    """
    Mencari produk di Lazada Feed/Search mengikut senarai kata kunci
    dan menapis produk yang mempunyai sekurang-kurangnya 20% kadar komisen.
    """
    domain = "api.lazada.com.my"
    feed_path = "/marketing/product/feed"
    feed_url = f"https://{domain}/rest{feed_path}"

    candidates = []
    seen_ids = set()

    for kw in keywords:
        timestamp = str(int(time.time() * 1000))
        params = {
            "app_key": str(app_key).strip(),
            "timestamp": timestamp,
            "sign_method": "sha256",
            "offerType": "1",
            "userToken": str(user_token).strip(),
            "page": "1",
            "limit": "50"
        }
        params["sign"] = sign_lazada(feed_path, params, app_secret)

        try:
            res = requests.get(feed_url, params=params, timeout=25)
            if res.status_code != 200:
                continue

            feed_json = res.json()
            if str(feed_json.get("code", "0")) != "0":
                continue

            result_data = feed_json.get("result", {}) or feed_json.get("data", {})
            products = []
            if isinstance(result_data, dict):
                products = result_data.get("products", []) or result_data.get("data", []) or result_data.get("items", [])
            elif isinstance(result_data, list):
                products = result_data

            for prod in products:
                p_id = str(prod.get("productId") or prod.get("product_id") or prod.get("id") or "").strip()
                p_name = prod.get("productName") or prod.get("title") or prod.get("name") or ""
                pics = prod.get("pictures") or prod.get("image_url") or prod.get("image") or prod.get("picUrl")

                # Semakan Kadar Komisen Minima 20%
                raw_comm = prod.get("commissionRate") or prod.get("commCommissionRate") or prod.get("commission") or 0
                try:
                    comm_rate = float(str(raw_comm).replace("%", ""))
                    if comm_rate < 1.0 and comm_rate > 0:  # Contoh 0.25 = 25%
                        comm_rate *= 100
                except (ValueError, TypeError):
                    comm_rate = 0.0

                # Padanan Kata Kunci Santai
                kw_match = any(w.lower() in p_name.lower() for w in kw.split())

                img_url = ""
                if isinstance(pics, list) and len(pics) > 0:
                    img_url = pics[0]
                elif isinstance(pics, str):
                    img_url = pics

                if p_id and img_url and p_id not in seen_ids:
                    # Jika komisen >= 20%
                    if comm_rate >= min_commission_rate or kw_match:
                        seen_ids.add(p_id)
                        candidates.append({
                            "id": p_id,
                            "title": p_name,
                            "image": img_url,
                            "discountPrice": prod.get("discountPrice"),
                            "price": prod.get("price") or prod.get("originalPrice"),
                            "outOfStock": prod.get("outOfStock"),
                            "commissionRate": comm_rate,
                            "desc": f"Promosi pilihan Cikgu Suri Rumah: {p_name}"
                        })
        except Exception as e:
            print(f"⚠️ [SEARCH WARN] Ralat carian keyword '{kw}': {e}")
            continue

    print(f"📦 Jumpa {len(candidates)} calon produk berpotensi dari carian keyword.")
    return candidates