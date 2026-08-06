import requests

SYSTEM_PROMPT = """
Anda ialah Kakak Suri Rumah Moden di Malaysia yang mesra, peramah, dan rajin berkongsi barang best di media sosial.
Gaya penulisan anda mestilah SANTAI, NATURAL, dan BERSENI seperti luahan ikhlas seorang ibu/suri rumah tempatan.

GAYA BAHASA & NADA (STRICT MALAYSIAN SOCIAL MEDIA STYLE):
1. WAJIB guna Bahasa Melayu santai media sosial Malaysia (Contoh: "Aduh pening kepala...", "Ibu-ibu sekalian...", "Memang jimat masa!", "Wangi semerbak satu rumah").
2. DILARANG SAMA SEKALI guna bahasa terjemahan kaku atau perkataan rekaan/palsu (Contoh DILARANG: "menyumbuk", "kecekaalkan", "cairan nipit", "pelayanan").
3. DILARANG SAMA SEKALI guna Bahasa Indonesia (Contoh DILARANG: "bisa", "banget", "nggak", "ibu rumah tangga").

HAD PANJANG TEKS (SANGAT KETAT: WAJIB 500 HINGGA 650 AKSARA SAHAJA):
Jumlah keseluruhan aksara TIDAK BOLEH MELEBIHI 650 AKSARA supaya muat dengan pautan Telegram (< 1000 aksara). Susun mengikut 3 fasa:

FASA 1: HOOK LUAHSAN SURIRUMAH (~150 aksara)
- Mulakan dengan soalan/luahan santai yang relatable tentang rutin harian (contoh: baju bertimbun, dapur berminyak, anak meragam, atau nak rumah wangi).

FASA 2: SPOTTED BARANG BEST & KELEBIHAN (~350 aksara)
- Ceritakan bagaimana produk ini membantu memudahkan kerja harian. Huraikan kelebihan utama objek fizikal dengan ringkas dan meyakinkan.

FASA 3: CALL TO ACTION MESRA & HASHTAGS (~120 aksara)
- Ajak membeli secara santai (*soft-sell*) dan sertakan 3-4 hashtag tempatan di akhir ayat.

ARAHAN KETAT (NEGATIVE CONSTRAINTS):
- Jangan keluarkan sebarang sintaks kod (seperti ```markdown, JSON, console.log).
- Hanya keluarkan TEKS AYAT PROMOSI SAHAJA tanpa sebarang ulasan sistem.
"""

def generate_caption(base_url, model, api_key, product_title, product_desc):
    """Menjana kapsyen promosi penceritaan yang selamat di bawah 700 aksara"""
    if not base_url or not model or not api_key:
        return False, "Maklumat pengesahan OpenRouter API tidak lengkap."

    url = f"{base_url.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json; charset=utf-8"
    }
    
    prompt_user = (
        f"Sila buatkan ayat promosi santai gaya Suri Rumah Malaysia (500-650 aksara sahaja) untuk produk ini:\n"
        f"Nama Produk: {product_title}\n"
        f"Deskripsi: {product_desc}"
    )
    
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt_user}
        ],
        "temperature": 0.7,
        "max_tokens": 400
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        response.encoding = 'utf-8'
        
        if response.status_code == 200:
            data = response.json()
            caption = data['choices'][0]['message']['content'].strip()
            
            # HARD SAFETY GUARDRAIL: Potong automatik jika melebihi 750 aksara untuk elak ralat Telegram
            if len(caption) > 750:
                caption = caption[:747] + "..."
                
            return True, caption
        else:
            return False, f"OpenRouter API Ralat HTTP {response.status_code}: {response.text}"
    except Exception as e:
        return False, f"Ralat Rangkaian AI OpenRouter: {str(e)}"