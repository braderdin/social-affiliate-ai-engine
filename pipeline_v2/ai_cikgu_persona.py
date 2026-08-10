import os
import json
import random
import re
import requests

# Senarai Kategori Diperluas (Persona Cikgu Suri Rumah Muslimah)
EXPANDED_CATEGORIES = [
    {"name": "barangan dapur", "desc": "Periuk seramik, air fryer mini, bekas simpanan kedap udara, gajet pemotong sayur"},
    {"name": "barangan rumah", "desc": "Penyusun ruang laci, rak kasut bertingkat, penyangkut baju jimat ruang, pelekat dinding"},
    {"name": "barangan baby & ibu berpantang", "desc": "Kelengkapan bayi, mandian lembut, tungku moden, bengkung, bakul baju bayi"},
    {"name": "barangan kosmetik & penjagaan diri", "desc": "Skincare mesra wuduk, pelembap bibir, pembersih muka halal, lotion"},
    {"name": "mainan bayi dan mainan kanak2", "desc": "Mainan edutainment, Montessori, sensory play kit, papan tulis magnetik"},
    {"name": "aksesori diy rumah", "desc": "Pelekat kalis air dapur, gam tampal paip, gajet lampu sensor, alat pembaikan mudah"},
    {"name": "peralatan sekolah & alat tulis anak-anak", "desc": "Pencetak mini sticker, set pemadam comel, beg sekolah ergonomik"},
    {"name": "kelengkapan solat & ibadah keluarga", "desc": "Sejadah tebal empuk, telekung travel ringkas, rak al-Quran kayu, rehal"},
    {"name": "gajet & elektrik jimat tenaga", "desc": "Pembersih vakum mini, periuk nasi elektrik kecil, penimbang makanan digital"},
    {"name": "aksesori pembersihan & kebersihan rumah", "desc": "Pengelap cermin magnetik, sabun wangi mop, berus periuk automatik"},
    {"name": "pakaian muslimah & fesyen keluarga", "desc": "Tudung sarung ironless, inner sejuk, stokin wuduk, baju kelawar selesa"},
    {"name": "organizer & storan serbaguna", "desc": "Kotak simpanan lutsinar, penyusun rempah ratus, bakul pakaian lipat"}
]

def generate_search_keywords(base_url, model, api_key):
    """
    Memilih 1 kategori secara rawak dan menggunakan AI Persona 'Cikgu Suri Rumah' 
    untuk menjana 5 kata kunci carian spesifik di Lazada.
    """
    if not base_url or not model or not api_key:
        print("⚠️ [AI PERSONA WARN] Kunci OpenRouter / Model tidak lengkap. Menggunakan kata kunci asas...")
        selected_cat = random.choice(EXPANDED_CATEGORIES)
        return selected_cat["name"], ["periuk seramik", "bekas kedap udara", "air fryer mini", "rak dapur", "mop automatik"]

    selected_cat = random.choice(EXPANDED_CATEGORIES)
    category_name = selected_cat["name"]
    category_desc = selected_cat["desc"]

    system_prompt = """
Anda ialah 'Cikgu Suri Rumah', seorang pakar dalam mencari barangan praktikal, jimat, dan berkualiti untuk keluarga Muslimah di Malaysia.
Tugas anda adalah menghasilkan 5 kata kunci carian (keywords) produk yang sangat spesifik dan popular di Lazada Malaysia.

SYARAT KATA KUNCI:
1. Menjana betul-betul 5 kata kunci carian dalam Bahasa Melayu atau Bahasa Inggeris biasa yang biasa ditaip di carian e-dagang.
2. Kata kunci mesti fokus kepada produk fizikal spesifik (Contoh: "air fryer mini", "telekung travel", "pencetak mini sticker").
3. WAJIB memulangkan hasil dalam format JSON ARRAY SAHAJA tanpa sebarang teks tambahan:
["keyword1", "keyword2", "keyword3", "keyword4", "keyword5"]
"""

    prompt_user = f"Kategori Terpilih: {category_name}\nContoh Idea: {category_desc}\nJana 5 kata kunci carian produk Lazada:"

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt.strip()},
            {"role": "user", "content": prompt_user.strip()}
        ],
        "temperature": 0.7,
        "max_tokens": 150
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
                print(f"🎯 [AI PERSONA] Kategori: '{category_name}' | Keywords: {keywords}")
                return category_name, keywords
    except Exception as e:
        print(f"⚠️ [AI PERSONA WARN] Gagal menjana keyword via AI: {e}")

    # Fallback jika AI gagal
    fallback_keywords = [k.strip() for k in category_desc.split(",")]
    return category_name, fallback_keywords[:5]