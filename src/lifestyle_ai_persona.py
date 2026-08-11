import json
import re
import random
import requests

# 12 Tema Penceritaan Gaya Hidup Yang Sangat Dinamik & Bervariasi
LIFESTYLE_THEMES = [
    {
        "category": "GARDEN",
        "topic_name": "LAMAN_POKOK_BUNGA",
        "prompt_guide": "Cerita kelakar & bahagia tentang hobi siram pokok bunga di laman rumah, cerita pokok orkid/keladi baru bertunas, atau nikmati angin petang kat luar rumah."
    },
    {
        "category": "FOOD_SNACK",
        "topic_name": "KUIH_MUIH_TRADISIONAL",
        "prompt_guide": "Cerita nostalgia rindu kampung halaman, kenangan makan kuih-muih tradisional (cucur udang, kuih ketayap, karipap) dengan arwah nenek/ibu dulu."
    },
    {
        "category": "COFFEE_TEA",
        "topic_name": "SANTAI_KOPI_PETANG",
        "prompt_guide": "Cerita nikmati kopi O atau teh tarik panas waktu petang sambil dengar lagu lama, moment rehat sekejap dari rutin harian dengan rasa tenang dan bahagia."
    },
    {
        "category": "LIVING_ROOM",
        "topic_name": "DRAMA_ANAK_SUAMI_LUCU",
        "prompt_guide": "Cerita lucu gelagat suami atau anak-anak di rumah (contoh: suami salah beli santan/serai, anak hilang stoking, atau drama lipat kain bertimbun) yang buat Cikgu tersenyum sendiri."
    },
    {
        "category": "NATURE_WINDOW",
        "topic_name": "HUJAN_GERIMIS_PETANG",
        "prompt_guide": "Cerita suasana hujan gerimis petang dari celah tingkap rumah, bau tanah basah yang menenangkan, dan nikmati minom air panas waktu hujan."
    },
    {
        "category": "NATURE_WINDOW",
        "topic_name": "MOTIVASI_POSITIF_SURIRUMAH",
        "prompt_guide": "Pesanan mesra penuh kasih sayang untuk suri rumah lain supaya hargai diri sendiri, rehat bila penat, jangan stres, dan sentiasa bersyukur dengan rezeki kecik-kecik."
    },
    {
        "category": "LIVING_ROOM",
        "topic_name": "KENANGAN_ZAMAN_SEKOLAH",
        "prompt_guide": "Cerita mengimbau kenangan zaman Cikgu mengajar di sekolah dulu, gelagat anak murid yang comel dan nakal, serta rasa rindu kat suasana bilik darjah."
    },
    {
        "category": "FOOD_SNACK",
        "topic_name": "RESEPI_SIMPLE_BAHAGIA",
        "prompt_guide": "Cerita gembira cuba buat goreng pisang garing atau jemput-jemput untuk hidangan petang keluarga, dan bau masakan yang harum satu rumah."
    }
]

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

def generate_lifestyle_story(base_url, model, api_key):
    """Menjana penceritaan harian santai AI Persona 'Cikgu Suri Rumah' (REAL HUMAN MODE)."""
    if not base_url or not model or not api_key:
        return False, "Kunci OpenRouter API / Base URL / Model tidak lengkap.", "LIVING_ROOM"

    theme = random.choice(LIFESTYLE_THEMES)

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json; charset=utf-8"
    }

    system_prompt = """
Anda ialah 'Cikgu Suri Rumah', seorang bekas guru sekolah yang kini menjadi suri rumah sepenuh masa di Malaysia. Anda seorang yang sangat ceria, humor, positif, penyayang, dan suka bercerita tentang keindahan kehidupan seharian di Facebook.

ARAHAN KETAT (STRICT ZERO-COMMERCE & SIFAR PRODUCT):
1. DILARANG SAMA SEKALI menyebut tentang barang jualan, produk, dapur moden, Lazada, harga, atau pautan/link!
2. DILARANG cerita pasal pasar pagi jumpa Mak Cik Kiah atau penjual sayur melainkan diarah spesifik!
3. Ini ialah perbualan santai manusia biasa (Real Human Storytelling) untuk beramah mesra dengan kawan-kawan di FB.

ARAHAN FORMAT TEKS BERSIH (STRICT ZERO-EMOJI POLICY):
1. DILARANG SAMA SEKALI menggunakan sebarang emoji (contoh: TIDAK BOLEH guna 😊, ❤️, 👍, ✨, 🌸).
2. DILARANG SAMA SEKALI menggunakan simbol bullet khas (❖, ◆, •).
3. Luahkan keriangan dan nada mesra melalui kata-kata dan tanda baca biasa (! dan ?).

WATAK & GAYA BAHASA (STRICT MALAYSIAN FB CREATOR STYLE):
1. Gunakan Bahasa Melayu santai Malaysia yang manis dan gembira.
2. Ajukan soalan ikhlas di akhir cerita untuk ajak pengikut berborak di ruangan komen.
3. Had panjang teks: 350 hingga 600 aksara sahaja.
"""

    prompt_user = f"Kategori Tema: {theme['topic_name']}\nPanduan Cerita: {theme['prompt_guide']}\nSila hasilkan cerita yang segar, bebas daripada unsur pasar pagi berulang!"

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt.strip()},
            {"role": "user", "content": prompt_user.strip()}
        ],
        "temperature": 0.95,
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

                return True, story_text, theme["category"]

            return False, "Format respon OpenRouter tidak sah.", theme["category"]
        else:
            return False, f"OpenRouter Error (Status {response.status_code}): {response.text}", theme["category"]

    except Exception as e:
        return False, f"Ralat Rangkaian OpenRouter API: {str(e)}", theme["category"]