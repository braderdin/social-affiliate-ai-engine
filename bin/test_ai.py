import os
import sys
from dotenv import load_dotenv

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.ai_persona import generate_caption

load_dotenv('.env.local')

base_url = os.getenv("OPENROUTER_BASE_URL")
model = os.getenv("OPENROUTER_MODEL")
api_key = os.getenv("OPENROUTER_API_KEY")

print("🧪 [TEST INDIVIDU] Testing AI OpenRouter Only...")
success, caption = generate_caption(
    base_url=base_url,
    model=model,
    api_key=api_key,
    product_title="Periuk Seramik Anti-Lekat",
    product_desc="Bebas PTFE & PFOA, pemanasan sekata, selamat untuk keluarga."
)

if success:
    print("🟢 [AI OK] Hasil Generated Text:")
    print(f"\n{caption}\n")
else:
    print(f"🔴 [AI FAIL] Error: {caption}")