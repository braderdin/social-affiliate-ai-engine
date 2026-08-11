import os
import json
import random
import re
import requests

EXPANDED_CATEGORIES = [
    "Barangan Dapur (air fryer, periuk seramik, bekas kedap udara, pemotong sayur)",
    "Barangan Rumah (rak kasut, penyangkut baju, wallpaper dapur, organizer laci)",
    "Barangan Baby & Ibu Berpantang (tungku moden, bengkung ibu, set mandian bayi, bakul baju baby)",
    "Barangan Kosmetik & Penjagaan Diri Halal (lip balm, pencuci muka halal, lotion pelembap, sunscreen)",
    "Mainan Bayi & Kanak-Kanak (sensory play, mainan montessori, papan tulis magnetik, lego budak)",
    "Aksesori DIY Rumah (lampu sensor, gam paip, pelekat dinding, pita kalis air)",
    "Peralatan Sekolah & Alat Tulis Anak-Anak (pencetak mini, set pemadam, beg sekolah, pensel warna)",
    "Kelengkapan Solat & Ibadah Keluarga (sejadah tebal, telekung travel, rehal kayu, rak al quran)",
    "Gajet & Elektrik Jimat Tenaga (vakum mini, periuk nasi mini, penimbang digital, kipas usb)",
    "Aksesori Pembersihan & Kebersihan Rumah (mop spray, berus periuk, pengelap cermin, sabun mop)"
]

def generate_5_keywords(category_name=None):
    """
    Menjana 5 kata kunci carian popular dan semula jadi menggunakan AI Persona Cikgu Suri Rumah.
    """
    base_url = os.getenv("OPENROUTER_BASE_URL", "").rstrip("/")
    model = os.getenv("OPENROUTER_MODEL", "")
    api_key = os.getenv("OPENROUTER_API_KEY", "")

    if not base_url or not model or not api_key:
        return False, [], "", "Kunci pengesahan OpenRouter API (.env.local) tidak lengkap."

    if not category_name:
        category_name = random.choice(EXPANDED_CATEGORIES)

    system_prompt = """Anda ialah AI Persona 'Cikgu Suri Rumah'.
Tugas anda: Hasilkan TEPAT 5 kata kunci (keyword) carian e-dagang yang PALING POPULAR & BANYAK DICARI di Lazada Malaysia.

PERATURAN KETAT:
1. Guna perkataan carian standard e-dagang Malaysia (2 hingga 3 perkataan penuh sahaja). Contoh: "mop spray", "sejadah tebal", "air fryer mini", "tungku moden".
2. DILARANG memotong perkataan hingga janggal (Contoh DILARANG: "pelekat dapur kalis", "gam paip kuat").
3. WAJIB pulangkan jawapan dalam format JSON ARRAY SAHAJA TANPA SEBARANG TEKS LAIN ATAU CODEBLOCK.

Contoh format output wajib:
["keyword 1", "keyword 2", "keyword 3", "keyword 4", "keyword 5"]
"""

    user_prompt = f"Jana 5 keyword carian popular Lazada untuk kategori: {category_name}"

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 150
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json; charset=utf-8"
    }

    try:
        endpoint = f"{base_url}/chat/completions"
        response = requests.post(endpoint, json=payload, headers=headers, timeout=25)
        
        if response.status_code == 200:
            res_data = response.json()
            if "choices" in res_data and len(res_data["choices"]) > 0:
                content = res_data["choices"][0]["message"]["content"].strip()
                cleaned = re.sub(r"^```(?:json)?\s*", "", content, flags=re.MULTILINE)
                cleaned = re.sub(r"\s*```$", "", cleaned, flags=re.MULTILINE).strip()
                
                keywords = json.loads(cleaned)
                if isinstance(keywords, list) and len(keywords) > 0:
                    keywords = [str(k).strip() for k in keywords[:5] if str(k).strip()]
                    return True, keywords, category_name, f"Berjaya menjana 5 keyword untuk '{category_name}'."
            
            return False, [], category_name, "Format JSON AI OpenRouter tidak sah."
        else:
            return False, [], category_name, f"Ralat HTTP OpenRouter ({response.status_code}): {response.text}"
            
    except Exception as e:
        return False, [], category_name, f"Ralat sambungan AI OpenRouter API: {str(e)}"