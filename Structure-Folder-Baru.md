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