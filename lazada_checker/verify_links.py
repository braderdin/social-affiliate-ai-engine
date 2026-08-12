import os
import glob
import time
import hmac
import hashlib
import requests
import pandas as pd
from urllib.parse import urlparse, parse_qs
from dotenv import load_dotenv

# Load environment variables daripada .env.local di root directory
env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '.env.local'))
load_dotenv(dotenv_path=env_path)

LAZADA_APP_KEY = os.getenv("LAZADA_APP_KEY", "")
LAZADA_APP_SECRET = os.getenv("LAZADA_APP_SECRET", "")
LAZADA_MEMBER_ID = os.getenv("LAZADA_MEMBER_ID", "")
LAZADA_USER_TOKEN = os.getenv("LAZADA_USER_TOKEN", "")

# Standard Lazada API Base URL
LAZADA_API_URL = "https://api.lazada.com.my/rest"

def generate_signature(api_path: str, params: dict, app_secret: str) -> str:
    """
    Menjana tandatangan HMAC-SHA256 mengikut spesifikasi Lazada Open Platform API.
    """
    sorted_params = sorted(params.items())
    string_to_sign = api_path
    for k, v in sorted_params:
        if k != 'sign' and not isinstance(v, bytes):
            string_to_sign += f"{k}{v}"
            
    h = hmac.new(app_secret.encode('utf-8'), string_to_sign.encode('utf-8'), hashlib.sha256)
    return h.hexdigest().upper()

def verify_via_lazada_api(source_url: str) -> dict:
    """
    Menghantar permintaan ke Lazada Open Platform API untuk menguji pautan affiliate.
    """
    if not LAZADA_APP_KEY or not LAZADA_APP_SECRET:
        return {"api_status": "SKIPPED", "api_message": "API Keys tiada dalam .env.local"}

    api_path = "/affiliate/link/generate"
    timestamp = str(int(time.time() * 1000))

    params = {
        "app_key": LAZADA_APP_KEY,
        "timestamp": timestamp,
        "sign_method": "sha256",
        "source_url": source_url,
    }

    if LAZADA_USER_TOKEN:
        params["access_token"] = LAZADA_USER_TOKEN

    # Janakan tandatangan HMAC-SHA256
    params["sign"] = generate_signature(api_path, params, LAZADA_APP_SECRET)

    try:
        response = requests.get(f"{LAZADA_API_URL}{api_path}", params=params, timeout=10)
        res_data = response.json()

        if response.status_code == 200 and res_data.get("code") == "0":
            return {
                "api_status": "SUCCESS",
                "api_message": "Pautan disahkan oleh API Lazada",
                "api_generated_link": res_data.get("data", {}).get("tracking_link", "")
            }
        else:
            msg = res_data.get("message", res_data.get("type", "Unknown Error"))
            return {
                "api_status": "API_ERROR",
                "api_message": f"Kod API: {res_data.get('code', 'N/A')} - {msg}",
                "api_generated_link": ""
            }
    except Exception as e:
        return {
            "api_status": "REQUEST_FAILED",
            "api_message": str(e),
            "api_generated_link": ""
        }

def check_member_id_in_url(url: str, member_id: str) -> bool:
    """
    Menyemak kehadiran Member ID dalam parameter URL atau query string.
    """
    if not member_id or not isinstance(url, str):
        return False
    return member_id in url

def resolve_redirect_url(short_url: str) -> str:
    """
    Mengikut tindanan redirect HTTP bagi pautan ringkas s.lazada.com.my.
    """
    if not isinstance(short_url, str) or not short_url.startswith("http"):
        return short_url
    try:
        resp = requests.head(short_url, allow_redirects=True, timeout=8)
        return resp.url
    except Exception:
        return short_url

