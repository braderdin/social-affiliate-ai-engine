social-affiliate-ai-engine/
├── .env.local
├── requirements.txt
├── src/
│   ├── __init__.py
│   ├── telegram_bot.py   # Modul khas Telegram
│   ├── ai_persona.py     # Modul khas AI OpenRouter
│   ├── lazada_api.py     # Modul khas Lazada API
│   └── redis_db.py       # Modul khas Upstash Redis (Deduplication)
└── bin/
    ├── test_telegram.py   # Uji Telegram sahaja
    ├── test_ai.py         # Uji AI sahaja
    ├── test_lazada.py     # Uji Lazada API sahaja
    └── run_pipeline.py    # Skrip utama (Gabungan semua)





    [LANGKAH 1: Ambil Data Produk]
  └── Panggil REST API: /marketing/product/feed
      ├── Parameter: offerType=1, userToken=xxx, limit=1, page=1
      └── Hasil: Mendapatkan 'productId', 'productName', dan URL 'pictures'

[LANGKAH 2: Jana Link Affiliate Sebenar]
  └── Panggil REST API: /marketing/product/link
      ├── Parameter: userToken=xxx, productId=<productId_dari_Langkah_1>
      └── Hasil: Mendapatkan 'trackingLink' rasmi

[LANGKAH 3: Penjanaan Ayat AI Persona]
  └── Hantar 'productName' ke OpenRouter AI
      └── Hasil: Ayat promosi dinamik (Persona Cikgu/Surirumah)

[LANGKAH 4: Penghantaran ke Telegram]
  └── Hantar 'pictures' (Imej Binary) + 'Ayat AI' + 'trackingLink' ke Telegram Bot





  