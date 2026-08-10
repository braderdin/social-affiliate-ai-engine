import sys
import os
import asyncio
import json
import logging
from dotenv import load_dotenv

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(ROOT_DIR)

env_local = os.path.join(ROOT_DIR, ".env.local")
if os.path.exists(env_local):
    load_dotenv(dotenv_path=env_local, override=True)

import modal

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

def sanitize_val(val):
    if not val:
        return ""
    return str(val).strip().strip('"').strip("'")

async def main():
    print("="*70)
    print("🧪 UJIAN DIAGNOSTIK LOCAL -> MODAL.COM SCRAPER")
    print("="*70)

    token_id = sanitize_val(os.getenv("MODAL_TOKEN_ID"))
    token_secret = sanitize_val(os.getenv("MODAL_TOKEN_SECRET"))

    if not token_id or not token_secret:
        print("🔴 [RALAT] MODAL_TOKEN_ID / MODAL_TOKEN_SECRET tidak dijumpai di .env.local")
        sys.exit(1)

    print(f"📌 MODAL_TOKEN_ID: {token_id[:6]}...{token_id[-4:]}")

    test_keyword = "periuk seramik"
    print(f"🔍 Menghantar kata kunci carian: '{test_keyword}'...")

    try:
        search_fn = modal.Function.from_name("lazada-playwright-scraper", "search_lazada_products")
        response = await search_fn.remote.aio(keyword=test_keyword, max_results=3)

        print("\n" + "="*70)
        print(f"📊 STATUS HASIL: {response.get('status')}")
        print("="*70)
        print(f"📄 Laporan Diagnostik Modal:\n{json.dumps(response.get('diagnostics'), indent=2)}")

        if response.get("status") == "SUCCESS":
            print("\n🟢 PRODUK DIJUMPAI:")
            print(json.dumps(response.get("products"), indent=2))
        else:
            print("\n🔴 GAGAL MENDAPAT PRODUK! Sila semak 'diagnostics' di atas untuk punca ralat.")

    except Exception as e:
        print(f"\n💥 [RALAT PEMANGGILAN MODAL]: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())