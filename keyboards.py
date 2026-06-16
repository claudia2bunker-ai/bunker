from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔗 Kanalga ulash", callback_data="connect_channel"),
         InlineKeyboardButton(text="📢 Kanalga qo'shilish", callback_data="join_main_channel")],
        [InlineKeyboardButton(text="🎮 Lobby ochish", callback_data="create_lobby"),
         InlineKeyboardButton(text="👥 Lobbylarni ko'rish", callback_data="view_lobbies")],
        [InlineKeyboardButton(text="📜 Qoidalar", callback_data="rules"),
         InlineKeyboardButton(text="🏆 Reyting", callback_data="rating")],
        [InlineKeyboardButton(text="🛒 Market", callback_data="market"),
         InlineKeyboardButton(text="👤 Profilim", callback_data="profile")],
    ])

def admin_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Karta yaratish", callback_data="admin_create_card")],
        [InlineKeyboardButton(text="📋 Mavjud kartalar", callback_data="admin_view_cards")],
        [InlineKeyboardButton(text="✏️ Kartani tahrirlash", callback_data="admin_edit_card")],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_main")],
    ])

def card_type_keyboard():
    types = [
        ("👮 Kasb", "type_kasb"), ("💪 Salomatlik", "type_salomatlik"),
        ("📖 Biografiya", "type_biografiya"), ("🎯 Hunar", "type_hunar"),
        ("🧬 Genetika", "type_genetika"), ("🧠 Aql", "type_aql"),
        ("❤️ Ijtimoiy", "type_ijtimoiy"), ("🎒 Bagaj", "type_bagaj"),
    ]
    rows = []
    for i in range(0, len(types), 2):
        row = [InlineKeyboardButton(text=types[i][0], callback_data=types[i][1])]
        if i+1 < len(types):
            row.append(InlineKeyboardButton(text=types[i+1][0], callback_data=types[i+1][1]))
        rows.append(row)
    rows.append([InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin_panel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def rules_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🤖 Bot qoidalari", callback_data="rules_bot")],
        [InlineKeyboardButton(text="👮 Kasb qoidalari", callback_data="rules_kasb")],
        [InlineKeyboardButton(text="💪 Salomatlik qoidalari", callback_data="rules_salomatlik")],
        [InlineKeyboardButton(text="🎯 Hunar qoidalari", callback_data="rules_hunar")],
        [InlineKeyboardButton(text="📖 Biografiya qoidalari", callback_data="rules_biografiya")],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_main")],
    ])

def lobbies_keyboard(lobbies):
    rows = []
    for lobby in lobbies:
        rows.append([InlineKeyboardButton(
            text=f"🏠 Lobby #{lobby['id']} | 👤 {lobby.get('player_count',0)}/7",
            callback_data=f"join_lobby_{lobby['id']}"
        )])
    rows.append([InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def lobby_action_keyboard(lobby_id, is_creator=False):
    rows = [[InlineKeyboardButton(text="✅ Qo'shilish", callback_data=f"join_lobby_{lobby_id}")]]
    if is_creator:
        rows.append([InlineKeyboardButton(text="▶️ O'yinni boshlash", callback_data=f"start_game_{lobby_id}")])
    rows.append([InlineKeyboardButton(text="🔙 Orqaga", callback_data="view_lobbies")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def reveal_card_keyboard(lobby_id):
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🃏 Kartamni ochish", callback_data=f"reveal_card_{lobby_id}")
    ]])

def vote_keyboard(lobby_id, players, voter_id):
    rows = []
    for p in players:
        if p["user_id"] != voter_id:
            rows.append([InlineKeyboardButton(
                text=f"☠️ {p['full_name']}",
                callback_data=f"vote_{lobby_id}_{p['user_id']}"
            )])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def market_keyboard(cards, page=0, per_page=8):
    start = page * per_page
    end = start + per_page
    rows = []
    for card in cards[start:end]:
        rows.append([InlineKeyboardButton(
            text=f"{card['emoji']} {card['name']} — {card['price']} BC",
            callback_data=f"buy_card_{card['id']}"
        )])
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="⬅️", callback_data=f"market_page_{page-1}"))
    if end < len(cards):
        nav.append(InlineKeyboardButton(text="➡️", callback_data=f"market_page_{page+1}"))
    if nav:
        rows.append(nav)
    rows.append([InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def confirm_buy_keyboard(card_id):
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Sotib olish", callback_data=f"confirm_buy_{card_id}"),
        InlineKeyboardButton(text="❌ Bekor", callback_data="market"),
    ]])

def back_keyboard(cb):
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🔙 Orqaga", callback_data=cb)
    ]])
