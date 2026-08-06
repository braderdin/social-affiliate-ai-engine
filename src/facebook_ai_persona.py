import json
import re
import requests

def remove_emojis_and_special_symbols(text):
    """
    Membuang semua emoji, simbol bullet khas (❖, ◆, ◇, •, ), 
    dan mengekalkan teks Bahasa Melayu serta tanda baca standard sahaja.
    """
    if not text:
        return ""
    
    # 1. Gantikan simbol bullet khas dengan tanda sempang biasa (-)
    special_bullets = ["❖", "◆", "◇", "►", "•", "▪", "▲", "★"]
    for sym in special_bullets:
        text = text.replace(sym, "-")
        
    # 2. Buang simbol replacement character 
    text = text.replace("", "")
    
    # 3. Buang semua aksara Unicode 4-byte (Emoji)
    emoji_pattern = re.compile(
        "["
        "\U0001f600-\U0001f64f"  # emoticons
        "\U0001f300-\U0001f5ff"  # symbols & pictographs
        "\U0001f680-\U0001f6ff"  # transport & map symbols
        "\U0001f1e0-\U0001f1ff"  # flags (iOS)
        "\U00002702-\U000027b0"
        "\U000024c2-\U000025ca"
        "\U0001f900-\U0001f9ff"  # Supplemental Symbols and Pictographs
        "\U0001fa70-\U0001faff"  # Symbols and Pictographs Extended-A
        "]+", 
        flags=re.UNICODE
    )
    text = emoji_pattern.sub("", text)
    
    # 4. Bersihkan ruang kosong berlebihan
    lines = [line.strip() for line in text.splitlines()]
    return "\n".join(lines).strip()

