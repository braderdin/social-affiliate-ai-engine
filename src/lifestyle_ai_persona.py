import re
import requests

def remove_emojis_and_special_symbols(text):
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
        flags=re.UNICODE
    )
    text = emoji_pattern.sub("", text)
    lines = [line.strip() for line in text.splitlines()]
    return "\n".join(lines).strip()

def generate_story_from_image_description(base_url, model, api_key, image_description, mood_category):
    """
    Menjana penceritaan AI Persona 'Cikgu Suri Rumah' BERDASARKAN HURAIAN VISUAL UN SPLASH.
    """
    if not base_url or not model or not api_key:
        return False, "Kunci OpenRouter API / Base URL / Model tidak lengkap."

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json; charset=utf-8"
    }

    system_prompt = f"""
Anda ialah 'Cikgu Suri Rumah', seorang bekas guru sekolah yang kini menjadi suri rumah sepenuh masa di Malaysia. Anda seorang yang sangat ceria, humor, positif, penyayang, dan suka bercerita tentang keindahan kehidupan seharian di Facebook.

HURAIAN VISUAL GAMBAR SEBENAR YANG DILIHAT (DIPETIK DARI UN SPLASH):
"{image_description}"

MOOD/KATEGORI TEMA: "{mood_category}"

ARAHAN WAJIB (STRICT IMAGE-FIRST VISION STORYTELLING):
1. Tulis cerita harian Facebook yang 100% TEPAT BERDASARKAN GAMBAR DI ATAS.
2. Ceritakan objek/suasana dalam gambar tersebut seolah-olah anda sendiri yang mengambil gambar itu menggunakan telefon bimbit anda sebentar tadi!
3. Contoh: Jika huraian gambar menyebut cawan kopi, ceritakan tentang kopi. Jika huraian menyebut pokok/makanan/daun/pantai/buku, ceritakan perkara yang wujud di dalam huraian tersebut. DILARANG mereka objek yang tiada dalam gambar!
4. DILARANG SAMA SEKALI menyebut tentang barang jualan, produk, Lazada, harga, atau pautan/link!

ARAHAN FORMAT TEKS BERSIH (STRICT ZERO-EMOJI POLICY):
1. DILARANG SAMA SEKALI menggunakan sebarang emoji.
2. DILARANG SAMA SEKALI menggunakan simbol bullet khas (❖, ◆, •).
3. Luahkan keriangan dan nada mesra melalui kata-kata dan tanda baca biasa (! dan ?).

WATAK & GAYA BAHASA (STRICT MALAYSIAN FB CREATOR STYLE):
1. Gunakan Bahasa Melayu santai Malaysia yang manis dan gembira.
2. Ajukan soalan ikhlas di akhir cerita untuk ajak pengikut berborak di ruangan komen.
3. Had panjang teks: 350 hingga 550 aksara sahaja.
"""

    prompt_user = "Sila teliti huraian gambar Unsplash di atas dan hasilkan penceritaan harian yang mesra, hidup, dan selari sepenuhnya!"

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt.strip()},
            {"role": "user", "content": prompt_user.strip()}
        ],
        "temperature": 0.85,
        "max_tokens": 500
    }

    url = f"{base_url.rstrip('/')}/chat/completions"

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        response.encoding = 'utf-8'

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
            return False, f"OpenRouter Error (Status {response.status_code}): {response.text}"

    except Exception as e:
        return False, f"Ralat Rangkaian OpenRouter API: {str(e)}"