import os
import sys
import json
from dotenv import load_dotenv

# Menambah direktori utama ke sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.lazada_api import get_lazada_product

# 1. Muat turun pemboleh ubah dari .env.local
load_dotenv('.env.local')

def sanitize_value(val):
    if not val:
        return ""
    val = str(val).strip()
    if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
        val = val[1:-1]
    return val.strip()

def main():
    print("==================================================")
    print("🧪 [TEST INDIVIDU] Testing Lazada API Only...")
    print("==================================================")

    # 2. Ambil pemboleh ubah persekitaran mengikut piawaian .env.example
    app_key = sanitize_value(os.getenv("LAZADA_LiteApp_Key") or os.getenv("LAZADA_APP_KEY"))
    app_secret = sanitize_value(os.getenv("LAZADA_LiteApp_Secret") or os.getenv("LAZADA_APP_SECRET"))
    user_token = sanitize_value(os.getenv("LAZADA_USER_TOKEN"))
    member_id = sanitize_value(os.getenv("LAZADA_MEMBER_ID"))

    # 3. Semakan Kunci Wajib
    missing = []
    if not app_key: missing.append("LAZADA_LiteApp_Key / LAZADA_APP_KEY")
    if not app_secret: missing.append("LAZADA_LiteApp_Secret / LAZADA_APP_SECRET")
    if not user_token: missing.append("LAZADA_USER_TOKEN")

    if missing:
        print(f"🔴 [RALAT KRITIKAL]: Kunci persekitaran tidak lengkap di dalam .env.local: {missing}")
        sys.exit(1)

    # 4. Panggilan tepat mengikut signature fungsi dalam src/lazada_api.py:
    # get_lazada_product(app_key, app_secret, user_token, member_id)
    success, data = get_lazada_product(app_key, app_secret, user_token, member_id)

    if success:
        print("\n🟢 [LAZADA API OK] Data Produk Sebenar Dipulangkan:")
        print(f"   📌 ID     : {data.get('id')}")
        print(f"   📌 Tajuk  : {data.get('title')}")
        print(f"   🖼️ Gambar : {data.get('image')}")
        print(f"   🔗 Link   : {data.get('link')}\n")
    else:
        print(f"\n🔴 [LAZADA API FAIL] Laporan Response:")
        if isinstance(data, dict):
            print(json.dumps(data, indent=2))
        else:
            print(data)

if __name__ == "__main__":
    main()