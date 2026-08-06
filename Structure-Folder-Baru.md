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