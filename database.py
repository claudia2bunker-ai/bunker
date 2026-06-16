import sqlite3
import random

DB_PATH = "bunker.db"

RULES = {
    "🤖 Bot qoidalari": [
        "• Har bir o'yinchi faqat bitta kartaga ega bo'ladi",
        "• O'yin 4-7 kishi bilan boshlanadi",
        "• Ovoz berish 1 daqiqa davom etadi",
        "• Teng ovozda qayta ovoz berish bo'ladi",
        "• Oxirgi 2 kishi g'olib hisoblanadi",
        "• O'yindan chiqarilgan o'yinchi chatda kuzatishi mumkin",
        "• Market kartalarni o'yin davomida ishlatib bo'lmaydi",
    ],
    "👮 Kasb qoidalari": [
        "• Politsiyachi — Kuchli, fidoyi, tartib saqlaydi",
        "• Shifokor — Kasallarni davolaydi, hayot saqlovchi",
        "• Muhandis — Inshootlar quradi, texnik muammolarni hal etadi",
        "• Fermer — Oziq-ovqat yetishtiradi, tirikchilik uchun zarur",
        "• Harbiy — Himoya qiladi, strategiya biladi",
        "• O'qituvchi — Bilim beradi, avlod tarbiyalaydi",
        "• Psixolog — Ruhiy holat boshqaradi",
        "• Oshpaz — Ovqat tayyorlaydi, guruh moralini ko'taradi",
    ],
    "💪 Salomatlik qoidalari": [
        "• A'lo sog'lom — Jismoniy jihatdan to'liq sog'lom",
        "• Surunkali kasallik — Doimiy davolanish kerak",
        "• Nogironlik — Ba'zi cheklovlar mavjud",
        "• Homilador — Maxsus g'amxo'rlik talab qiladi",
        "• Keksa — Tajribali lekin jismoniy imkoniyat cheklangan",
        "• Yosh bola — Kelajak avlod, himoya kerak",
    ],
    "🎯 Hunar qoidalari": [
        "• Qurol ishlatish — Himoya uchun qimmatli",
        "• Meditsina — Yarador va kasallarga yordam",
        "• Qishloq xo'jaligi — Uzoq muddatli ozuqa ta'minoti",
        "• Qurilish — Bunker kengaytirish va ta'mirlash",
        "• Elektr — Energiya va texnologiyani ushlab turish",
        "• Tabiiy fanlar — Ilmiy muammolarni hal etish",
    ],
    "📖 Biografiya qoidalari": [
        "• Yosh (18-30) — Energiya yuqori, tajriba kam",
        "• O'rta yosh (31-50) — Tajriba va kuch muvozanati",
        "• Katta yosh (51+) — Tajriba ko'p, jismoniy imkoniyat kamaygan",
        "• Oilali — Motivatsiya yuqori, mas'uliyat katta",
        "• Yolg'iz — Erkin, faqat o'zini o'ylar",
    ],
}

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_conn()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        full_name TEXT,
        bc_balance INTEGER DEFAULT 0,
        wins INTEGER DEFAULT 0,
        games_played INTEGER DEFAULT 0,
        joined_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS cards (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        card_type TEXT NOT NULL,
        name TEXT NOT NULL,
        description TEXT NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS market_cards (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        description TEXT NOT NULL,
        effect TEXT NOT NULL,
        price INTEGER NOT NULL,
        emoji TEXT NOT NULL
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS user_market_cards (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        market_card_id INTEGER,
        bought_at TEXT DEFAULT CURRENT_TIMESTAMP,
        used INTEGER DEFAULT 0
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS lobbies (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        creator_id INTEGER,
        chat_id INTEGER,
        status TEXT DEFAULT 'waiting',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        scenario TEXT,
        scenario_year TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS lobby_players (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        lobby_id INTEGER,
        user_id INTEGER,
        card_id INTEGER,
        card_revealed INTEGER DEFAULT 0,
        is_alive INTEGER DEFAULT 1,
        joined_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS connected_channels (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        channel_id TEXT,
        channel_name TEXT,
        connected_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')
    conn.commit()
    conn.close()
    print("✅ Database tayyor!")

# ─── USERS ───────────────────────────────────────────────
def get_or_create_user(user_id, username, full_name):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    user = c.fetchone()
    if not user:
        c.execute("INSERT INTO users (user_id, username, full_name) VALUES (?,?,?)",
                  (user_id, username, full_name))
        conn.commit()
        c.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
        user = c.fetchone()
    conn.close()
    return dict(user)

def get_user(user_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    user = c.fetchone()
    conn.close()
    return dict(user) if user else None

def add_bc(user_id, amount):
    conn = get_conn()
    c = conn.cursor()
    c.execute("UPDATE users SET bc_balance=bc_balance+? WHERE user_id=?", (amount, user_id))
    conn.commit()
    conn.close()

def spend_bc(user_id, amount):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT bc_balance FROM users WHERE user_id=?", (user_id,))
    row = c.fetchone()
    if row and row[0] >= amount:
        c.execute("UPDATE users SET bc_balance=bc_balance-? WHERE user_id=?", (amount, user_id))
        conn.commit()
        conn.close()
        return True
    conn.close()
    return False

def update_stats(user_id, won=False):
    conn = get_conn()
    c = conn.cursor()
    if won:
        c.execute("UPDATE users SET games_played=games_played+1, wins=wins+1 WHERE user_id=?", (user_id,))
    else:
        c.execute("UPDATE users SET games_played=games_played+1 WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()

def get_top_users(limit=10):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM users ORDER BY wins DESC, bc_balance DESC LIMIT ?", (limit,))
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]

# ─── CARDS ───────────────────────────────────────────────
def create_card(card_type, name, description):
    conn = get_conn()
    c = conn.cursor()
    c.execute("INSERT INTO cards (card_type, name, description) VALUES (?,?,?)",
              (card_type, name, description))
    conn.commit()
    card_id = c.lastrowid
    conn.close()
    return card_id

def get_recent_cards(limit=10):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM cards ORDER BY id DESC LIMIT ?", (limit,))
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_card_by_id(card_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM cards WHERE id=?", (card_id,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None

def update_card(card_id, card_type=None, name=None, description=None):
    conn = get_conn()
    c = conn.cursor()
    if card_type:
        c.execute("UPDATE cards SET card_type=? WHERE id=?", (card_type, card_id))
    if name:
        c.execute("UPDATE cards SET name=? WHERE id=?", (name, card_id))
    if description:
        c.execute("UPDATE cards SET description=? WHERE id=?", (description, card_id))
    conn.commit()
    conn.close()

def get_random_cards(count):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM cards ORDER BY RANDOM() LIMIT ?", (count,))
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]

# ─── MARKET CARDS ────────────────────────────────────────
def init_market_cards():
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM market_cards")
    count = c.fetchone()[0]
    if count == 0:
        market_cards = [
            ("Ta'sir kartasi", "Birovning ovozini bekor qilish", "cancel_vote", 600, "🗳️"),
            ("Ayg'oqchi kartasi", "Boshqaning kartasini yashirincha ko'rish", "spy", 600, "👁️"),
            ("Almashtirish kartasi", "Kartangni yangi random kartaga almashtirish", "swap_card", 600, "🔄"),
            ("Shifo kartasi", "Salomatlik kartasi zaif bo'lsa kuchaytirish", "heal", 600, "💊"),
            ("Niqob kartasi", "Kartangni boshqalarga yashirish", "mask", 700, "🎭"),
            ("Ovoz kartasi", "Ovozingiz 2x hisoblanadi", "double_vote", 700, "📢"),
            ("Bashorat kartasi", "Voqeadan oldin qo'shimcha karta olish", "prophecy", 700, "🔮"),
            ("Vaqt kartasi", "Ovoz berish vaqtini 30 sekund uzaytirish yoki qisqartirish", "time_control", 700, "⏳"),
            ("Qo'rquv kartasi", "Bitta o'yinchini bir raund ovoz berishdan mahrum qilish", "fear", 1000, "😱"),
            ("Sir kartasi", "Kartangning bir qismini faqat o'zingiz ko'rasiz", "secret", 900, "🤫"),
            ("Qimor kartasi", "50/50 ehtimol bilan birovni o'yindan chiqarish yoki o'zing chiqish", "gamble", 800, "🎲"),
            ("Ittifoq kartasi", "Bitta o'yinchiga ovoz berishda himoya", "alliance", 800, "🤝"),
            ("Maqsad kartasi", "Bitta o'yinchini to'g'ridan ovoz berishga majburlash", "target", 800, "🎯"),
            ("Tez ovoz kartasi", "Ovoz berishda 30 sekund qo'shimcha vaqt olish", "extra_time", 800, "⚡"),
            ("Ikki yuz kartasi", "Boshqa o'yinchiga yashirincha ittifoq taklif qilish", "double_face", 1100, "🕵️"),
            ("Ko'zgu kartasi", "Birovning senga bergan ovozini unga qaytarish", "mirror", 1100, "🪞"),
            ("Sirkachi kartasi", "O'zing haqida yolg'on ma'lumot ko'rsatish imkoni", "clown", 1100, "🎪"),
            ("Manipulyator kartasi", "Chatda bitta xabaringiz barcha tomonidan ishonchli ko'rinadi", "manipulate", 1200, "🧠"),
            ("Xaos kartasi", "Barcha kartalarni random aralashtirish", "chaos", 900, "🌪️"),
            ("Lider kartasi", "Bir raundda ovoz natijasini ko'rish imkoni", "leader", 900, "👑"),
            ("Sudya kartasi", "Sen ovoz bermaysan lekin natijani sen belgilaysan", "judge", 1300, "⚖️"),
            ("Evolyutsiya kartasi", "Kartangni bir daraja kuchaytirish", "evolve", 1000, "🧬"),
            ("Sabotaj kartasi", "Bitta o'yinchining kartasini bir raundga o'chirish", "sabotage", 1000, "💣"),
            ("Legenda kartasi", "Barcha ovozlarda +1 bonus olish butun o'yin davomida", "legend", 1200, "🌟"),
            ("Aktyor kartasi", "Boshqa o'yinchining identifikatsiyasini bir raund uchun olish", "actor", 1600, "🎭"),
            ("Portal kartasi", "O'yindan chiqarilgan o'yinchini qaytarish", "portal", 1500, "🌀"),
            ("Omniscient kartasi", "Barcha o'yinchilarning kartalarini ko'rish", "omniscient", 2000, "👁️‍🗨️"),
            ("Mutatsiya kartasi", "Ikkita kartangni birlashtirib yangi kuchli karta hosil qilish", "mutation", 1800, "🧬"),
            ("Apokalipsis kartasi", "Barcha kartalarni qayta tarqatish butun o'yin boshidan", "apocalypse", 2000, "☢️"),
            ("O'lim kartasi", "Bitta o'yinchini to'g'ridan o'yindan chiqarish ovossiz", "death", 2500, "💀"),
        ]
        c.executemany(
            "INSERT INTO market_cards (name, description, effect, price, emoji) VALUES (?,?,?,?,?)",
            market_cards
        )
        conn.commit()
        print("✅ Market kartalar yuklandi!")
    conn.close()

def get_all_market_cards():
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM market_cards ORDER BY price ASC")
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_market_card(card_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM market_cards WHERE id=?", (card_id,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None

def buy_market_card(user_id, market_card_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("INSERT INTO user_market_cards (user_id, market_card_id) VALUES (?,?)",
              (user_id, market_card_id))
    conn.commit()
    conn.close()

def get_user_market_cards(user_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""SELECT umc.id, mc.name, mc.description, mc.effect, mc.emoji
                 FROM user_market_cards umc
                 JOIN market_cards mc ON umc.market_card_id=mc.id
                 WHERE umc.user_id=? AND umc.used=0""", (user_id,))
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]

# ─── LOBBIES ─────────────────────────────────────────────
def create_lobby(creator_id, chat_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("INSERT INTO lobbies (creator_id, chat_id) VALUES (?,?)", (creator_id, chat_id))
    conn.commit()
    lobby_id = c.lastrowid
    conn.close()
    return lobby_id

def get_lobby(lobby_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM lobbies WHERE id=?", (lobby_id,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None

def get_active_lobbies(chat_id=None):
    conn = get_conn()
    c = conn.cursor()
    if chat_id:
        c.execute("SELECT * FROM lobbies WHERE status='waiting' AND chat_id=? ORDER BY created_at DESC", (chat_id,))
    else:
        c.execute("SELECT * FROM lobbies WHERE status='waiting' ORDER BY created_at DESC")
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def join_lobby(lobby_id, user_id, card_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM lobby_players WHERE lobby_id=? AND user_id=?", (lobby_id, user_id))
    if c.fetchone():
        conn.close()
        return False
    c.execute("INSERT INTO lobby_players (lobby_id, user_id, card_id) VALUES (?,?,?)",
              (lobby_id, user_id, card_id))
    conn.commit()
    conn.close()
    return True

def get_lobby_players(lobby_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""SELECT lp.*, u.full_name, u.username,
                        ca.name as card_name, ca.description as card_desc, ca.card_type
                 FROM lobby_players lp
                 JOIN users u ON lp.user_id=u.user_id
                 JOIN cards ca ON lp.card_id=ca.id
                 WHERE lp.lobby_id=? AND lp.is_alive=1""", (lobby_id,))
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def update_lobby_status(lobby_id, status, scenario=None, year=None):
    conn = get_conn()
    c = conn.cursor()
    if scenario and year:
        c.execute("UPDATE lobbies SET status=?, scenario=?, scenario_year=? WHERE id=?",
                  (status, scenario, year, lobby_id))
    else:
        c.execute("UPDATE lobbies SET status=? WHERE id=?", (status, lobby_id))
    conn.commit()
    conn.close()

def reveal_card(lobby_id, user_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("UPDATE lobby_players SET card_revealed=1 WHERE lobby_id=? AND user_id=?",
              (lobby_id, user_id))
    conn.commit()
    conn.close()

def eliminate_player(lobby_id, user_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("UPDATE lobby_players SET is_alive=0 WHERE lobby_id=? AND user_id=?",
              (lobby_id, user_id))
    conn.commit()
    conn.close()

def count_alive_players(lobby_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM lobby_players WHERE lobby_id=? AND is_alive=1", (lobby_id,))
    count = c.fetchone()[0]
    conn.close()
    return count

def get_lobby_player_count(lobby_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM lobby_players WHERE lobby_id=?", (lobby_id,))
    count = c.fetchone()[0]
    conn.close()
    return count

# ─── CHANNELS ────────────────────────────────────────────
def connect_channel(user_id, channel_id, channel_name):
    conn = get_conn()
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO connected_channels (user_id, channel_id, channel_name) VALUES (?,?,?)",
              (user_id, channel_id, channel_name))
    conn.commit()
    conn.close()

def get_user_channels(user_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM connected_channels WHERE user_id=?", (user_id,))
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]
