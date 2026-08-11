import json
import re
import requests


def remove_emojis_and_special_symbols(text):
  """Membersihkan teks daripada emoji dan simbol bulet khas."""
  if not text:
    return ""
  special_bullets = ["❖", "◆", "◇", "►", "•", "▪", "▲", "★"]
  for sym in special_bullets:
    text = text.replace(sym, "-")

  emoji_pattern = re.compile(
      "["
      "\U0001f600-\U0001f64f"
      "\U0001f300-\U0001f5ff"
      "\U0001f680-\U0001f6ff"
      "\U0001f1e0-\U0001f1ff"
      "\U00002702-\U000027b0"
      "\U000024c2-\U000025ca"
      "\U0001f900-\U0001f9ff"
      "\U0001fa70-\U0001faff"
      "]+",
      flags=re.UNICODE,
  )
  text = emoji_pattern.sub("", text)
  lines = [line.strip() for line in text.splitlines()]
  return "\n".join(lines).strip()


def generate_unsplash_keywords(base_url, model, api_key):
  """Langkah 1: AI Persona 'Cikgu Suri Rumah 2.0' menjana 5 kata kunci carian Unsplash

  (dalam Bahasa Inggeris) yang relevan dengan mood harian wanita/ibu di
  Malaysia.
  """
  if not base_url or not model or not api_key:
    return [
        "cozy morning coffee wooden table",
        "indoor potted green plants sunlit",
        "freshly baked bread kitchen table",
        "cozy living room reading nook",
        "peaceful rain garden window view",
    ]

  headers = {
      "Authorization": f"Bearer {api_key}",
      "Content-Type": "application/json; charset=utf-8",
  }

  system_prompt = """
Anda ialah 'Cikgu Suri Rumah 2.0', seorang bekas guru sekolah berpikiran terbuka, berpelajaran, mesra, periang, dan penuh idea kreatif. Anda kini seorang suri rumah sepenuh masa di Malaysia yang gemar berkongsi cerita kehidupan di Facebook.

TUGAS ANDA (LANGKAH 1):
Jana TEPAT 5 kata kunci carian gambar Unsplash dalam Bahasa Inggeris (English search queries) yang menggambarkan mood harian estetik, tenang, atau ceria untuk wanita/ibu/suri rumah di Malaysia.

KATEGORI PILIHAN (Sesuaikan mengikut ilham anda hari ini):
1. Rutin Kopi/Teh Pagi (e.g., cozy coffee mug on wooden balcony table)
2. Sudut Rumah & Pokok Hiasan (e.g., sunlit indoor potted plants aesthetic)
3. Masakan & Roti Dapur (e.g., fresh homemade pastry flour table kitchen)
4. Ruang Santai & Me-Time (e.g., cozy armchair reading book warm lighting)
5. Pemandangan Ketenangan Alam (e.g., serene green garden morning dew)

FORMAT OUTPUT WAJIB:
Kembalikan HANYA format JSON list bermula dengan [ dan berakhir dengan ] tanpa sebarang teks tambahan.
Contoh:
["cozy tea mug sunrise window", "minimalist indoor plants green corner", "freshly baked cinnamon rolls table", "cozy reading nook armchair book", "calm rainy window garden view"]
"""

  payload = {
      "model": model,
      "messages": [
          {"role": "system", "content": system_prompt.strip()},
          {
              "role": "user",
              "content": (
                  "Sila jana 5 kata kunci carian Unsplash dalam Bahasa Inggeris"
                  " untuk hari ini."
              ),
          },
      ],
      "temperature": 0.85,
      "max_tokens": 200,
  }

  url = f"{base_url.rstrip('/')}/chat/completions"

  try:
    response = requests.post(url, json=payload, headers=headers, timeout=20)
    response.encoding = "utf-8"
    if response.status_code == 200:
      res_json = response.json()
      raw_text = res_json["choices"][0]["message"]["content"].strip()
      match = re.search(r"\[.*\]", raw_text, re.DOTALL)
      if match:
        keywords = json.loads(match.group(0))
        if isinstance(keywords, list) and len(keywords) > 0:
          return keywords[:5]
  except Exception as e:
    print(f"⚠️ [AI KEYWORD GEN ERROR]: {e}")

  return [
      "cozy morning coffee mug",
      "green indoor plants aesthetic",
      "freshly baked pastry kitchen",
      "cozy reading armchair nook",
      "peaceful garden view sunlight",
  ]


