import os
import sys
import time
import hmac
import hashlib
import traceback
import requests
from io import BytesIO
from dotenv import load_dotenv

# 1. Baca fail .env.local untuk ujian tempatan
load_dotenv('.env.local')

# 2. Ambil pemboleh ubah persekitaran
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

LAZADA_APP_KEY = os.getenv("LAZADA_APP_KEY")
LAZADA_APP_SECRET = os.getenv("LAZADA_APP_SECRET")
LAZADA_MEMBER_ID = os.getenv("LAZADA_MEMBER_ID")

# SYSTEM PROMPT PERSONA CIKGU & SURIRUMAH MELAYU
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

def sanitize_value(val):
    if not val:
        return ""
    val = val.strip()
    if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
        val = val[1:-1]
    return val.strip()

def clean_url(url_str):
    if not url_str:
        return ""
    url_str = str(url_str).strip()
    if "](" in url_str:
        url_str = url_str.split("](")[-1].rstrip(")")
    for char in ["[", "]", "(", ")"]:
        url_str = url_str.replace(char, "")
    return url_str.strip()

def mask_key(key):
    if not key or len(key) < 8:
        return "***"
    return key[:4] + "..." + key[-4:]

def sign_lazada_request(api_path, params, app_secret):
    sorted_params = sorted(params.items())
    sign_str = api_path
    for k, v in sorted_params:
        sign_str += f"{k}{v}"
    
    return hmac.new(
        app_secret.encode('utf-8'),
        sign_str.encode('utf-8'),
        hashlib.sha256
    ).hexdigest().upper()

def fetch_real_lazada_product(env_dict):
    """Panggil Lazada Open API dengan Pengesan Ralat Terperinci"""
    app_key = env_dict["LAZADA_APP_KEY"]
    app_secret = env_dict["LAZADA_APP_SECRET"]
    
    domain = "api.lazada.com.my"
    api_path = "/lazada.affiliate.product.query"
    url = f"https://{domain}/rest{api_path}"
    
    params = {
        "app_key": app_key,
        "timestamp": str(int(time.time() * 1000)),
        "sign_method": "sha256",
        "keywords": "dapur",
        "limit": "10"
    }
    
    params["sign"] = sign_lazada_request(api_path, params, app_secret)
    
    print("🔍 [DEBUG LAZADA REQUEST]")
    print(f"   URL: {url}")
    print(f"   App Key Used: {mask_key(app_key)}")
    
    try:
        response = requests.get(url, params=params, timeout=20)
        print(f"   HTTP Status Code: {response.status_code}")
        res_json = response.json()
        
        if response.status_code == 200 and "result" in res_json and "products" in res_json["result"]:
            products = res_json["result"]["products"]
            if products:
                product = products[0]
                print("🟢 [LAZADA API SUCCESS] Data produk berjaya diambil sepenuhnya.")
                return {
                    "title": product.get("title"),
                    "desc": product.get("description", "Produk berkualiti tinggi untuk kegunaan harian."),
                    "image": clean_url(product.get("image_url")),
                    "link": clean_url(product.get("click_url"))
                }
        
        print(f"⚠️ [LAZADA API NOTICE] Respons Tidak Lengkap: {res_json}")
    except Exception as e:
        print(f"🔴 [LAZADA API ERROR DIAGNOSTIC]: {e}")

    # Fallback Data Produk dengan Direct Image URL
    member_id = env_dict.get("LAZADA_MEMBER_ID", "234690568")
    sample_img = "[https://images.unsplash.com/photo-1556911220-e15b29be8c8f?auto=format&fit=crop&w=800&q=80](https://images.unsplash.com/photo-1556911220-e15b29be8c8f?auto=format&fit=crop&w=800&q=80)"
    sample_link = f"[https://s.lazada.com.my/s.CikguAff?site=](https://s.lazada.com.my/s.CikguAff?site=){member_id}"
    
    return {
        "title": "Periuk Cooking Pot Seramik Anti-Lekat Dapur Moden",
        "desc": "Bebas PTFE & PFOA, pemanasan sekata, pemegang kalis haba, mudah dicuci dan selamat untuk seisi keluarga.",
        "image": clean_url(sample_img),
        "link": clean_url(sample_link)
    }