def generate_facebook_caption(base_url, model, api_key, product_title, product_desc):
    """
    Menjana caption promosi & ayat komen AI Persona 'Cikgu Suri Rumah' KHAS UNTUK FACEBOOK PAGE.
    - Watak: Cikgu Suri Rumah Ceria & Penyayang.
    - Format: TEKS BERSIH STANDARD (100% Tanpa Emoji & Tanpa Simbol Khas).
    - Bahasa Melayu santai FB Malaysia (100% Bebas Bahasa Indonesia).
    - Memulangkan: (success_bool, caption, comment_text)
    """
    if not base_url or not model or not api_key:
        return False, "Kunci OpenRouter API / Base URL / Model tidak lengkap.", ""

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json; charset=utf-8"
    }

    system_prompt = """
Anda ialah 'Cikgu Suri Rumah', seorang bekas guru yang kini menjadi suri rumah sepenuh masa. Anda seorang yang sangat ceria, ramah, penyayang, dan suka berkongsi tips serta barangan dapur/rumah idaman di Facebook.

ARAHAN FORMAT TEKS BERSIH (STRICT ZERO-EMOJI POLICY):
1. DILARANG SAMA SEKALI menggunakan sebarang emoji (contoh: TIDAK BOLEH guna 😊, ❤️, 👍, ✨, 🌸, 📌, 👉).
2. DILARANG SAMA SEKALI menggunakan simbol bullet khas (contoh: TIDAK BOLEH guna ❖, ◆, ◇, •, ►).
3. Untuk senarai kelebihan produk, WAJIB guna tanda sempang biasa sahaja (Contoh: - Kelebihan 1).
4. Sampaikan keceriaan dan nada mesra Cikgu menggunakan perkataan dan tanda baca biasa (! dan ?).

WATAK & GAYA BAHASA (STRICT MALAYSIAN TEACHER & SURIRUMAH FB STYLE):
1. Gunakan nada seorang Cikgu yang mesra, kelakar, dan ceria. Suka menyapa pengikut dengan panggilan mesra seperti "Ibu-ibu sekalian", "Anak-anak murid Cikgu", atau "Suri rumah tersayang".
2. Selitkan elemen Cikgu secara santai (Contoh: "Haa harini Cikgu nak bagi nota penting...", "Nah Cikgu bagi ganjaran barang best...", "Geram betul Cikgu tengok benda ni!").
3. WAJIB guna Bahasa Melayu santai media sosial Malaysia.
4. DILARANG SAMA SEKALI guna Bahasa Indonesia. (Haramkan perkataan: "bisa", "banget", "nggak", "solusi", "ibu rumah tangga", "yuk", "sih", "efisien", "pasti jimat").

HAD PANJANG TEKS & STRUKTUR CAPTION:
- Jumlah keseluruhan aksara WAJIB BAWAH 900 AKSARA (termasuk hashtag).
- STRUKTUR CAPTION:
  1. Hook mesra watak Cikgu (1-2 ayat).
  2. Masalah dapur/rumah & bagaimana produk ini membantu (2-3 ayat ringkas).
  3. 3-4 kelebihan utama produk dalam bentuk senarai sempang biasa (- Kelebihan).
  4. 1 soalan pancingan komen untuk pengikut (Contoh: "Korang kat rumah ada masalah macam ni jugak tak? Cer komen sikit...").
  5. 3 hingga 5 hashtag tempatan di bahagian paling bawah (Contoh: #CikguSuriRumah #RacunLazada #BaranganDapur #TipsSurirumah).

FORMAT OUTPUT (WAJIB JSON SAHAJA):
Sila pulangkan jawapan dalam format JSON sah tanpa sebarang teks tambahan di luar JSON:
{
  "caption": "Teks post FB lengkap tanpa emoji, berserta soalan pancingan dan hashtag di bawah...",
  "comment_text": "Ayat komen pendek mesra (1-2 ayat) ajak tekan link tanpa emoji. Contoh: Haa ni link yang Cikgu janji tadi ye ibu-ibu, tekan terus kat sini"
}

ARAHAN KETAT (NEGATIVE CONSTRAINTS):
- DILARANG meletakkan sebarang pautan URL/link di dalam "caption" mahupun "comment_text".
- Hanya pulangkan format JSON yang sah.
"""

    prompt_user = f"Nama Produk: {product_title}\nDeskripsi Produk: {product_desc}"

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt.strip()},
            {"role": "user", "content": prompt_user.strip()}
        ],
        "temperature": 0.7,
        "max_tokens": 800
    }

    url = f"{base_url.rstrip('/')}/chat/completions"

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        response.encoding = 'utf-8'

        if response.status_code == 200:
            res_json = response.json()
            if "choices" in res_json and len(res_json["choices"]) > 0:
                raw_content = res_json["choices"][0]["message"]["content"].strip()

                # Bersihkan sintaks markdown codeblock jika ada
                cleaned_content = re.sub(r"^```(?:json)?\s*", "", raw_content, flags=re.MULTILINE)
                cleaned_content = re.sub(r"\s*```$", "", cleaned_content, flags=re.MULTILINE).strip()

                try:
                    parsed_json = json.loads(cleaned_content)
                    caption = parsed_json.get("caption", "").strip()
                    comment_text = parsed_json.get("comment_text", "").strip()
                except json.JSONDecodeError:
                    caption = cleaned_content
                    comment_text = "Haa ni link produk yang Cikgu cakap tadi ye ibu-ibu, tekan kat sini"

                # Pembersihan Keras Emojis & Simbol Khas
                caption = remove_emojis_and_special_symbols(caption)
                comment_text = remove_emojis_and_special_symbols(comment_text)

                # Pemotongan keselamatan keras jika caption melebihi 1000 aksara
                if len(caption) > 1000:
                    caption = caption[:997] + "..."

                if not comment_text:
                    comment_text = "Haa ni link produk yang Cikgu cakap tadi ye ibu-ibu, tekan kat sini"

                return True, caption, comment_text

            return False, "Format respons JSON dari OpenRouter tidak sah.", ""
        else:
            return False, f"OpenRouter API Error (Status {response.status_code}): {response.text}", ""

    except Exception as e:
        return False, f"Ralat Rangkaian OpenRouter API: {str(e)}", ""