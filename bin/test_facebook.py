import os
import sys
import json
import requests
from dotenv import load_dotenv

# Menambah direktori utama ke sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Muat turun pemboleh ubah persekitaran (.env.local)
load_dotenv('.env.local')

def sanitize_value(val):
    if not val:
        return ""
    val = str(val).strip()
    if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
        val = val[1:-1]
    return val.strip()

def mask_string(val):
    if not val or len(val) < 8:
        return "***"
    return val[:4] + "..." + val[-4:]

def test_facebook_diagnostics():
    print("==================================================")
    print("🔍 [FB DIAGNOSTIC] Ujian Kebenaran, Gambar & Komen Meta Graph API")
    print("==================================================\n")

    # Pembacaan Kunci Facebook mengikut nama-nama pemboleh ubah persekitaran di env.example
    page_id = sanitize_value(
        os.getenv("FACEBOOK_PAGE_ID") or 
        os.getenv("FB_PAGE_ID") or 
        os.getenv("META_PAGE_ID")
    )
    
    page_token = sanitize_value(
        os.getenv("FB_PAGE_ACCESS_TOKEN") or 
        os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN") or 
        os.getenv("META_PAGE_ACCESS_TOKEN")
    )

    print(f"📌 [INFO] Page ID          : {page_id if page_id else '🔴 KOSONG'}")
    print(f"📌 [INFO] Page Access Token: {mask_string(page_token)}\n")

    if not page_id or not page_token:
        print("🔴 [RALAT KRITIKAL]: FACEBOOK_PAGE_ID / FB_PAGE_ACCESS_TOKEN tidak dijumpai di .env.local!")
        sys.exit(1)

    graph_base_url = "https://graph.facebook.com/v19.0"

    # ==================================================
    # 1. SEMAK KEBENARAN TOKEN & IDENTITI PAGE
    # ==================================================
    print("1️⃣ [STEP 1] Semakan Kebenaran Token & Identiti Page...")
    me_url = f"{graph_base_url}/me"
    me_params = {
        "fields": "id,name",
        "access_token": page_token
    }

    try:
        res_me = requests.get(me_url, params=me_params, timeout=15)
        me_json = res_me.json()

        print(f"📊 [HTTP STATUS]: {res_me.status_code}")
        if res_me.status_code == 200 and "id" in me_json:
            print(f"🟢 [PAGE IDENTITI]: Nama Page = '{me_json.get('name')}' | ID = {me_json.get('id')}")
            
            perms_data = me_json.get("permissions", {}).get("data", [])
            granted_perms = [p.get("permission") for p in perms_data if p.get("status") == "granted"]
            print(f"📜 [KEBENARAN DILEPASI]: {granted_perms if granted_perms else 'Tiada senarai spesifik dipulangkan.'}\n")
        else:
            err = me_json.get("error", {})
            print(f"🔴 [FB ERROR - ME CHECK]: Code {err.get('code')} | Message: {err.get('message')}\n")
            print(f"📄 Respons Penuh JSON:\n{json.dumps(me_json, indent=2)}\n")
    except Exception as e:
        print(f"💥 [EXCEPTION - STEP 1]: {e}\n")

    # ==================================================
    # 2. UJIAN HANTAR GAMBAR + CAPTION (POST PHOTO)
    # ==================================================
    print("2️⃣ [STEP 2] Ujian Hantar Gambar + Caption ke Facebook Page...")
    photo_url = f"{graph_base_url}/{page_id}/photos"
    sample_img = "https://my-live-01.slatic.net/p/30d3234bcab3e8a9fd0167d4278c613a.jpg"
    sample_caption = "🧪 [TEST DIAGNOSTIC FB] Ujian hantaran foto ke Facebook Page 'Racun Dapur Ibu'."

    photo_payload = {
        "url": sample_img,
        "caption": sample_caption,
        "published": "true",
        "access_token": page_token
    }

    target_post_id = None

    try:
        res_photo = requests.post(photo_url, data=photo_payload, timeout=25)
        photo_json = res_photo.json()

        print(f"📊 [HTTP STATUS]: {res_photo.status_code}")
        if res_photo.status_code == 200 and ("id" in photo_json or "post_id" in photo_json):
            photo_id = photo_json.get("id")
            target_post_id = photo_json.get("post_id") or photo_id
            print(f"🟢 [SUCCESS POST PHOTO] Gambar berjaya dipos!")
            print(f"   📌 Photo ID : {photo_id}")
            print(f"   📌 Target Post ID untuk Komen : {target_post_id}\n")
        else:
            err = photo_json.get("error", {})
            print(f"🔴 [FB ERROR - POST PHOTO]:")
            print(f"   • Code     : {err.get('code')}")
            print(f"   • Subcode  : {err.get('error_subcode')}")
            print(f"   • Type     : {err.get('type')}")
            print(f"   • Message  : {err.get('message')}")
            print(f"   • FB Trace : {err.get('fbtrace_id')}\n")
            print(f"📄 Respons Penuh JSON:\n{json.dumps(photo_json, indent=2)}\n")
            sys.exit(1)
    except Exception as e:
        print(f"💥 [EXCEPTION - STEP 2]: {e}\n")
        sys.exit(1)

    # ==================================================
    # 3. UJIAN MASUK KOMEN PERTAMA (POST COMMENT WITH LINK)
    # ==================================================
    print("3️⃣ [STEP 3] Ujian Masuk Komen Pertama + Affiliate Link...")
    comment_url = f"{graph_base_url}/{target_post_id}/comments"
    sample_comment = "🛒 Dapatkan di Lazada sekarang: https://s.lazada.com.my/s.Z2EWU2"

    comment_payload = {
        "message": sample_comment,
        "access_token": page_token
    }

    try:
        res_comment = requests.post(comment_url, data=comment_payload, timeout=20)
        comment_json = res_comment.json()

        print(f"📊 [HTTP STATUS]: {res_comment.status_code}")
        if res_comment.status_code == 200 and "id" in comment_json:
            print(f"🟢 [SUCCESS POST COMMENT] Komen pertama berjaya dimasukkan!")
            print(f"   📌 Comment ID : {comment_json.get('id')}\n")
        else:
            err = comment_json.get("error", {})
            print(f"🔴 [FB ERROR - POST COMMENT]:")
            print(f"   • Code     : {err.get('code')}")
            print(f"   • Subcode  : {err.get('error_subcode')}")
            print(f"   • Message  : {err.get('message')}")
            print(f"   • FB Trace : {err.get('fbtrace_id')}\n")
            print(f"📄 Respons Penuh JSON:\n{json.dumps(comment_json, indent=2)}\n")
            sys.exit(1)
    except Exception as e:
        print(f"💥 [EXCEPTION - STEP 3]: {e}\n")
        sys.exit(1)

    print("==================================================")
    print("🟢 [FB DIAGNOSTIC 100% LULUS] Facebook Page API Sedia Digunakan!")
    print("==================================================")

if __name__ == "__main__":
    test_facebook_diagnostics()