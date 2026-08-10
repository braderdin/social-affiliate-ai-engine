import os
import json
import random
import re
import requests

# Senarai Kategori Diperluas (Persona Cikgu Suri Rumah Muslimah)
EXPANDED_CATEGORIES = [
    {"name": "barangan dapur", "desc": "periuk, air fryer, bekas, pisau, kuali, blender, rak dapur"},
    {"name": "barangan rumah", "desc": "rak kasut, penyangkut, pelekat, langsir, sarung, penyusun"},
    {"name": "barangan baby & ibu berpantang", "desc": "tungku, bengkung, mandian, bakul, botol, stokin"},
    {"name": "barangan kosmetik & penjagaan diri", "desc": "skincare, pelembap, pembersih, lotion, gincu, serum"},
    {"name": "mainan bayi dan mainan kanak2", "desc": "mainan, montessori, sensory, papan tulis, lego, puzzle"},
    {"name": "aksesori diy rumah", "desc": "pelekat, gam, lampu, pemutar, span, pita"},
    {"name": "peralatan sekolah & alat tulis anak-anak", "desc": "pencetak, pemadam, beg sekolah, pensel, pembaris"},
    {"name": "kelengkapan solat & ibadah keluarga", "desc": "sejadah, telekung, rehal, tasbih, kopiah, sejadah tebal"},
    {"name": "gajet & elektrik jimat tenaga", "desc": "vacuum, periuk nasi, penimbang, cerek, kipas mini"},
    {"name": "aksesori pembersihan & kebersihan rumah", "desc": "mop, berus, sabun, pengelap, tuala, berus gigi"},
    {"name": "pakaian muslimah & fesyen keluarga", "desc": "tudung, inner, stokin, baju kelawar, khimar"},
    {"name": "organizer & storan serbaguna", "desc": "kotak, bakul, bekas, beg storan, penyusun"}
]

def generate_search_keywords(base_url, model, api_key):
    """
    Memilih 1 kategori secara rawak dan menjana 5 kata kunci carian PENDEK (1-2 perkataan).
    """
    selected_cat = random.choice(EXPANDED_CATEGORIES)
    category_name = selected_cat["name"]
    category_desc = selected_cat["desc"]
    fallback_kws = [k.strip() for k in category_desc.split(",")][:5]

    if not base_url or not model or not api_key:
        print(f"🎯 [AI PERSONA] Kategori: '{category_name}' | Keywords Asas: {fallback_kws}")
        return category_name, fallback_kws

    system_prompt = """
Anda ialah 'Cikgu Suri Rumah'.
Tugas anda: Jana BETUL-BETUL 5 kata kunci carian produk di e-dagang Malaysia.

SYARAT KETAT:
1. Setiap kata kunci MESTI SANGAT PENDEK: 1 HINGGA 2 PERKATAAN SAHAJA (Contoh: "sejadah", "telekung", "mop", "periuk", "rak").
2. DILARANG guna ayat panjang.
3. WAJIB memulangkan hasil dalam format JSON ARRAY SAHAJA tanpa sebarang teks penjelasan:
["keyword1", "keyword2", "keyword3", "keyword4", "keyword5"]
"""

    prompt_user = f"Kategori: {category_name}\nContoh Idea: {category_desc}\nJana 5 kata kunci carian pendek (1-2 perkataan):"

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt.strip()},
            {"role": "user", "content": prompt_user.strip()}
        ],
        "temperature": 0.5,
        "max_tokens": 100
    }

    url = f"{base_url.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json; charset=utf-8"
    }

    try:
        res = requests.post(url, json=payload, headers=headers, timeout=25)
        if res.status_code == 200:
            raw_text = res.json()["choices"][0]["message"]["content"].strip()
            cleaned = re.sub(r"^```(?:json)?\s*", "", raw_text, flags=re.MULTILINE)
            cleaned = re.sub(r"\s*```$", "", cleaned, flags=re.MULTILINE).strip()

            keywords = json.loads(cleaned)
            if isinstance(keywords, list) and len(keywords) > 0:
                shortened_kws = [" ".join(str(kw).strip().split()[:2]) for kw in keywords]
                print(f"🎯 [AI PERSONA] Kategori: '{category_name}' | Keywords: {shortened_kws}")
                return category_name, shortened_kws
    except Exception as e:
        print(f"⚠️ [AI PERSONA WARN] Ralat OpenRouter AI: {e}")

    return category_name, fallback_kws