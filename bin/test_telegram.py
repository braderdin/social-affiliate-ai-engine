import os
import sys
from dotenv import load_dotenv

# Tambah root dir ke sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.telegram_bot import send_photo_to_telegram

load_dotenv('.env.local')

token = os.getenv("TELEGRAM_BOT_TOKEN")
chat_id = os.getenv("TELEGRAM_CHAT_ID")

print("🧪 [TEST INDIVIDU] Testing Telegram Bot API Only...")
success, response = send_photo_to_telegram(
    token=token,
    chat_id=chat_id,
    caption="✨ Ujian modul Telegram berasingan berjaya!",
    image_url="https://images.unsplash.com/photo-1556911220-e15b29be8c8f?auto=format&fit=crop&w=800&q=80",
    affiliate_link="https://s.lazada.com.my/s.sample"
)

if success:
    print("🟢 [TELEGRAM OK] Mesej ujian berjaya dihantar!")
else:
    print(f"🔴 [TELEGRAM FAIL] Response: {response}")