# ☢️ BUNKER BOT

Telegram uchun to'liq Bunker o'yin boti.

## O'rnatish

### 1. Kerakli kutubxonalarni o'rnating:
```bash
pip install -r requirements.txt
```

### 2. `.env` faylini yarating:
```bash
cp .env.example .env
```

### 3. `.env` faylini tahrirlang:
```
BOT_TOKEN=siz_bot_token
ADMIN_ID=siz_telegram_id
GROK_API_KEY=siz_grok_api_key
```

### 4. Botni ishga tushiring:
```bash
python bot.py
```

---

## Funksiyalar

### Foydalanuvchi paneli:
- 🔗 Kanalga ulash
- 📢 Asosiy kanalga qo'shilish
- 🎮 Lobby ochish
- 👥 Lobbylarni ko'rish
- 📜 Qoidalar (kategoriyalar bo'yicha)
- 🏆 Reyting
- 🛒 Market (30 ta maxsus karta)
- 👤 Profil

### Admin paneli (/admin):
- ➕ Karta yaratish
- 📋 Mavjud kartalar (oxirgi 10 ta)
- ✏️ Kartani tahrirlash

### O'yin mexanikasi:
- 4-7 o'yinchi
- Random voqea va yil
- Karta ochish bosqichi
- 1 daqiqa muhokama
- 1 daqiqa ovoz berish
- Teng ovozda qayta ovoz
- 2 g'olib qolguncha
- Grok AI tahlili
- BC mukofot tizimi

### BC mukofotlar:
- Yutqazsa: +10 BC
- G'olib: +50-100 BC

### Market (30 ta karta, 600-2500 BC):
- Ta'sir kartasi, Ayg'oqchi, Almashtirish...
- O'lim kartasi, Apokalipsis, Omniscient va boshqalar

---

## Fayl strukturasi:
```
bunker_bot/
├── bot.py          # Asosiy bot fayli
├── database.py     # SQLite ma'lumotlar bazasi
├── game.py         # O'yin mexanikasi
├── grok_ai.py      # Grok AI integratsiya
├── keyboards.py    # Tugmalar
├── requirements.txt
├── .env.example
└── README.md
```
