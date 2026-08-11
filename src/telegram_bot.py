import os
import requests
from io import BytesIO

def send_photo_to_telegram(token, chat_id, caption, image_url, affiliate_link=""):
    """
    Hantar gambar secara direct binary upload ke Telegram Bot API.
    Jika affiliate_link kosong/tiada, HANYA hantar kapsyen cerita bersih (Real Human Mode).
    """
    domain = "api.telegram.org"
    url = f"https://{domain}/bot{token}/sendPhoto"
    
    clean_link = str(affiliate_link or "").strip()
    if clean_link:
        full_caption = f"{caption}\n\nDapatkan di Lazada sekarang👇\n{clean_link}"
    else:
        full_caption = caption  # 100% Cerita Bersih Tanpa Teks Lazada

    # Download gambar ke memori
    img_bytes = None
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        res = requests.get(image_url, headers=headers, timeout=15)
        if res.status_code == 200:
            img_bytes = BytesIO(res.content)
            img_bytes.name = "lifestyle.jpg"
    except Exception as e:
        print(f"⚠️ [TELEGRAM WARN] Gagal muat turun gambar: {e}")

    # Hantar ke Telegram
    if img_bytes:
        files = {"photo": ("lifestyle.jpg", img_bytes.getvalue(), "image/jpeg")}
        data = {"chat_id": chat_id, "caption": full_caption}
        response = requests.post(url, data=data, files=files, timeout=30)
    else:
        payload = {"chat_id": chat_id, "photo": image_url, "caption": full_caption}
        response = requests.post(url, json=payload, timeout=20)
        
    res_json = response.json()
    if response.status_code == 200 and res_json.get("ok"):
        return True, res_json
    else:
        return False, res_json