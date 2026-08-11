import os
import sys
import time
from dotenv import load_dotenv

load_dotenv(dotenv_path=".env.local")
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.facebook_bot import send_to_facebook_page
from src.lifestyle_ai_persona import (
    generate_story_from_image_description,
    generate_unsplash_keywords,
    select_best_image_candidate,
)
from src.lifestyle_image_fetcher import (
    fetch_candidate_images_from_queries,
    mark_image_id_posted,
)
from src.redis_db import mark_product_posted
from src.telegram_bot import send_photo_to_telegram
from src.vector_db import is_similar_product_posted, mark_vector_posted


def run_lifestyle_posting_job():
  print("\n" + "=" * 70)
  print(
      "📖 [START] ENJIN PEMPOSAN CERITA HARIAN (CIKGU SURI RUMAH 2.0 - AI"
      " AUTONOMI)"
  )
  print("=" * 70)

  # Pembacaan daripada Pembolehubah Persekitaran (.env.local & GitHub Secrets)
  base_url = os.getenv("OPENROUTER_BASE_URL", "").strip()
  model = os.getenv("OPENROUTER_MODEL", "").strip()
  api_key = os.getenv("OPENROUTER_API_KEY", "").strip()

  unsplash_key = os.getenv("UNSPLASH_ACCESS_KEY", "").strip()

  redis_url = os.getenv("UPSTASH_REDIS_REST_URL", "").strip()
  redis_token = os.getenv("UPSTASH_REDIS_REST_TOKEN", "").strip()
  vector_url = os.getenv("UPSTASH_VECTOR_REST_URL", "").strip()
  vector_token = os.getenv("UPSTASH_VECTOR_REST_TOKEN", "").strip()

  tg_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
  tg_chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()

  fb_page_id = os.getenv("FACEBOOK_PAGE_ID", "").strip() or os.getenv(
      "META_PAGE_ID", ""
  ).strip()
  fb_page_token = (
      os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN", "").strip()
      or os.getenv("FB_PAGE_ACCESS_TOKEN", "").strip()
      or os.getenv("META_PAGE_ACCESS_TOKEN", "").strip()
  )

  # =========================================================================
  # LANGKAH 1: AI PERSONA JANA 5 KATA KUNCI CARIAN UNSPLASH
  # =========================================================================
  print(
      "\n💡 [LANGKAH 1] AI Persona 'Cikgu Suri Rumah 2.0' menjana 5 kata kunci"
      " carian Unsplash..."
  )
  generated_keywords = generate_unsplash_keywords(base_url, model, api_key)
  print(f"🎯 [KATA KUNCI DIJANA AI]: {generated_keywords}")

  # =========================================================================
  # LANGKAH 2: CUKUR & TARIK CALON GAMBAR DARIPADA UNSPLASH API
  # =========================================================================
  print(
      "\n🌐 [LANGKAH 2] Menarik calon gambar real-time dari Unsplash API"
      " berdasarkan kata kunci AI..."
  )
  candidates = fetch_candidate_images_from_queries(
      access_key=unsplash_key,
      keywords_list=generated_keywords,
      redis_url=redis_url,
      redis_token=redis_token,
      candidates_per_query=2,
  )

  if not candidates:
    print("❌ [ABORT] Tiada calon gambar yang sah dijumpai dari Unsplash.")
    return

  print(
      f"✅ Berjaya mengumpul {len(candidates)} calon gambar Unsplash yang belum"
      " pernah dipos."
  )

  # =========================================================================
  # LANGKAH 3: AI PERSONA CURATE & PILIH GAMBAR "PILIHAN HATI"
  # =========================================================================
  print(
      "\n👀 [LANGKAH 3] AI Persona meneliti senarai calon & memilih gambar"
      " pilihan hati..."
  )
  selected_candidate, selection_reason = select_best_image_candidate(
      base_url, model, api_key, candidates
  )

  photo_id = selected_candidate.get("photo_id")
  image_url = selected_candidate.get("image_url")
  image_desc = selected_candidate.get("description")
  keyword_used = selected_candidate.get("keyword")

  print(f"📸 [UNSPLASH PHOTO ID] : {photo_id}")
  print(f"🔗 [IMAGE URL]        : {image_url}")
  print(f"👁️ [HURAIAN VISUAL]   : {image_desc}")
  print(f"💬 [ALASAN AI PILIH]  : {selection_reason}")

  # =========================================================================
  # LANGKAH 4: AI PERSONA JANA PENULISAN CERITA FB
  # =========================================================================
  print(
      "\n✍️ [LANGKAH 4] AI Persona menjana cerita Facebook berdasarkan gambar"
      " pilihan..."
  )
  selected_story = None

  for attempt in range(1, 4):
    ok_story, story_text = generate_story_from_image_description(
        base_url, model, api_key, image_desc, selection_reason
    )
    if not ok_story or not story_text:
      continue

    if vector_url and vector_token:
      if is_similar_product_posted(vector_url, vector_token, story_text):
        print(
            "  ⏭️ [VECTOR SKIP] Cerita serupa dikesan di Vector DB. Mencuba"
            " semula..."
        )
        continue

    selected_story = story_text
    break

  if not selected_story:
    selected_story = (
        "Salam sejahtera kawan-kawan sekalian! Cikgu kongsikan pemandangan"
        " indah hari ini. Cikgu doakan semoga hari ini membawa kebahagiaan dan"
        " ketenangan buat kita semua. Salam mesra daripada Cikgu!"
    )

  print(f"\n✅ [CERITA AI CIKGU SURI RUMAH 2.0]:\n{selected_story}\n")

  tg_success = False
  fb_success = False

  # =========================================================================
  # PENYIARAN KE TELEGRAM & FACEBOOK
  # =========================================================================
  if tg_token and tg_chat_id:
    print("✈️ [STEP 5A] Menyiar ke Telegram Channel...")
    sent_tg, res_tg = send_photo_to_telegram(
        token=tg_token,
        chat_id=tg_chat_id,
        caption=selected_story,
        image_url=image_url,
        affiliate_link="",
    )
    if sent_tg:
      print("  ✅ Berjaya dipos ke Telegram Channel!")
      tg_success = True
    else:
      print(f"  ❌ Gagal pos ke Telegram: {res_tg}")

  if fb_page_id and fb_page_token:
    print("\n📘 [STEP 5B] Menyiar ke Facebook Page...")
    sent_fb, res_fb = send_to_facebook_page(
        page_id=fb_page_id,
        page_token=fb_page_token,
        caption=selected_story,
        image_url=image_url,
        affiliate_link="",
    )
    if sent_fb:
      print(
          "  ✅ Berjaya dipos ke Facebook Page! (Post ID:"
          f" {res_fb.get('post_id')})"
      )
      fb_success = True
    else:
      print(f"  ❌ Gagal pos ke Facebook Page: {res_fb}")

  # =========================================================================
  # REKOD STATUS KE REDIS & VECTOR DB
  # =========================================================================
  if tg_success or fb_success:
    print(
        "\n💾 [REKOD] Merekodkan Unsplash Photo ID & cerita ke Redis & Vector"
        " DB..."
    )
    unique_id = f"lifestyle_{photo_id}"

    mark_image_id_posted(redis_url, redis_token, photo_id)
    print(
        f"  ✅ Unsplash Photo ID '{photo_id}' direkodkan di Upstash Redis (TTL"
        " 30 Hari)."
    )

    if vector_url and vector_token:
      mark_vector_posted(vector_url, vector_token, unique_id, selected_story)
      print("  ✅ Embedding cerita disimpan di Upstash Vector DB.")

    if redis_url and redis_token:
      mark_product_posted(redis_url, redis_token, unique_id, selected_story)
      print("  ✅ Rekod cerita disimpan di Upstash Redis.")

    print(
        "\n🎉 [SUCCESS] Hantaran Cikgu Suri Rumah 2.0 (AI Autonomi) berjaya"
        " disiarkan!\n"
    )


if __name__ == "__main__":
  run_lifestyle_posting_job()