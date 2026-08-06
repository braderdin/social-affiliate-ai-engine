# Kategori Sasaran Rasmi Kekeluargaan & Surirumah
TARGET_CATEGORIES = [
    "10100539",  # Keperluan Rumah & Pembersihan Dapur
    "1438",      # Penjagaan Kulit & Kecantikan Wanita
    "3752",      # Makanan, Minuman & Barangan Bayi / Kanak-kanak
    "10000343",  # Barangan Dapur & Bekas Makanan
    "275"        # Perkakas Elektrik Rumah (Kipas, Aircond, Air Fryer, dll.)
]

# Senarai Hitam Strict (Non-Halal, Alkohol & Jenama Arak, Promo Fake/GWP, Barangan Mewah/Bukan Persona)
BLACKLIST_KEYWORDS = [
    # Non-Halal / Alkohol / Babi / Jenama Arak Utama
    "whisky", "whiskey", "liquor", "wine", "vodka", "alcohol", "beer", "rum",
    "pork", "lard", "bacon", "ham", "non-halal", "non halal", "tokek", "arak",
    "martell", "cognac", "brandy", "xo", "hennessy", "chivas", "johnnie", "walker",
    "smirnoff", "heineken", "tiger", "carlsberg", "guinness", "somersby", "asahi",
    "budweiser", "jack daniels", "bacardi", "absolut", "gin", "tequila",
    # Promo Palsu / GWP / Gift
    "gwp", "not for sale", "gift not for sale", "free gift", "sample",
    "blind box", "tester", "prize", "lazland only", "cgwp", "voucher", "e-voucher",
    # Barangan Mewah / Industri / Bukan Persona Surirumah
    "coin", "silver", "gold", "pendant", "caravan", "campervan",
    "machine", "testing", "sneakers", "jade", "watch", "quartz", "automatic",
    "diamond", "luxury", "machinery"
]

def normalize_image_url(url):
    """Memastikan URL imej mempunyai skema https: yang sah untuk Telegram API."""
    if not url:
        return ""
    url = str(url).strip()
    if url.startswith("//"):
        return f"https:{url}"
    elif not url.startswith("http"):
        return f"https://{url}"
    return url

def is_title_blacklisted(title):
    """Menyemak sama ada tajuk produk mengandungi sebarang kata kunci disekat."""
    lower_title = str(title or "").lower()
    for kw in BLACKLIST_KEYWORDS:
        if kw in lower_title:
            return True, kw
    return False, ""

def evaluate_product(prod):
    """
    Menilai kelayakan produk mengikut:
    1. Status outOfStock
    2. Semakan Kata Kunci Disekat (Non-Halal, GWP, dll.)
    3. Julat Harga Idaman RM 10.00 - RM 1000.00
    """
    if prod.get("outOfStock") is True or str(prod.get("outOfStock")).lower() == "true":
        return False, 0.0, "Habis Stok (outOfStock)"

    # 1. Semak kata kunci disekat
    is_blacklisted, kw = is_title_blacklisted(prod.get("title"))
    if is_blacklisted:
        return False, 0.0, f"Ditolak Kata Kunci Disekat ('{kw}')"

    # 2. Semak Harga Mentah (Ringgit Malaysia)
    raw_p = prod.get("discountPrice") if prod.get("discountPrice") is not None else prod.get("price")
    price_val = 0.0
    try:
        price_val = float(raw_p or 0.0)
    except (ValueError, TypeError):
        return False, 0.0, "Format Harga Tidak Sah"

    # Tapis harga dummy penjual (> RM 10,000)
    if price_val >= 10000.0:
        return False, price_val, "Harga Dummy/Out of Stock (> RM 10,000)"

    # Julat Standard RM 10.00 - RM 1000.00
    if 10.0 <= price_val <= 1000.0:
        return True, price_val, "Harga Lulus"

    return False, price_val, "Luar Julat RM10-RM1000"