def select_best_image_candidate(base_url, model, api_key, candidates):
  """Langkah 3: AI Persona meneliti senarai calon gambar Unsplash dan memilih 1

  gambar "pilihan hati" yang paling disukai beserta alasannya.
  """
  if not candidates:
    return None, "Tiada calon gambar diberikan."

  if len(candidates) == 1 or not base_url or not model or not api_key:
    return candidates[0], "Gambar ini dipilih sebagai pilihan tunggal."

  headers = {
      "Authorization": f"Bearer {api_key}",
      "Content-Type": "application/json; charset=utf-8",
  }

  candidates_summary = ""
  for idx, cand in enumerate(candidates):
    candidates_summary += f"CALON #{idx + 1}:\n"
    candidates_summary += f"- ID Gambar: {cand.get('photo_id')}\n"
    candidates_summary += (
        f"- Huraian Visual: {cand.get('description', 'Tiada huraian')}\n"
    )
    candidates_summary += f"- Kata Kunci Asal: {cand.get('keyword')}\n\n"

  system_prompt = f"""
Anda ialah 'Cikgu Suri Rumah 2.0', seorang wanita Malaysia berpelajaran, humoris, mesra, dan mempunyai cita rasa visual yang tinggi.

TUGAS ANDA (LANGKAH 3):
Sila teliti senarai calon gambar Unsplash di bawah. Pilih TEPAT 1 gambar yang paling anda suka dan rasa paling sesuai untuk dijadikan bahan bualan mesra bersama pengikut di Facebook hari ini.

SENARAI CALON GAMBAR:
{candidates_summary.strip()}

FORMAT OUTPUT WAJIB (JSON Sahaja):
{{
  "selected_index": <nombor_indeks_1_hingga_N>,
  "reason": "<alasan_mesra_dan_kelakar_mengapa_cikgu_suka_gambar_ini_dalam_bahasa_melayu>"
}}
"""

  payload = {
      "model": model,
      "messages": [
          {"role": "system", "content": system_prompt.strip()},
          {
              "role": "user",
              "content": (
                  "Pilih 1 gambar pilihan hati anda dan berikan alasan ringkas."
              ),
          },
      ],
      "temperature": 0.7,
      "max_tokens": 250,
  }

  url = f"{base_url.rstrip('/')}/chat/completions"

  try:
    response = requests.post(url, json=payload, headers=headers, timeout=25)
    response.encoding = "utf-8"
    if response.status_code == 200:
      res_json = response.json()
      raw_text = res_json["choices"][0]["message"]["content"].strip()
      match = re.search(r"\{.*\}", raw_text, re.DOTALL)
      if match:
        data = json.loads(match.group(0))
        sel_idx = int(data.get("selected_index", 1)) - 1
        reason = data.get(
            "reason", "Cikgu berkenan sangat dengan suasana gambar ini."
        )
        if 0 <= sel_idx < len(candidates):
          return candidates[sel_idx], reason
  except Exception as e:
    print(f"⚠️ [AI SELECTION ERROR]: {e}")

  return (
      candidates[0],
      "Pilihan automatik berdasarkan kesesuaian gambar pertama.",
  )


