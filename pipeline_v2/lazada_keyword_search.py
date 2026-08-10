import json
import requests
import traceback

def search_lazada_direct_fetch(keyword):
    """
    Membuat 100% Direct Fetch Search ke Lazada Catalog AJAX JSON Endpoint.
    Memulangkan senarai produk serta mencetak log ralat terperinci jika gagal.
    """
    kw_clean = str(keyword).strip()
    search_url = f"https://www.lazada.com.my/catalog/?q={kw_clean}&ajax=true"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9,ms;q=0.8",
        "Referer": f"https://www.lazada.com.my/catalog/?q={kw_clean}",
        "X-Requested-With": "XMLHttpRequest"
    }

    print(f"\n📡 [DIRECT FETCH SEARCH] Requesting: {search_url}")
    
    try:
        res = requests.get(search_url, headers=headers, timeout=20)
        print(f"   📊 HTTP Status Code: {res.status_code}")

        if res.status_code != 200:
            print(f"   🔴 [RALAT HTTP {res.status_code}]: Respon dari pelayan Lazada disekat/ralat.")
            print(f"      📄 Response Headers: {dict(res.headers)}")
            print(f"      📄 Raw Body Snippet: {res.text[:400]}")
            return []

        try:
            data = res.json()
        except json.JSONDecodeError as json_err:
            print(f"   🔴 [RALAT JSON DECODE]: Respon bukan format JSON sah. {json_err}")
            print(f"      📄 Raw Body Snippet: {res.text[:400]}")
            return []

        # Ekstrak barang dari struktur JSON Lazada Catalog
        mods = data.get("mods", {}) or data.get("mainInfo", {}).get("mods", {})
        list_items = mods.get("listItems", [])

        if not list_items:
            # Semak struktur alternatif resultValue
            result_val = data.get("resultValue", {})
            if isinstance(result_val, dict):
                list_items = result_val.get("data", {}).get("unpackedItems", []) or result_val.get("content", [])

        print(f"   📦 [FETCH SUCCESS]: Jumpa {len(list_items)} produk untuk keyword '{kw_clean}'.")

        extracted_products = []
        for item in list_items:
            item_id = str(item.get("itemId") or item.get("id") or "").strip()
            title = item.get("name") or item.get("title") or ""
            img = item.get("image") or item.get("pic") or ""
            price = item.get("price") or item.get("priceShow") or 0.0

            if img and not img.startswith("http"):
                img = f"https:{img}" if img.startswith("//") else f"https://{img}"

            if item_id and title and img:
                extracted_products.append({
                    "id": item_id,
                    "title": title,
                    "image": img,
                    "price": price,
                    "discountPrice": price,
                    "outOfStock": False,
                    "matched_keyword": kw_clean,
                    "desc": f"Promosi pilihan Cikgu Suri Rumah: {title}"
                })

        return extracted_products

    except Exception as e:
        print(f"   💥 [EXCEPTIONAL ERROR] Gagal melakukan Direct Fetch Search untuk '{kw_clean}': {e}")
        print("   📜 Full Traceback:")
        traceback.print_exc()
        return []

def search_lazada_candidates_by_keywords(keywords):
    """
    Melakukan Direct Fetch Search untuk semua 5 kata kunci.
    """
    all_candidates = []
    seen_ids = set()

    print("\n==================================================")
    print("🔍 [100% DIRECT FETCH SEARCH] Initiating Keyword Search")
    print(f"📋 Keywords: {keywords}")
    print("==================================================")

    for kw in keywords:
        items = search_lazada_direct_fetch(kw)
        for prod in items:
            p_id = prod["id"]
            if p_id not in seen_ids:
                seen_ids.add(p_id)
                all_candidates.append(prod)

    print(f"\n🎯 [RUMUSAN DIRECT FETCH]: Keseluruhan Produk Carian Ditemui = {len(all_candidates)}")
    return all_candidates