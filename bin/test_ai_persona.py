import os
import sys
import traceback
import requests
from dotenv import load_dotenv

# 1. Baca fail .env.local untuk ujian tempatan
load_dotenv('.env.local')

# 2. Ambil pemboleh ubah persekitaran
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
TELEGRAM_USERNAME = os.getenv("TELEGRAM_USERNAME")
TELEGRAM_URL = os.getenv("TELEGRAM_URL")

OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

LAZADA_APP_KEY = os.getenv("LAZADA_APP_KEY")
LAZADA_APP_SECRET = os.getenv("LAZADA_APP_SECRET")
LAZADA_MEMBER_ID = os.getenv("LAZADA_MEMBER_ID")
LAZADA_USER_TOKEN = os.getenv("LAZADA_USER_TOKEN")

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
    """Pembersihan pemboleh ubah daripada simbol luar dan pembuka/penutup petik"""
    if not val:
        return ""
    val = val.strip()
    if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
        val = val[1:-1]
    return val.strip()

def check_env_variables():
    """Semak kewujudan kunci API wajib"""
    required_vars = {
        "TELEGRAM_BOT_TOKEN": sanitize_value(TELEGRAM_BOT_TOKEN),
        "TELEGRAM_CHAT_ID": sanitize_value(TELEGRAM_CHAT_ID),
        "OPENROUTER_BASE_URL": sanitize_value(OPENROUTER_BASE_URL),
        "OPENROUTER_MODEL": sanitize_value(OPENROUTER_MODEL),
        "OPENROUTER_API_KEY": sanitize_value(OPENROUTER_API_KEY)
    }
    
    missing_vars = [key for key, val in required_vars.items() if not val]
    
    if missing_vars:
        print("🔴 [RALAT ENVIRONMENT] Kunci berikut tiada atau kosong di dalam .env.local:")
        for var in missing_vars:
            print(f"   ❌ {var}")
        print("\n💡 Sila pastikan fail .env.local telah diisi sepenuhnya.\n")
        return False, required_vars
    
    print("🟢 [ENVIRONMENT OK] Semua kunci API wajib tersedia.")
    return True, required_vars

def generate_ai_caption(env_dict, product_name, product_desc):
    """Panggil AI Endpoint"""
    base_url = env_dict["OPENROUTER_BASE_URL"].rstrip('/')
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
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        response.encoding = 'utf-8' # Memastikan emoji & bahasa Melayu dibaca bersih
        
        if response.status_code == 200:
            data = response.json()
            caption = data['choices'][0]['message']['content'].strip()
            print("🟢 [AI SUCCESS] Ayat promosi AI berjaya dijana.")
            return caption
        else:
            print(f"🔴 [AI ERROR] Status Code: {response.status_code}")
            print(f"   Laporan Respons: {response.text}")
            raise Exception(f"Gagal panggil AI API ({response.status_code}): {response.text}")
            
    except requests.exceptions.RequestException as req_err:
        print(f"🔴 [AI NETWORK ERROR] Ralat sambungan ke AI Base URL ({base_url})")
        raise Exception(f"Network error pada AI API: {req_err}")

def send_to_telegram(env_dict, caption, image_url, affiliate_link):
    """Hantar Gambar + Caption + Link ke Telegram Bot API"""
    token = env_dict["TELEGRAM_BOT_TOKEN"]
    chat_id = env_dict["TELEGRAM_CHAT_ID"]
    
    # Trik penggabungan string supaya VS Code / Markdown tak kacau URL
    domain = "api.telegram.org"
    url = f"https://{domain}/bot{token}/sendPhoto"
    
    full_caption = f"{caption}\n\nDapatkan di Lazada sekarang👇\n{affiliate_link}"
    
    payload = {
        "chat_id": chat_id,
        "photo": image_url.strip(),
        "caption": full_caption
    }
    
    try:
        response = requests.post(url, json=payload, timeout=20)
        res_json = response.json()
        
        if response.status_code == 200 and res_json.get("ok"):
            print("🟢 [TELEGRAM SUCCESS] Gambar & caption berjaya dihantar ke Telegram!")
            return res_json
        else:
            print(f"🔴 [TELEGRAM ERROR] Status Code: {response.status_code}")
            print(f"   Keterangan Ralat Telegram: {res_json.get('description', res_json)}")
            raise Exception(f"Gagal hantar ke Telegram: {res_json.get('description', 'Unknown Error')}")
            
    except requests.exceptions.RequestException as req_err:
        print("🔴 [TELEGRAM NETWORK ERROR] Ralat sambungan ke Telegram API")
        raise Exception(f"Network error Telegram: {req_err}")

def main():
    print("\n==================================================")
    print("🚀 [START] Memulakan Ujian Automasi AI Persona")
    print("==================================================\n")
    
    # 1. Semakan Environment Variables
    env_ok, env_dict = check_env_variables()
    if not env_ok:
        sys.exit(1)
        
    # Data Ujian (Dummy Data)
    dummy_product_name = "Pengukus Makanan Elektrik Multipurpose 2-Tier"
    dummy_product_desc = "Kapasiti besar 5L, auto-off keselamatan, sesuai untuk kukus makanan bayi dan lauk pauk dapur dengan cepat."
    
    # URL bersih tanpa pembungkusan markdown
    unsplash_domain = "images.unsplash.com"
    lazada_domain = "s.lazada.com.my"
    
    dummy_image_url = f"https://{unsplash_domain}/photo-1584269600464-37b1b58a9fe7?w=500"
    dummy_affiliate_link = f"https://{lazada_domain}/s.sampleLink"
    
    try:
        # 2. Jana Ayat Persona AI
        print("\n1️⃣ Menjana ayat promosi dari AI...")
        caption = generate_ai_caption(env_dict, dummy_product_name, dummy_product_desc)
        
        print("\n--------------------------------------------------")
        print("📝 [HASIL AYAT AI CIKGU/SURIRUMAH]:")
        print("--------------------------------------------------")
        print(caption)
        print("--------------------------------------------------\n")
        
        # 3. Hantar ke Telegram
        print("2️⃣ Menghantar hasil ke Telegram Bot...")
        send_to_telegram(env_dict, caption, dummy_image_url, dummy_affiliate_link)
        
        print("\n==================================================")
        print("🟢 [UJIAN SELESAI] SEMUA ALIRAN BERJAYA 100%!")
        print("==================================================\n")

    except Exception as e:
        print("\n==================================================")
        print("🔴 [LAPORAN KESAN RALAT TERPERINCI]")
        print("==================================================")
        print(f"Mesej Ralat Utama : {e}")
        print("\n📜 TRACEBACK BUKTI RALAT:")
        traceback.print_exc()
        print("==================================================\n")

if __name__ == "__main__":
    main()