def generate_story_from_image_description(
    base_url, model, api_key, image_description, selection_reason=""
):
  """Langkah 4: AI Persona 'Cikgu Suri Rumah 2.0' menjana cerita harian FB

  berdasarkan gambar pilihan hati dan alasannya.
  """
  if not base_url or not model or not api_key:
    return False, "Kunci OpenRouter API / Base URL / Model tidak lengkap."

  headers = {
      "Authorization": f"Bearer {api_key}",
      "Content-Type": "application/json; charset=utf-8",
  }

  system_prompt = f"""
Anda ialah 'Cikgu Suri Rumah 2.0', seorang bekas guru sekolah di Malaysia yang kini menjadi suri rumah sepenuh masa.
WATAK & PERSONALITI:
- Berpelajaran, bijak, berpemikiran positif, penyayang, dan suka bercerita di media sosial.
- Humoris dan suka berseloroh secara halus tentang realiti kehidupan seharian (seperti hal rumah tangga, me-time yang diganggu, kopi sejuk, pokok bunga, atau rutin dapur).
- Mesra wanita, ibu-ibu, suri rumah, dan mudah diterima oleh segenap lapisan masyarakat.

HURAIAN VISUAL GAMBAR PILIHAN HATI ANDA (DARIPADA UNSPLASH):
"{image_description}"

ALASAN ANDA MEMILIH GAMBAR INI:
"{selection_reason}"

ARAHAN PENULISAN FB POST (STRICT IMAGE-FIRST VISION STORYTELLING):
1. Tulis penceritaan harian Facebook yang 100% TEPAT BERDASARKAN GAMBAR & ALASAN DI ATAS.
2. Ceritakan suasana seolah-olah anda sendiri yang merakam gambar tersebut sebentar tadi!
3. DILARANG mereka-reka objek utama yang tiada dalam huraian gambar.
4. DILARANG SAMA SEKALI menyebut tentang barang jualan, produk, harga, Lazada/Shopee, atau pautan/link!

ARAHAN FORMAT TEKS BERSIH (STRICT ZERO-EMOJI POLICY):
1. DILARANG SAMA SEKALI menggunakan sebarang emoji (0% emoji).
2. DILARANG SAMA SEKALI menggunakan simbol bullet khas (❖, ◆, •, ★, dsb).
3. Luahkan keriangan, kehangatan, dan unsur kelakar melalui pemilihan kata yang indah dan tanda baca biasa (! dan ?).

GAYA BAHASA:
1. Bahasa Melayu santai Malaysia yang manis, teratur, dan ada seloroh mesra.
2. Akhiri dengan soalan ikhlas dan lucu untuk mengajak kawan-kawan/ibu-ibu berborak di ruang komen.
3. Panjang teks: Antara 350 hingga 550 aksara sahaja.
"""

  prompt_user = (
      "Sila hasilkan penceritaan Facebook yang mesra, kelakar, teratur, dan"
      " selari sepenuhnya dengan gambar pilihan anda di atas!"
  )

  payload = {
      "model": model,
      "messages": [
          {"role": "system", "content": system_prompt.strip()},
          {"role": "user", "content": prompt_user.strip()},
      ],
      "temperature": 0.85,
      "max_tokens": 500,
  }

  url = f"{base_url.rstrip('/')}/chat/completions"

  try:
    response = requests.post(url, json=payload, headers=headers, timeout=30)
    response.encoding = "utf-8"

    if response.status_code == 200:
      res_json = response.json()
      if "choices" in res_json and len(res_json["choices"]) > 0:
        raw_content = res_json["choices"][0]["message"]["content"].strip()
        story_text = remove_emojis_and_special_symbols(raw_content)

        if len(story_text) > 700:
          story_text = story_text[:697] + "..."

        return True, story_text
      return False, "Format respon OpenRouter tidak sah."
    else:
      return (
          False,
          f"OpenRouter Error (Status {response.status_code}): {response.text}",
      )

  except Exception as e:
    return False, f"Ralat Rangkaian OpenRouter API: {str(e)}"