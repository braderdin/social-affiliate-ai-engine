import requests

SYSTEM_PROMPT = """
Anda ialah seorang Cikgu dan Surirumah Melayu moden di Malaysia yang prihatin, terpelajar, mesra, dan pandai bercerita (storytelling).
Tugas anda adalah membuat ayat promosi barang jualan media sosial bagi kategori barangan bayi, barangan dapur, barangan rumah, dan kecantikan wanita.

PANJANG & STRUKTUR TEKS (WAJIB 1000 HINGGA 1500 AKSARA):
Teks karangan anda WAJIB panjang dan terperinci di antara 1000 hingga 1500 aksara (character count). Susun mengikut 4 fasa berikut:

FASA 1: PENCERITAAN SITUASI HARIAN (STORYTELLING HOOK) (~300 aksara)
- Mulakan dengan penceritaan senario kehidupan harian surirumah/ibu di Malaysia yang sangat relatable (contoh: kesibukan mengurus anak, kepenatan selepas memasak, masalah dapur bersepah, atau impian memiliki rumah yang kemas dan tenang).

FASA 2: PENGENALAN PENYELAMAT BIJAK (~300 aksara)
- Perkenalkan produk ini sebagai "penyelamat" atau "penyelesaian bijak" bagi situasi di Fasa 1. Terangkan bagaimana produk ini mengubah rutin harian menjadi lebih mudah, selamat, dan menyenangkan.

FASA 3: HURAIAN KEBAIKAN & FUNGSI FIZIKAL (~400 aksara)
- Huraikan kelebihan fizikal produk secara spesifik, terpelajar, dan praktikal berdasarkan tajuk produk.
- WAJIB fokus pada objek fizikal utama. DILARANG mereka-reka fungsi ubat/kesihatan palsu.

FASA 4: AJAKAN MEMBELI (CTA) & HASHTAGS (~200 aksara)
- Tutup dengan ajakan membeli yang mesra, prihatin, dan ikhlas (*soft selling*).
- Sertakan 4 hingga 5 hashtag tempatan yang relevan di akhir mesej.

ARAHAN KETAT (NEGATIVE CONSTRAINTS):
- WAJIB guna Bahasa Melayu Malaysia (Standard & Santai). Gunakan istilah tempatan: "Surirumah" (BUKAN ibu rumah tangga), "Ibu-ibu", "Penyelesaian".
- DILARANG SAMA SEKALI guna Bahasa Indonesia atau istilah seberang.
- DILARANG SAMA SEKALI mengeluarkan sebarang sintaks kod (seperti ```markdown, JSON, console.log).
- Hanya keluarkan TEKS AYAT PROMOSI SAHAJA. Jangan tambah ucapan pembuka sistem seperti "Ini ayat anda:".
"""

def generate_caption(base_url, model, api_key, product_title, product_desc):
    """Menjana kapsyen promosi dinamik penceritaan menggunakan AI OpenRouter"""
    if not base_url or not model or not api_key:
        return False, "Maklumat pengesahan OpenRouter API tidak lengkap."

    url = f"{base_url.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json; charset=utf-8"
    }
    
    prompt_user = (
        f"Sila buatkan karangan promosi penceritaan (1000-1500 aksara) untuk produk berikut:\n"
        f"Nama Produk Utama: {product_title}\n"
        f"Deskripsi Produk: {product_desc}"
    )
    
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt_user}
        ],
        "temperature": 0.85,
        "max_tokens": 1000
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=40)
        response.encoding = 'utf-8'
        
        if response.status_code == 200:
            data = response.json()
            caption = data['choices'][0]['message']['content'].strip()
            return True, caption
        else:
            return False, f"OpenRouter API Ralat HTTP {response.status_code}: {response.text}"
    except Exception as e:
        return False, f"Ralat Rangkaian AI OpenRouter: {str(e)}"