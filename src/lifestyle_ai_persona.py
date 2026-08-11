import json
import re
import random
import requests

LIFESTYLE_THEMES = [
    {
        "category": "GARDEN",
        "topic_name": "POKOK_BUNGA_LAMAN",
        "prompt_guide": "Cerita kelakar & gembira tentang hobi siram pokok bunga di laman rumah, cerita pokok orkid/keladi baru bertunas, atau angin petang yang sepoi-sepoi basah."
    },
    {
        "category": "FOOD_SNACK",
        "topic_name": "RESEPI_MEMORI_KAMPUNG",
        "prompt_guide": "Cerita nostalgia rindu kampung halaman, kenangan makan kuih-muih tradisional dengan arwah nenek/ibu dulu, atau gelagat cuba buat kuih cucur udang garing."
    },
    {
        "category": "COFFEE_TEA",
        "topic_name": "SANTAI_MINUM_PETANG",
        "prompt_guide": "Cerita nikmati kopi/teh panas waktu petang sambil dengar lagu lama, moment rehat sekejap dari rutin harian dengan rasa tenang dan bahagia."
    },
    {
        "category": "LIVING_ROOM",
        "topic_name": "GELAGAT_GELAK_TAWA_KELUARGA",
        "prompt_guide": "Cerita lucu gelagat suami atau anak-anak di rumah (contoh: suami terlupa beli barang dapur, atau anak buat lawak spontan) yang buat Cikgu tersenyum sendiri."
    },
    {
        "category": "NATURE_WINDOW",
        "topic_name": "MOTIVASI_POSITIF_SURIRUMAH",
        "prompt_guide": "Pesanan mesra penuh kasih sayang untuk suri rumah lain supaya hargai diri sendiri, rehat bila penat, jangan stres, dan sentiasa bersyukur dengan rezeki kecik-kecik."
    },
    {
        "category": "FOOD_SNACK",
        "topic_name": "PASAR_PAGI_DAN_RAMAH_MESRA",
        "prompt_guide": "Cerita ceria pegi pasar pagi jumpa jiran-jiran lama, berborak mesra dengan penjual sayur, dan gembira dapat bahan segar untuk masak hari ini."
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
2. DILARANG cerita pasal dapur kemas/peralatan rumah yang nampak seperti iklan.
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

    prompt_user = f"Kategori Tema: {theme['topic_name']}\nPanduan Cerita: {theme['prompt_guide']}"

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

                return True, story_text, theme["category"]

            return False, "Format respon OpenRouter tidak sah.", theme["category"]
        else:
            return False, f"OpenRouter Error (Status {response.status_code}): {response.text}", theme["category"]

    except Exception as e:
        return False, f"Ralat Rangkaian OpenRouter API: {str(e)}", theme["category"]