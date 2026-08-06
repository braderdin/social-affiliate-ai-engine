# STRUKTUR PROJEK: SOCIAL AFFILIATE AI ENGINE

```text
social-affiliate-ai-engine/
├── .agents/                      # Konfigurasi dan kemahiran ejen AI
│   └── skills/
│       └── SKILL.MD              # Dokumen skil & rujukan rasmi Lazada API
├── .github/                      # Workflow GitHub Actions untuk automasi
│   └── workflows/
│       └── run_ai_persona.yml    # Skrip automasi jadual GitHub Actions
├── .Master_Plan/                 # Pelan induk dan dokumentasi seni bina projek
├── bin/                          # Skrip ujian diagnostik & pemicu pipeline
│   ├── run_pipeline.py           # Skrip utama (Full Automation Pipeline)
│   ├── test_ai_persona.py        # Ujian modul AI Persona
│   ├── test_ai.py                # Ujian asas sambungan OpenRouter AI
│   ├── test_lazada_link.py       # Ujian khas Lazada API Feed & Tracking Link (100% Real Data)
│   ├── test_lazada.py            # Ujian asas Lazada API
│   └── test_telegram.py          # Ujian hantaran Telegram Bot
├── src/                          # Modul teras projek (Core Modules)
│   ├── ai_persona.py             # Modul penjanaan kapsyen AI OpenRouter
│   ├── lazada_api.py             # Modul rasmi panggilan Lazada Open API
│   ├── redis_db.py               # Modul Upstash Redis (Semakan Duplikasi Produk)
│   └── telegram_bot.py           # Modul hantaran foto & kapsyen Telegram Bot
├── venv/                         # Virtual environment Python
├── .clinerules                   # Peraturan dan tetapan sistem Cliners
├── .env.example                  # Templat rujukan pemboleh ubah persekitaran (RUJUKAN-UTAMA)
├── .env.local                    # Fail kunci rahsia tempatan (Kunci API Sebenar)
├── .gitignore                    # Senarai fail diabaikan oleh Git
├── README.md                     # Panduan penggunaan projek
├── requirements.txt              # Senarai pakej/library Python
└── Structure-Folder-Baru.md      # Fail dokumentasi struktur folder terkini


ALIRAN KERJA AUTOMASI ENGINE (4-LANGKAH)

[LANGKAH 1: Ambil Data Produk Real]
  └── Panggil REST API: /marketing/product/feed
      ├── Parameter: offerType=1, userToken=xxx, limit=20, page=1
      └── Hasil: Mendapatkan 'productId', 'productName', dan URL 'pictures'

[LANGKAH 2: Jana Link Affiliate Sebenar]
  └── Panggil REST API: /marketing/product/link (Fallback: /marketing/getlink)
      ├── Parameter: userToken=xxx, productId=<productId_dari_Langkah_1>
      └── Hasil: Mendapatkan 'trackingLink' rasmi

[LANGKAH 3: Penjanaan Ayat AI Persona]
  └── Hantar 'productName' ke OpenRouter AI
      └── Hasil: Ayat promosi dinamik (Persona Cikgu/Surirumah)

[LANGKAH 4: Penghantaran ke Telegram]
  └── Hantar 'pictures' (Imej Binary) + 'Ayat AI' + 'trackingLink' ke Telegram Bot


[Data Real Lazada] ──> [OpenRouter AI Engine] ──> [Telegram Bot API]
 (Tajuk + Gambar +      (Jana Ayat Persona        (Muat Turun Gambar
   Affiliate Link)        Cikgu/Surirumah)          ke Memori & Post)

Gabungan Upstash Redis, Upstash Vector, dan Penapis Harga menetapkan kawalan tiga lapisan (3-layer guardrail) untuk memastikan setiap produk yang disiarkan ke Telegram sentiasa berharga munasabah (RM 10.00 hingga RM 500.00), tiada pengulangan item yang sama dalam tempoh 7 hari, dan tiada kebosanan kategori yang serupa dalam tempoh 2 hari.1. Pembahagian Peranan & FungsiKomponenPeranan UtamaCara Kerja TeknikalTempoh KawalanPenapis Harga (Price Guard)Menapis harga gila/palsu (contoh: RM 99,994)Menyemak medan discountPrice / price dari Lazada Feed APISerta-merta (RM 10 – RM 500)Upstash RedisMengelakkan produk tepat yang sama disiar berulangMenyimpan productId dengan kunci TTL (Time-To-Live)7 Hari (604,800 saat)Upstash VectorMengelakkan produk berbeza tetapi makna/fungsi serupaMencari keserupaan skrip/teks (Cosine Similarity) guna text-embedding-3-small2 Hari (172,800 saat)2. Struktur Kerja & Logik Keputusan (Step-by-Step Flow)Apabila run_pipeline.py dijalankan, ia akan memproses setiap produk dari Lazada Feed mengikut urutan logik berikut:


[Lazada API Feed]
       │
       ▼
[LAPISAN 1: Semakan Harga Munasabah]
       ├── Adakah Harga < RM 10.00 ATAU > RM 500.00?
       │     ├── YA  ──> ❌ (Langkau Produk, Cari Item Seterusnya)
       │     └── TIDAK ─> 🟢 (Lulus Lapisan 1)
       ▼
[LAPISAN 2: Semakan Redis - Produk Tepat]
       ├── Adakah `posted:product:<productId>` Wujud dalam Redis?
       │     ├── YA  ──> ❌ (Telah disiar dalam 7 hari lepas -> Langkau)
       │     └── TIDAK ─> 🟢 (Lulus Lapisan 2)
       ▼
[LAPISAN 3: Semakan Upstash Vector - Makna/Fungsi Serupa]
       ├── Hasilkan Vector Embedding dari (Tajuk + Kategori)
       ├── Cari dalam Vector DB: Adakah wujud item serupa (Skor > 0.85) dalam masa < 48 jam?
       │     ├── YA  ──> ❌ (Kategori/Fungsi terlalu serupa -> Langkau)
       │     └── TIDAK ─> 🟢 (Lulus Lapisan 3)
       ▼
[Jana AI Caption] ──> [Post ke Telegram]
       │
       ▼
[KINI REKOD DATA BAHARU]
  ├── 1. Redis: Simpan key `posted:product:<productId>` dengan TTL = 7 Hari
  └── 2. Vector DB: Simpan Embedding + Metadata (productId, timestamp, tajuk)


3. Perincian Pelaksanaan Logik
Lapisan 1: Penapis Harga Munasabah (Price Filter)
Punca harga RM 99,994.00 keluar sebelum ini adalah kerana sesetengah penjual menetapkan harga stok akaun/ujicuba di Lazada. Penapis ini diletakkan pada peringkat awal pengambilan data:


# Logik Penapis Harga
price = float(product.get("discountPrice") or product.get("price") or 0)

if price < 10.0 or price > 500.0:
    print(f"⏩ [PRICE FILTER] Harga RM {price:.2f} di luar julat (RM 10 - RM 500). Langkau.")
    continue


Lapisan 2: Upstash Redis (Had 7 Hari Produk Tepat)
Mengelakkan Cetaphil PRO AD Derma 29ml dengan ID 14950556095 yang sama dipost semula sebelum 7 hari.

Format Kunci Redis: posted:product:14950556095

Masa Luput (TTL): 604800 saat (7 hari).

Cara Kerja:

Sebelum post: Panggil redis.get("posted:product:14950556095"). Jika bernilai 1, langkau.

Selepas post: Panggil redis.set("posted:product:14950556095", "1", ex=604800).

Selepas 7 hari, Redis akan memadam kunci ini secara automatik, membolehkan produk dipromosikan semula jika masih hangat.

Lapisan 3: Upstash Vector (Had 2 Hari Makna Serupa)
Mengelakkan situasi di mana hari ini dipost Lotion Cetaphil, dan esok dipost Lotion Sebamed (produk berbeza ID, tetapi tergolong dalam fungsi/makna yang sama iaitu Lotion/Moisturizer Kulit Sensitif).

Model Embedding: Dense -> text-embedding-3-small (1536 dimensi).

Teks Dihantar ke Vector: Cetaphil PRO AD Derma Moisture Lotion Kulit Sensitif

Cara Kerja:

Hantar teks produk ke Upstash Vector untuk carian keserupaan (Vector Query).

Jika jumpa item terdekat dengan skor keserupaan Cosine Similarity > 0.85:

Semak cap masa (timestamp) item tersebut dari metadata.

Jika perbezaan masa Masa Semasa - Masa Dihantar < 172,800 saat (2 hari), langkau produk tersebut.

Jika lulus, hantar ke Telegram dan simpan vector baharu ke Upstash Vector bersama metadata:

{
  "id": "14950556095",
  "posted_at": 1786000000,
  "title": "CETAPHIL PRO AD DERMA MOISTURE"
}


