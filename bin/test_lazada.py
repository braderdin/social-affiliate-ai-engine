import os
import sys
from dotenv import load_dotenv

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.lazada_api import get_lazada_product

load_dotenv('.env.local')

app_key = os.getenv("LAZADA_APP_KEY")
app_secret = os.getenv("LAZADA_APP_SECRET")
member_id = os.getenv("LAZADA_MEMBER_ID")

print("🧪 [TEST INDIVIDU] Testing Lazada API Only...")
success, data = get_lazada_product(app_key, app_secret, member_id, keyword="dapur")

if success:
    print("🟢 [LAZADA API OK] Data Produk Sebenar:")
    print(f"   ID: {data['id']}")
    print(f"   Tajuk: {data['title']}")
    print(f"   Link: {data['link']}")
else:
    print(f"🔴 [LAZADA API FAIL] Laporan Response:\n{data}")