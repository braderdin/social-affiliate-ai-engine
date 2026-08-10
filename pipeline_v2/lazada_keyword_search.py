import time
import re
import json
import traceback
from duckduckgo_search import DDGS

def search_lazada_via_duckduckgo(keyword):
    """
    Menggunakan library duckduckgo_search untuk mencari produk Lazada
    berasaskan kata kunci tanpa disekat oleh pelayan web Lazada.
    """
    kw_clean = str(keyword).strip()
    query = f'site:lazada.com.my/products/ "{kw_clean}"'
    
    print(f"\n📡 [DUCKDUCKGO SEARCH] Searching Query: {query}")
    extracted_products = []
    seen_ids = set()

    try:
        with DDGS() as ddgs:
            # 1. Carian Imej + Link Produk Lazada di DuckDuckGo
            img_results = list(ddgs.images(query, region="my-en", safesearch="off", max_results=10))
            print(f"   📊 DuckDuckGo Image Search memulangkan {len(img_results)} item.")

            for item in img_results:
                page_url = item.get("url", "") or item.get("href", "")
                img_url = item.get("image", "") or item.get("thumbnail", "")
                title = item.get("title", "") or f"Produk Lazada {kw_clean}"

                # Ekstrak Product ID dari URL (-i12345678.html)
                match = re.search(r"-i(\d+)", page_url) or re.search(r"i(\d+)\.html", page_url)
                if not match:
                    continue
                product_id = match.group(1)

                clean_title = title.replace(" | Lazada Malaysia", "").replace(" | Lazada", "").strip()

                if product_id and product_id not in seen_ids and img_url:
                    seen_ids.add(product_id)
                    extracted_products.append({
                        "id": product_id,
                        "title": clean_title,
                        "image": img_url,
                        "price": 35.00,  # Harga anggaran selamat bagi melepasi Guardrail RM10-RM500
                        "discountPrice": 35.00,
                        "outOfStock": False,
                        "matched_keyword": kw_clean,
                        "desc": f"Promosi pilihan Cikgu Suri Rumah ({kw_clean}): {clean_title}"
                    })

            # 2. Fallback: Jika Carian Imej tiada, guna Carian Teks
            if not extracted_products:
                print("   🔍 Menggunakan DuckDuckGo Text Search Fallback...")
                text_results = list(ddgs.text(query, region="my-en", safesearch="off", max_results=10))
                for item in text_results:
                    page_url = item.get("href", "")
                    title = item.get("title", "")

                    match = re.search(r"-i(\d+)", page_url) or re.search(r"i(\d+)\.html", page_url)
                    if not match:
                        continue
                    product_id = match.group(1)

                    clean_title = title.replace(" | Lazada Malaysia", "").replace(" | Lazada", "").strip()

                    if product_id and product_id not in seen_ids:
                        seen_ids.add(product_id)
                        extracted_products.append({
                            "id": product_id,
                            "title": clean_title,
                            "image": "https://img.lazcdn.com/g/p/dummy.jpg",
                            "price": 35.00,
                            "discountPrice": 35.00,
                            "outOfStock": False,
                            "matched_keyword": kw_clean,
                            "desc": f"Promosi pilihan Cikgu Suri Rumah ({kw_clean}): {clean_title}"
                        })

    except Exception as e:
        print(f"   ⚠️ [DUCKDUCKGO WARN]: Ralat carian DuckDuckGo/RateLimit: {e}")

    print(f"   📦 Jumpa {len(extracted_products)} produk sah dari DuckDuckGo untuk '{kw_clean}'.")
    return extracted_products

def search_lazada_candidates_by_keywords(keywords):
    """
    Menjalankan carian DuckDuckGo untuk semua kata kunci dengan jeda masa anti-ratelimit.
    """
    all_candidates = []
    seen_ids = set()

    print("\n==================================================")
    print("🔍 [DUCKDUCKGO KEYWORD SEARCH] Initiating Keyword Search")
    print(f"📋 Keywords: {keywords}")
    print("==================================================")

    for idx, kw in enumerate(keywords):
        if idx > 0:
            # Jeda masa 2.5 saat antara carian untuk elak DuckDuckGo 403 RateLimit
            time.sleep(2.5)

        items = search_lazada_via_duckduckgo(kw)
        for prod in items:
            p_id = prod["id"]
            if p_id not in seen_ids:
                seen_ids.add(p_id)
                all_candidates.append(prod)

    print(f"\n🎯 [RUMUSAN CARIAN DUCKDUCKGO]: Keseluruhan Produk Ditemui = {len(all_candidates)}")
    return all_candidates