def process_excel_files():
    """
    Proses utama membaca folder link_affiliate_xlsx dan menyemak setiap pautan.
    """
    input_folder = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'link_affiliate_xlsx'))
    output_folder = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'link_verification_results'))
    os.makedirs(output_folder, exist_ok=True)

    excel_files = glob.glob(os.path.join(input_folder, "*.xlsx"))

    if not excel_files:
        print(f"❌ Tiada fail .xlsx dijumpai dalam folder: {input_folder}")
        return

    print("==================================================")
    print("      LAZADA AFFILIATE LINK VERIFIER TOOL        ")
    print("==================================================")
    print(f"📁 Folder Input : {input_folder}")
    print(f"🔑 App Key       : {LAZADA_APP_KEY if LAZADA_APP_KEY else 'TIADA'}")
    print(f"🆔 Member ID     : {LAZADA_MEMBER_ID if LAZADA_MEMBER_ID else 'TIADA'}")
    print(f"📄 Jumlah Fail   : {len(excel_files)}")
    print("--------------------------------------------------\n")

    summary_results = []

    for file_path in excel_files:
        filename = os.path.basename(file_path)
        print(f"🔍 Memproses fail: {filename} ...")

        try:
            df = pd.read_excel(file_path)
        except Exception as e:
            print(f"   ❌ Gagal membaca fail {filename}: {e}")
            continue

        for idx, row in df.iterrows():
            product_name = row.get("product_name", f"Baris {idx + 1}")
            item_id = row.get("item_id", "")
            
            # Dapatkan pautan yang tersimpan
            promo_link = str(row.get("promo_link", ""))
            promo_short_link = str(row.get("promo_short_link", ""))
            product_url = str(row.get("product_url", ""))

            target_link = promo_short_link if promo_short_link.startswith("http") else promo_link

            if not target_link.startswith("http"):
                target_link = product_url

            # 1. Semakan Parameter Member ID
            has_member_id = check_member_id_in_url(promo_link, LAZADA_MEMBER_ID) or \
                            check_member_id_in_url(target_link, LAZADA_MEMBER_ID)

            # 2. Buka redirect jika pautan pendek
            resolved_url = target_link
            if "s.lazada.com.my" in target_link:
                resolved_url = resolve_redirect_url(target_link)
                if not has_member_id:
                    has_member_id = check_member_id_in_url(resolved_url, LAZADA_MEMBER_ID)

            # 3. Semakan API Rasmi Lazada
            api_res = verify_via_lazada_api(product_url if product_url.startswith("http") else target_link)

            # Keputusan Pengesahan Akhir
            if has_member_id or api_res["api_status"] == "SUCCESS":
                status_final = "✅ SAH (Affiliate Anda)"
            elif api_res["api_status"] == "API_ERROR":
                status_final = "⚠️ PERLU SEMAKAN (Ralat API)"
            else:
                status_final = "❌ BUKAN AFFILIATE / TIADA MATCH"

            summary_results.append({
                "Nama Fail": filename,
                "Baris": idx + 2,
                "Nama Produk": product_name,
                "Item ID": item_id,
                "Member ID Match": "YA" if has_member_id else "TIDAK",
                "Status API": api_res["api_status"],
                "Mesej API": api_res["api_message"],
                "Status Akhir": status_final,
                "Pautan Ditemui": target_link,
                "Pautan Sebenar (Resolved)": resolved_url
            })

    # Simpan Laporan
    res_df = pd.DataFrame(summary_results)
    output_excel = os.path.join(output_folder, "Laporan_Pengesahan_Affiliate.xlsx")
    output_csv = os.path.join(output_folder, "Laporan_Pengesahan_Affiliate.csv")

    res_df.to_excel(output_excel, index=False)
    res_df.to_csv(output_csv, index=False)

    print("\n==================================================")
    print("             LAPORAN UJIAN SELESAI                ")
    print("==================================================")
    print(f"📊 Jumlah Pautan Diuji : {len(summary_results)}")
    print(f"✅ Fail Laporan Excel  : {output_excel}")
    print(f"📄 Fail Laporan CSV    : {output_csv}\n")

if __name__ == "__main__":
    process_excel_files()