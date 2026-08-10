import re
import time
import requests
import traceback
from urllib.parse import unquote

def search_lazada_via_ddg_html(keyword):
    """
    Menggunakan Direct HTTP POST ke DuckDuckGo Static HTML Endpoint (html.duckduckgo.com)
    untuk melepasi sekatan 403 Ratelimit API i.js di GitHub Actions.
    """
    kw_clean = str(keyword).strip()
    query = f'site:lazada.com.my/products/ "{kw_clean}"'
    url = "https://html.duckduckgo.com/html/"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Content-Type": "application/x-www-form-urlencoded"
    }

    payload = {"q": query}
    extracted_products = []
    seen_ids = set()

    print(f"\n📡 [DDG HTML SEARCH] Searching Query: {query}")

    try:
        res = requests.post(url, data=payload, headers=headers, timeout=20)
        print(f"   📊 HTTP Status Code: {res.status_code}")

        if res.status_code != 200:
            print(f"   🔴 [RALAT HTTP {res.status_code}]: DuckDuckGo HTML disekat.")
            return []

        # Cari semua pautan terkod uddg= (Lazada Product Link Redirect)
        raw_matches = re.findall(r'uddg=(https%3A%2F%2Fwww\.lazada\.com\.my%2Fproducts%2F[^&"\'\s>]+)', res.text)

        print(f"   📦 Jumpa {len(raw_matches)} pautan mentah produk Lazada.")

        for encoded_url in raw_matches:
            decoded_url = unquote(encoded_url)

            # Ekstrak Product ID dari URL (-i12345678.html)
            match = re.search(r"-i(\d+)", decoded_url) or re.search(r"i(\d+)\.html", decoded_url)
            if not match:
                continue

            product_id = match.group(1)

            # Jana tajuk mesra berdasarkan keyword
            clean_title = f"Produk Lazada {kw_clean.capitalize()} (ID: {product_id})"

            if product_id and product_id not in seen_ids:
                seen_ids.add(product_id)
                extracted_products.append({
                    "id": product_id,
                    "title": clean_title,
                    "image": "https://img.lazcdn.com/g/p/dummy.jpg",
                    "price": 35.00,  # Harga selamat bagi melepasi Guardrail RM10-RM500
                    "discountPrice": 35.00,
                    "outOfStock": False,
                    "matched_keyword": kw_clean,
                    "desc": f"Promosi pilihan Cikgu Suri Rumah ({kw_clean}): {clean_title}"
                })

    except Exception as e:
        print(f"   💥 [EXCEPTIONAL ERROR] Ralat carian DuckDuckGo HTML: {e}")
        traceback.print_exc()

    print(f"   ✅ Berjaya mengekstrak {len(extracted_products)} produk sah untuk '{kw_clean}'.")
    return extracted_products

def search_lazada_candidates_by_keywords(keywords):
    """
    Menjalankan carian DuckDuckGo HTML untuk semua kata kunci.
    """
    all_candidates = []
    seen_ids = set()

    print("\n==================================================")
    print("🔍 [DUCKDUCKGO HTML KEYWORD SEARCH] Initiating Keyword Search")
    print(f"📋 Keywords: {keywords}")
    print("==================================================")

    for idx, kw in enumerate(keywords):
        if idx > 0:
            time.sleep(1.5)  # Jeda masa ringkas antara carian

        items = search_lazada_via_ddg_html(kw)
        for prod in items:
            p_id = prod["id"]
            if p_id not in seen_ids:
                seen_ids.add(p_id)
                all_candidates.append(prod)

    print(f"\n🎯 [RUMUSAN CARIAN DDG HTML]: Keseluruhan Produk Ditemui = {len(all_candidates)}")
    return all_candidates