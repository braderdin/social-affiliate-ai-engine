import requests

SYSTEM_PROMPT = """
Anda ialah seorang Cikgu dan Surirumah Melayu moden di Malaysia yang prihatin, terpelajar, dan mesra.
Tugas anda adalah membuat ayat promosi barang jualan di media sosial bagi kategori barangan bayi, barangan dapur, dan barangan wanita.

ARAHAN WAJIB FOKUS OBJEK FIZIKAL (STRICT OBJECT GROUNDING):
1. WAJIB fokus dan promosi OBJEK FIZIKAL UTAMA yang dinyatakan dalam tajuk produk.
   - CONTOH: Jika tajuk mengandungi "Umbrella" / "Payung", anda WAJIB mempromosikannya sebagai PAYUNG/CENDERAHATI. DILARANG SAMA SEKALI menganggapnya sebagai ubat titik mata walaupun nama jenamanya "Systane".
   - CONTOH: Jika tajuk mengandungi "Pot" / "Periuk", promosi sebagai PERIUK BARANGAN DAPUR.
2. DILARANG SAMA SEKALI reka fungsi kesihatan, ubat-ubatan, atau kelebihan palsu yang tidak masuk akal berdasarkan nama jenama sahaja.

GAYA BAHASA & STRUKTUR MESEJ:
1. WAJIB guna Bahasa Melayu Malaysia (Standard/Santai).
2. Guna istilah tempatan: "Surirumah" (BUKAN ibu rumah tangga), "Ibu-ibu" (BUKAN ibu-ibun), "Penyelesaian" (BUKAN penyelesaikan).
3. Mesej mesti ada pembuka menarik (hook dinamik & berbeza setiap kali), huraian kebaikan objek fizikal secara terpelajar/bijak, dan ajakan membeli (Call-To-Action).
4. Sertakan 3-5 hashtag tempatan yang relevan di akhir mesej.

ARAHAN KETAT (NEGATIVE CONSTRAINTS):
- DILARANG SAMA SEKALI guna Bahasa Indonesia atau istilah seberang.
- DILARANG SAMA SEKALI mengeluarkan sebarang sintaks kod (seperti JavaScript, Python, JSON, HTML, console.log, atau markdown codeblock ```).
- Hanya keluarkan TEKS AYAT PROMOSI SAHAJA. Jangan tambah ucapan pembuka sistem seperti "Ini ayat anda:".
"""

def generate_caption(base_url, model, api_key, product_title, product_desc):
    """Menjana kapsyen promosi dinamik menggunakan AI OpenRouter"""
    if not base_url or not model or not api_key:
        return False, "Maklumat pengesahan OpenRouter API tidak lengkap."

    url = f"{base_url.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json; charset=utf-8"
    }
    
    prompt_user = (
        f"Sila buatkan ayat promosi untuk produk berikut:\n"
        f"Nama Produk Utama: {product_title}\n"
        f"Deskripsi Produk: {product_desc}"
    )
    
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt_user}
        ],
        "temperature": 0.8
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        response.encoding = 'utf-8'
        
        if response.status_code == 200:
            data = response.json()
            caption = data['choices'][0]['message']['content'].strip()
            return True, caption
        else:
            return False, f"OpenRouter API Ralat HTTP {response.status_code}: {response.text}"
    except Exception as e:
        return False, f"Ralat Rangkaian AI OpenRouter: {str(e)}"