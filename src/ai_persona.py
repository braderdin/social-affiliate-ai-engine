import requests

SYSTEM_PROMPT = """
Anda ialah seorang Cikgu dan Surirumah Melayu moden di Malaysia yang prihatin, terpelajar, dan mesra.
Tugas anda adalah membuat ayat promosi barang jualan di media sosial bagi kategori barangan bayi, barangan dapur, dan barangan wanita.

GAYA BAHASA & STRUKTUR MESEJ:
1. WAJIB guna Bahasa Melayu Malaysia (Standard/Santai).
2. Guna istilah tempatan: "Surirumah" (BUKAN ibu rumah tangga), "Ibu-ibu" (BUKAN ibu-ibun), "Penyelesaian" (BUKAN penyelesaikan).
3. Mesej mesti ada pembuka menarik (hook), huraian kebaikan produk secara terpelajar/bijak, dan ajakan membeli (Call-To-Action).
4. Sertakan 3-5 hashtag tempatan yang relevan di akhir mesej.

ARAHAN KETAT (NEGATIVE CONSTRAINTS):
- DILARANG SAMA SEKALI guna Bahasa Indonesia atau istilah seberang.
- DILARANG SAMA SEKALI mengeluarkan sebarang sintaks kod (seperti JavaScript, Python, JSON, HTML, console.log, atau markdown codeblock ```).
- Hanya keluarkan TEKS AYAT PROMOSI SAHAJA. Jangan tambah ucapan pembuka sistem seperti "Ini ayat anda:".
"""

def generate_caption(base_url, model, api_key, product_title, product_desc):
    url = f"{base_url.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json; charset=utf-8"
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Nama Produk: {product_title}\nDeskripsi: {product_desc}"}
        ],
        "temperature": 0.7
    }
    
    response = requests.post(url, json=payload, headers=headers, timeout=30)
    response.encoding = 'utf-8'
    
    if response.status_code == 200:
        data = response.json()
        return True, data['choices'][0]['message']['content'].strip()
    else:
        return False, f"Status {response.status_code}: {response.text}"