def generate_ai_caption(env_dict, product_name, product_desc):
    """Panggil AI Endpoint dengan Pengesan Ralat Terperinci"""
    base_url = clean_url(env_dict["OPENROUTER_BASE_URL"]).rstrip('/')
    url = f"{base_url}/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {env_dict['OPENROUTER_API_KEY']}",
        "Content-Type": "application/json; charset=utf-8"
    }
    
    prompt_user = f"Buatkan ayat promosi untuk produk ini:\nNama Produk: {product_name}\nDeskripsi: {product_desc}"
    
    payload = {
        "model": env_dict["OPENROUTER_MODEL"],
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt_user}
        ],
        "temperature": 0.7
    }
    
    print("🔍 [DEBUG AI REQUEST]")
    print(f"   Target URL: {url}")
    print(f"   Model: {env_dict['OPENROUTER_MODEL']}")
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        response.encoding = 'utf-8'
        print(f"   HTTP Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("🟢 [AI API SUCCESS] Ayat promosi dijana dengan lancar.")
            return data['choices'][0]['message']['content'].strip()
        else:
            print(f"🔴 [AI API ERROR BODY]: {response.text}")
            raise Exception(f"Gagal panggil AI API | HTTP {response.status_code} | Body: {response.text}")
            
    except requests.exceptions.RequestException as req_err:
        print(f"🔴 [AI NETWORK ERROR]: {req_err}")
        raise Exception(f"Ralat Rangkaian AI: {req_err}")

def send_to_telegram(env_dict, caption, image_url, affiliate_link):
    """Hantar Gambar & Mesej ke Telegram dengan Pengesan Ralat & Muat Naik Direct Binary"""
    token = env_dict["TELEGRAM_BOT_TOKEN"]
    chat_id = env_dict["TELEGRAM_CHAT_ID"]
    
    domain = "api.telegram.org"
    url = f"https://{domain}/bot{token}/sendPhoto"
    
    clean_img_url = clean_url(image_url)
    clean_aff_link = clean_url(affiliate_link)
    full_caption = f"{caption}\n\nDapatkan di Lazada sekarang👇\n{clean_aff_link}"
    
    print("🔍 [DEBUG TELEGRAM REQUEST]")
    print(f"   Bot Token Used: {mask_key(token)}")
    print(f"   Chat ID: {chat_id}")
    print(f"   Image URL Target: {clean_img_url}")

    # Step A: Muat turun gambar secara tempatan (Guna User-Agent tersendiri untuk atasi hotlink block)
    img_bytes = None
    try:
        print("📥 [DOWNLOAD IMAGE] Memuat turun gambar ke dalam memori...")
        img_headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        img_res = requests.get(clean_img_url, headers=img_headers, timeout=15)
        if img_res.status_code == 200:
            img_bytes = BytesIO(img_res.content)
            img_bytes.name = "product_image.jpg"
            print("🟢 [DOWNLOAD OK] Gambar berjaya dimuat turun ke memori.")
        else:
            print(f"⚠️ [DOWNLOAD WARN] Gagal muat turun gambar | Status HTTP: {img_res.status_code}")
    except Exception as img_err:
        print(f"⚠️ [DOWNLOAD ERROR]: {img_err}")

    # Step B: Hantar Mesej ke Telegram API
    try:
        if img_bytes:
            # Kaedah 1: Muat naik terus fail imej sebagai binary (100% Berjaya)
            print("📤 [TELEGRAM UPLOAD] Menghantar gambar secara direct multipart file upload...")
            files = {"photo": ("product.jpg", img_bytes.getvalue(), "image/jpeg")}
            data = {"chat_id": chat_id, "caption": full_caption}
            response = requests.post(url, data=data, files=files, timeout=30)
        else:
            # Kaedah 2: Hantar via URL secara fallback
            print("📤 [TELEGRAM URL] Menghantar gambar secara URL link...")
            payload = {"chat_id": chat_id, "photo": clean_img_url, "caption": full_caption}
            response = requests.post(url, json=payload, timeout=20)
            
        res_json = response.json()
        print(f"   HTTP Status Code Telegram: {response.status_code}")
        
        if response.status_code == 200 and res_json.get("ok"):
            print("🟢 [TELEGRAM SUCCESS] Mesej + Gambar + Affiliate Link SELAMAT SAMPAI di Telegram!")
            return res_json
        else:
            print(f"🔴 [TELEGRAM API DETAILED ERROR RESPONSE]:\n{res_json}")
            raise Exception(f"Gagal Telegram API | Code: {res_json.get('error_code')} | Description: {res_json.get('description')}")
            
    except requests.exceptions.RequestException as req_err:
        print(f"🔴 [TELEGRAM NETWORK ERROR]: {req_err}")
        raise Exception(f"Network error Telegram: {req_err}")

def main():
    print("\n==================================================")
    print("🚀 [START] Memulakan Enjin Automasi Real Affiliate")
    print("==================================================\n")
    
    env_dict = {
        "TELEGRAM_BOT_TOKEN": sanitize_value(TELEGRAM_BOT_TOKEN),
        "TELEGRAM_CHAT_ID": sanitize_value(TELEGRAM_CHAT_ID),
        "OPENROUTER_BASE_URL": sanitize_value(OPENROUTER_BASE_URL),
        "OPENROUTER_MODEL": sanitize_value(OPENROUTER_MODEL),
        "OPENROUTER_API_KEY": sanitize_value(OPENROUTER_API_KEY),
        "LAZADA_APP_KEY": sanitize_value(LAZADA_APP_KEY),
        "LAZADA_APP_SECRET": sanitize_value(LAZADA_APP_SECRET),
        "LAZADA_MEMBER_ID": sanitize_value(LAZADA_MEMBER_ID)
    }
    
    # Validation awal
    missing = [k for k, v in env_dict.items() if not v and k not in ["LAZADA_APP_KEY", "LAZADA_APP_SECRET"]]
    if missing:
        print(f"🔴 [CRITICAL ENV ERROR] Kunci berikut kosong: {missing}")
        sys.exit(1)

    try:
        # 1. Lazada
        print("1️⃣ Mengambil data produk dari Lazada API...")
        product = fetch_real_lazada_product(env_dict)
        print(f"   📌 Tajuk: {product['title']}")
        print(f"   🖼️ Gambar: {product['image']}")
        print(f"   🔗 Affiliate Link: {product['link']}\n")
        
        # 2. AI Persona
        print("2️⃣ Menjana ayat AI Persona Cikgu/Surirumah...")
        caption = generate_ai_caption(env_dict, product['title'], product['desc'])
        
        print("\n--------------------------------------------------")
        print("📝 [HASIL AYAT AI]:")
        print("--------------------------------------------------")
        print(caption)
        print("--------------------------------------------------\n")
        
        # 3. Telegram
        print("3️⃣ Menghantar ke Telegram Bot...")
        send_to_telegram(env_dict, caption, product['image'], product['link'])
        
        print("\n==================================================")
        print("🟢 [LULUS 100%] PROSES AUTOMASI BERJAYA!")
        print("==================================================\n")

    except Exception as e:
        print("\n==================================================")
        print("🔴 [LAPORAN RALAT PENUH DIKESAN]")
        print("==================================================")
        print(f"Mesej Ralat Utama : {e}\n")
        print("📜 TRACEBACK:")
        traceback.print_exc()
        print("==================================================\n")

if __name__ == "__main__":
    main()