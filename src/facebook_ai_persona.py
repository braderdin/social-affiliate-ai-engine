import json
import re
import requests

def generate_facebook_caption(base_url, model, api_key, product_title, product_desc):
    """
    Menjana caption promosi & ayat komen AI Persona 'Cikgu Suri Rumah' KHAS UNTUK FACEBOOK PAGE.
    - Watak: Cikgu Suri Rumah Ceria & Penyayang.
    - Sasaran panjang: 600 - 850 aksara (Maksimum Keras: 1000 aksara termasuk hashtag).
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
  3. 3-4 kelebihan utama produk dalam bentuk emoji point.
  4. 1 soalan pancingan komen untuk pengikut (Contoh: "Korang kat rumah ada masalah macam ni jugak tak? Cer komen sikit...").
  5. 3 hingga 5 hashtag tempatan di bahagian paling bawah (Contoh: #CikguSuriRumah #RacunLazada #BaranganDapur #TipsSurirumah).

FORMAT OUTPUT (WAJIB JSON SAHAJA):
Sila pulangkan jawapan dalam format JSON sah tanpa sebarang teks tambahan di luar JSON:
{
  "caption": "Teks post FB lengkap berserta soalan pancingan dan hashtag di bawah...",
  "comment_text": "Ayat komen pendek mesra (1-2 ayat) ajak tekan link. Contoh: Haa ni link yang Cikgu janji tadi ye ibu-ibu, tekan terus kat sini 👉"
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
                    # Fallback jika model gagal memulangkan format JSON
                    caption = cleaned_content
                    comment_text = "Haa ni link produk yang Cikgu cakap tadi ye ibu-ibu, tekan kat sini 👉"

                # Pemotongan keselamatan keras jika caption melebihi 1000 aksara
                if len(caption) > 1000:
                    caption = caption[:997] + "..."

                if not comment_text:
                    comment_text = "Haa ni link produk yang Cikgu cakap tadi ye ibu-ibu, tekan kat sini 👉"

                return True, caption, comment_text

            return False, "Format respons JSON dari OpenRouter tidak sah.", ""
        else:
            return False, f"OpenRouter API Error (Status {response.status_code}): {response.text}", ""

    except Exception as e:
        return False, f"Ralat Rangkaian OpenRouter API: {str(e)}", ""