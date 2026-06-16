import os
import asyncio
import random
import logging
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, BotCommand
from aiogram.types import BotCommandScopeDefault, BotCommandScopeAllPrivateChats, BotCommandScopeAllGroupChats
from aiogram.filters import CommandStart, Command
from aiogram.fsm.storage.memory import MemoryStorage

load_dotenv()
logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
MAIN_CHANNEL = "https://t.me/+Ypej9hA5AC8wNTQy"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

from database import *
from game import *
from grok_ai import analyze_winners, get_scenario_description
from keyboards import *

user_states = {}

# ═══════════════════════════════════════════════════════════
# PRIVATE COMMANDALAR
# ═══════════════════════════════════════════════════════════

@dp.message(CommandStart())
async def start(msg: Message):
    user = get_or_create_user(msg.from_user.id, msg.from_user.username or "", msg.from_user.full_name)
    await msg.answer(
        f"☢️ <b>BUNKER</b> ga xush kelibsiz, {msg.from_user.first_name}!\n\n"
        f"Apokalipsis boshlanmoqda. Bunkerda joy cheklangan.\n"
        f"Faqat eng loyiqlari omon qoladi...\n\n"
        f"💰 BC: {user['bc_balance']}",
        parse_mode="HTML",
        reply_markup=main_menu()
    )

@dp.message(Command("admin"))
async def admin_cmd(msg: Message):
    if msg.from_user.id != ADMIN_ID:
        await msg.answer("❌ Ruxsat yo'q!")
        return
    await msg.answer("🔧 Admin paneli:", reply_markup=admin_menu())

@dp.message(Command("help"))
async def cmd_help(msg: Message):
    if msg.chat.type == "private":
        await msg.answer(
            "🤖 <b>Bunker Bot yordam</b>\n\n"
            "Guruhda o'yin o'ynash uchun botni guruhga qo'shing va:\n\n"
            "/newgame — yangi o'yin boshlash\n"
            "/join — o'yinga qo'shilish\n"
            "/players — o'yinchilar ro'yxati\n"
            "/start_game — o'yinni boshlash\n"
            "/stop — o'yinni bekor qilish\n\n"
            "Private botda:\n"
            "🛒 Market, 🏆 Reyting, 👤 Profil va boshqalar",
            parse_mode="HTML",
            reply_markup=main_menu()
        )
    else:
        await msg.answer(
            "🤖 <b>Bunker Bot buyruqlari:</b>\n\n"
            "/newgame — yangi o'yin boshlash\n"
            "/join — o'yinga qo'shilish\n"
            "/players — o'yinchilar ro'yxati\n"
            "/start_game — o'yinni boshlash (yaratuvchi)\n"
            "/stop — o'yinni bekor qilish",
            parse_mode="HTML"
        )

# ═══════════════════════════════════════════════════════════
# GURUH COMMANDALARI
# ═══════════════════════════════════════════════════════════

@dp.message(Command("newgame"))
async def cmd_newgame(msg: Message):
    if msg.chat.type == "private":
        await msg.answer("❌ Bu buyruq faqat guruh yoki kanalda ishlaydi!")
        return
    cards = get_recent_cards(50)
    if not cards:
        await msg.answer("❌ Hali kartalar yo'q! Admin avval karta yaratsin.")
        return
    existing = [l for l in get_active_lobbies() if l["chat_id"] == msg.chat.id]
    if existing:
        await msg.answer(
            f"❌ Bu guruhda allaqachon ochiq lobby bor! #{existing[0]['id']}\n"
            f"Qo'shilish: /join\n"
            f"O'yinchilar: /players"
        )
        return
    get_or_create_user(msg.from_user.id, msg.from_user.username or "", msg.from_user.full_name)
    lobby_id = create_lobby(msg.from_user.id, msg.chat.id)
    rc = random.choice(cards)
    join_lobby(lobby_id, msg.from_user.id, rc["id"])
    await msg.answer(
        f"🏠 <b>Yangi Bunker o'yini #{lobby_id}!</b>\n\n"
        f"👤 Yaratuvchi: {msg.from_user.full_name}\n"
        f"👥 O'yinchilar: 1/7 (minimum 4)\n\n"
        f"▶️ Qo'shilish: /join\n"
        f"👁 O'yinchilar: /players\n"
        f"🚀 Boshlash: /start_game\n"
        f"🛑 Bekor qilish: /stop",
        parse_mode="HTML"
    )

@dp.message(Command("join"))
async def cmd_join(msg: Message):
    if msg.chat.type == "private":
        await msg.answer("❌ Bu buyruq faqat guruh yoki kanalda ishlaydi!")
        return
    lobbies = [l for l in get_active_lobbies() if l["chat_id"] == msg.chat.id]
    if not lobbies:
        await msg.answer("❌ Bu guruhda ochiq lobby yo'q!\nYangi o'yin: /newgame")
        return
    lobby = lobbies[0]
    lobby_id = lobby["id"]
    if get_lobby_player_count(lobby_id) >= 7:
        await msg.answer("❌ Lobby to'ldi! (max 7 kishi)")
        return
    get_or_create_user(msg.from_user.id, msg.from_user.username or "", msg.from_user.full_name)
    if is_in_lobby(lobby_id, msg.from_user.id):
        await msg.answer(f"❌ {msg.from_user.first_name}, siz allaqachon lobbydasiz!")
        return
    cards = get_recent_cards(50)
    if not cards:
        await msg.answer("❌ Kartalar yo'q!")
        return
    rc = random.choice(cards)
    join_lobby(lobby_id, msg.from_user.id, rc["id"])
    count = get_lobby_player_count(lobby_id)
    await msg.answer(
        f"✅ <b>{msg.from_user.full_name}</b> lobbyga qo'shildi!\n"
        f"👥 O'yinchilar: {count}/7",
        parse_mode="HTML"
    )

@dp.message(Command("leave"))
async def cmd_leave(msg: Message):
    if msg.chat.type == "private":
        await msg.answer("❌ Bu buyruq faqat guruhda ishlaydi!")
        return
    lobbies = [l for l in get_active_lobbies() if l["chat_id"] == msg.chat.id]
    if not lobbies:
        await msg.answer("❌ Ochiq lobby yo'q!")
        return
    lobby = lobbies[0]
    lobby_id = lobby["id"]
    if lobby["creator_id"] == msg.from_user.id:
        await msg.answer("❌ Yaratuvchi lobbyni tark eta olmaydi!\nO'yinni bekor qilish: /stop")
        return
    if leave_lobby(lobby_id, msg.from_user.id):
        count = get_lobby_player_count(lobby_id)
        await msg.answer(
            f"🚪 <b>{msg.from_user.full_name}</b> lobbydan chiqdi.\n"
            f"👥 Qolgan o'yinchilar: {count}/7",
            parse_mode="HTML"
        )
    else:
        await msg.answer("❌ Siz bu lobbyda emassiz!")

@dp.message(Command("players"))
async def cmd_players(msg: Message):
    if msg.chat.type == "private":
        await msg.answer("❌ Bu buyruq faqat guruhda ishlaydi!")
        return
    lobbies = [l for l in get_active_lobbies() if l["chat_id"] == msg.chat.id]
    if not lobbies:
        await msg.answer("❌ Ochiq lobby yo'q!")
        return
    lobby_id = lobbies[0]["id"]
    players = get_lobby_players(lobby_id)
    if not players:
        await msg.answer("👥 Hali hech kim qo'shilmagan!")
        return
    text = f"👥 <b>Lobby #{lobby_id} o'yinchilari ({len(players)}/7):</b>\n\n"
    for i, p in enumerate(players, 1):
        text += f"{i}. {p['full_name']}\n"
    needed = max(0, 4 - len(players))
    if needed > 0:
        text += f"\n⏳ Yana {needed} kishi kerak"
    else:
        text += f"\n✅ O'yinni boshlash mumkin! /start_game"
    await msg.answer(text, parse_mode="HTML")

@dp.message(Command("start_game"))
async def cmd_start_game(msg: Message):
    if msg.chat.type == "private":
        await msg.answer("❌ Bu buyruq faqat guruhda ishlaydi!")
        return
    lobbies = [l for l in get_active_lobbies() if l["chat_id"] == msg.chat.id]
    if not lobbies:
        await msg.answer("❌ Ochiq lobby yo'q! /newgame bilan yangi o'yin oching.")
        return
    lobby = lobbies[0]
    lobby_id = lobby["id"]
    if lobby["creator_id"] != msg.from_user.id:
        await msg.answer("❌ Faqat yaratuvchi o'yinni boshlaydi!")
        return
    count = get_lobby_player_count(lobby_id)
    if count < 4:
        await msg.answer(f"❌ Kamida 4 kishi kerak! Hozir: {count}\nQo'shilish: /join")
        return
    players = get_lobby_players(lobby_id)
    scenario, year = get_random_scenario()
    update_lobby_status(lobby_id, "active", scenario, year)
    init_game_state(lobby_id, players, scenario, year)
    scenario_desc = await get_scenario_description(scenario, year)
    player_list = "\n".join([f"• {p['full_name']}" for p in players])
    me = await bot.get_me()
    await msg.answer(
        f"🚨 <b>O'YIN BOSHLANDI!</b>\n\n"
        f"📅 Yil: <b>{year}</b>\n"
        f"⚡ Voqea: <b>{scenario}</b>\n\n"
        f"<i>{scenario_desc}</i>\n\n"
        f"👥 Ishtirokchilar:\n{player_list}\n\n"
        f"⚠️ Har bir o'yinchi botga o'tib kartasini ochsin!\n"
        f"👉 @{me.username}",
        parse_mode="HTML"
    )
    failed = []
    for player in players:
        try:
            await bot.send_message(
                player["user_id"],
                f"🃏 <b>Sizning kartangiz:</b>\n\n"
                f"🏷️ Tur: {player['card_type']}\n"
                f"👤 Nom: <b>{player['card_name']}</b>\n"
                f"📝 Tavsif: {player['card_desc']}\n\n"
                f"Kartangizni guruhda ochish uchun quyidagi tugmani bosing:",
                parse_mode="HTML",
                reply_markup=reveal_card_keyboard(lobby_id)
            )
        except Exception as e:
            logging.error(f"Xabar yuborilmadi {player['user_id']}: {e}")
            failed.append(player['full_name'])
    if failed:
        await msg.answer(
            f"⚠️ Quyidagi o'yinchilarga xabar yuborilmadi:\n"
            f"{', '.join(failed)}\n\n"
            f"Iltimos botga avval /start yuboring: @{me.username}",
            parse_mode="HTML"
        )

@dp.message(Command("stop"))
async def cmd_stop(msg: Message):
    if msg.chat.type == "private":
        await msg.answer("❌ Bu buyruq faqat guruhda ishlaydi!")
        return
    lobbies = [l for l in get_active_lobbies() if l["chat_id"] == msg.chat.id]
    if not lobbies:
        await msg.answer("❌ Ochiq lobby yo'q!")
        return
    lobby = lobbies[0]
    if lobby["creator_id"] != msg.from_user.id and msg.from_user.id != ADMIN_ID:
        await msg.answer("❌ Faqat yaratuvchi yoki admin bekor qila oladi!")
        return
    update_lobby_status(lobby["id"], "finished")
    end_game(lobby["id"])
    await msg.answer("🛑 O'yin bekor qilindi!")

# ═══════════════════════════════════════════════════════════
# CALLBACKS
# ═══════════════════════════════════════════════════════════

@dp.callback_query()
async def callback_handler(call: CallbackQuery):
    uid = call.from_user.id
    cid = call.message.chat.id
    data = call.data

    async def edit(text, kb=None):
        try:
            await call.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
        except Exception as e:
            logging.error(f"edit error: {e}")

    async def send(text, kb=None):
        await bot.send_message(cid, text, parse_mode="HTML", reply_markup=kb)

    await call.answer()

    if data == "back_main":
        user = get_user(uid)
        bc = user['bc_balance'] if user else 0
        await edit(f"🏠 Asosiy menyu\n💰 BC: {bc}", main_menu())

    elif data == "profile":
        u = get_user(uid)
        pct = round(u['wins']/u['games_played']*100) if u['games_played'] > 0 else 0
        await edit(
            f"👤 <b>Profilingiz</b>\n\n"
            f"📛 {u['full_name']}\n"
            f"💰 BC: {u['bc_balance']}\n"
            f"🎮 O'yinlar: {u['games_played']}\n"
            f"🏆 G'alabalar: {u['wins']}\n"
            f"📊 G'alaba: {pct}%",
            back_keyboard("back_main")
        )

    elif data == "rating":
        top = get_top_users(10)
        medals = ["🥇","🥈","🥉"]
        text = "🏆 <b>TOP 10 O'YINCHILAR</b>\n\n"
        for i, u in enumerate(top):
            m = medals[i] if i < 3 else f"{i+1}."
            text += f"{m} {u['full_name']} — {u['wins']} g'alaba | {u['bc_balance']} BC\n"
        await edit(text, back_keyboard("back_main"))

    elif data == "rules":
        await edit("📜 <b>Qoidalar bo'limlari:</b>", rules_keyboard())

    elif data.startswith("rules_"):
        section = data.replace("rules_","")
        rules_map = {
            "bot": "🤖 Bot qoidalari",
            "kasb": "👮 Kasb qoidalari",
            "salomatlik": "💪 Salomatlik qoidalari",
            "hunar": "🎯 Hunar qoidalari",
            "biografiya": "📖 Biografiya qoidalari",
        }
        key = rules_map.get(section)
        if key and key in RULES:
            text = f"<b>{key}</b>\n\n" + "\n".join(RULES[key])
            await edit(text, back_keyboard("rules"))

    elif data == "connect_channel":
        user_states[uid] = "awaiting_channel_id"
        await edit(
            "🔗 Kanalingizning ID sini yuboring:\n\n"
            "Masalan: @mening_kanalim\n\n"
            "⚠️ Bot kanalga admin bo'lishi kerak!",
            back_keyboard("back_main")
        )

    elif data == "join_main_channel":
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📢 Kanalga qo'shilish", url=MAIN_CHANNEL)],
            [InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_main")],
        ])
        await edit("📢 Asosiy Bunker kanaliga qo'shiling:", kb)

    elif data == "market" or data.startswith("market_page_"):
        page = int(data.split("_")[-1]) if data.startswith("market_page_") else 0
        cards = get_all_market_cards()
        await edit(f"🛒 <b>MARKET</b> ({len(cards)} ta karta)\n\nMaxsus imkoniyat kartalar:", market_keyboard(cards, page))

    elif data.startswith("buy_card_"):
        card_id = int(data.split("_")[-1])
        card = get_market_card(card_id)
        u = get_user(uid)
        await edit(
            f"{card['emoji']} <b>{card['name']}</b>\n\n"
            f"📝 {card['description']}\n\n"
            f"💰 Narx: {card['price']} BC\n"
            f"💳 Sizda: {u['bc_balance']} BC\n\n"
            f"Sotib olasizmi?",
            confirm_buy_keyboard(card_id)
        )

    elif data.startswith("confirm_buy_"):
        card_id = int(data.split("_")[-1])
        card = get_market_card(card_id)
        if spend_bc(uid, card["price"]):
            buy_market_card(uid, card_id)
            await call.answer(f"✅ {card['name']} sotib olindi!", show_alert=True)
            cards = get_all_market_cards()
            await edit("🛒 <b>MARKET</b>", market_keyboard(cards))
        else:
            u = get_user(uid)
            needed = card['price'] - u['bc_balance']
            await edit(
                f"{card['emoji']} <b>{card['name']}</b>\n\n"
                f"❌ <b>BC yetarli emas!</b>\n\n"
                f"💰 Narx: {card['price']} BC\n"
                f"💳 Sizda: {u['bc_balance']} BC\n"
                f"📉 Yetishmaydi: {needed} BC\n\n"
                f"O'yin o'ynab BC to'plang:\n"
                f"• O'yindan chiqsangiz: +10 BC\n"
                f"• G'olib bo'lsangiz: +50-100 BC",
                back_keyboard("market")
            )

    elif data == "create_lobby":
        cards = get_recent_cards(50)
        if not cards:
            await call.answer("❌ Hali kartalar yo'q! Admin karta yaratsin.", show_alert=True)
            return
        existing = [l for l in get_active_lobbies() if l["creator_id"] == uid]
        if existing:
            await call.answer("❌ Sizda allaqachon ochiq lobby bor!", show_alert=True)
            return
        lobby_id = create_lobby(uid, cid)
        rc = random.choice(cards)
        join_lobby(lobby_id, uid, rc["id"])
        await edit(
            f"🏠 <b>Lobby #{lobby_id} yaratildi!</b>\n\n"
            f"👤 Yaratuvchi: {call.from_user.full_name}\n"
            f"👥 O'yinchilar: 1/7\n"
            f"⏳ Minimum: 4 kishi\n\n"
            f"Boshqalar qo'shilishini kuting, keyin o'yinni boshlang!",
            lobby_action_keyboard(lobby_id, is_creator=True, joined=True)
        )

    elif data == "view_lobbies":
        lobbies = get_active_lobbies()
        if not lobbies:
            await edit("😔 Hozircha ochiq lobby yo'q.\n\nBirinchi bo'lib lobby oching!", back_keyboard("back_main"))
            return
        for l in lobbies:
            l["player_count"] = get_lobby_player_count(l["id"])
        await edit(f"👥 <b>Ochiq lobbylar:</b> {len(lobbies)} ta", lobbies_keyboard(lobbies))

    elif data.startswith("join_lobby_"):
        lobby_id = int(data.split("_")[-1])
        lobby = get_lobby(lobby_id)
        if not lobby or lobby["status"] != "waiting":
            await call.answer("❌ Bu lobby mavjud emas yoki o'yin boshlangan!", show_alert=True)
            return
        if get_lobby_player_count(lobby_id) >= 7:
            await call.answer("❌ Lobby to'ldi!", show_alert=True)
            return
        already_in = is_in_lobby(lobby_id, uid)
        if not already_in:
            cards = get_recent_cards(50)
            if not cards:
                await call.answer("❌ Kartalar yo'q!", show_alert=True)
                return
            rc = random.choice(cards)
            join_lobby(lobby_id, uid, rc["id"])
        new_count = get_lobby_player_count(lobby_id)
        is_creator = lobby["creator_id"] == uid
        await edit(
            f"🏠 <b>Lobby #{lobby_id}</b>\n\n"
            f"👥 O'yinchilar: {new_count}/7\n"
            f"✅ Siz lobbydasiz!\n"
            f"⏳ Yaratuvchi o'yinni boshlashini kuting...",
            lobby_action_keyboard(lobby_id, is_creator=is_creator, joined=True)
        )

    elif data.startswith("leave_lobby_"):
        lobby_id = int(data.split("_")[-1])
        lobby = get_lobby(lobby_id)
        if not lobby or lobby["status"] != "waiting":
            await call.answer("❌ O'yin boshlangan, chiqib bo'lmaydi!", show_alert=True)
            return
        if lobby["creator_id"] == uid:
            await call.answer("❌ Yaratuvchi chiqolmaydi! /stop bilan bekor qiling.", show_alert=True)
            return
        if leave_lobby(lobby_id, uid):
            new_count = get_lobby_player_count(lobby_id)
            await call.answer("✅ Lobbydan chiqdingiz!")
            await edit(
                f"🏠 <b>Lobby #{lobby_id}</b>\n\n"
                f"👥 O'yinchilar: {new_count}/7\n\n"
                f"Qaytib qo'shilish uchun tugmani bosing:",
                lobby_action_keyboard(lobby_id, joined=False)
            )
        else:
            await call.answer("❌ Siz bu lobbyda emassiz!", show_alert=True)

    elif data.startswith("start_game_"):
        lobby_id = int(data.split("_")[-1])
        lobby = get_lobby(lobby_id)
        if not lobby or lobby["creator_id"] != uid:
            await call.answer("❌ Faqat yaratuvchi o'yinni boshlaydi!", show_alert=True)
            return
        count = get_lobby_player_count(lobby_id)
        if count < 4:
            await call.answer(f"❌ Kamida 4 kishi kerak! Hozir: {count}", show_alert=True)
            return
        players = get_lobby_players(lobby_id)
        scenario, year = get_random_scenario()
        update_lobby_status(lobby_id, "active", scenario, year)
        init_game_state(lobby_id, players, scenario, year)
        scenario_desc = await get_scenario_description(scenario, year)
        player_list = "\n".join([f"• {p['full_name']}" for p in players])
        me = await bot.get_me()
        await edit(
            f"🚨 <b>O'YIN BOSHLANDI!</b>\n\n"
            f"📅 Yil: <b>{year}</b>\n"
            f"⚡ Voqea: <b>{scenario}</b>\n\n"
            f"<i>{scenario_desc}</i>\n\n"
            f"👥 Ishtirokchilar:\n{player_list}\n\n"
            f"⚠️ Har bir o'yinchi botga o'tib kartasini ochsin!\n"
            f"👉 @{me.username}"
        )
        for player in players:
            try:
                await bot.send_message(
                    player["user_id"],
                    f"🃏 <b>Sizning kartangiz:</b>\n\n"
                    f"🏷️ Tur: {player['card_type']}\n"
                    f"👤 Nom: <b>{player['card_name']}</b>\n"
                    f"📝 Tavsif: {player['card_desc']}\n\n"
                    f"Kartangizni ochish uchun tugmani bosing:",
                    parse_mode="HTML",
                    reply_markup=reveal_card_keyboard(lobby_id)
                )
            except Exception as e:
                logging.error(f"Xabar yuborilmadi {player['user_id']}: {e}")

    elif data.startswith("reveal_card_"):
        lobby_id = int(data.split("_")[-1])
        game = get_game(lobby_id)
        if not game:
            await call.answer("❌ O'yin topilmadi!", show_alert=True)
            return
        if uid not in game["alive_players"]:
            await call.answer("❌ Siz bu o'yinda emassiz!", show_alert=True)
            return
        if uid in game["revealed"]:
            await call.answer("✅ Allaqachon ochdingiz!", show_alert=True)
            return
        player = game["players"].get(uid)
        all_revealed = reveal_player_card(lobby_id, uid)
        await call.answer(f"✅ Kartangiz ochildi: {player['card_name']}")
        lobby = get_lobby(lobby_id)
        chat_id = lobby["chat_id"] if lobby else cid
        await bot.send_message(
            chat_id,
            f"👁️ <b>{player['full_name']}</b> kartasini ochdi:\n\n"
            f"🏷️ {player['card_type']}\n"
            f"👤 <b>{player['card_name']}</b>\n"
            f"📝 <i>{player['card_desc']}</i>",
            parse_mode="HTML"
        )
        if all_revealed:
            await asyncio.sleep(2)
            asyncio.create_task(start_voting_phase(chat_id, lobby_id))

    elif data.startswith("vote_"):
        parts = data.split("_")
        lobby_id = int(parts[1])
        target_id = int(parts[2])
        game = get_game(lobby_id)
        if not game:
            await call.answer("❌ O'yin topilmadi!", show_alert=True)
            return
        if uid not in game["alive_players"]:
            await call.answer("❌ Siz o'yindan chiqgansiz!", show_alert=True)
            return
        if game["market_card_used"].get(uid) == "fear":
            await call.answer("😱 Siz bu raundda ovoz bera olmaysiz!", show_alert=True)
            return
        add_vote(lobby_id, uid, target_id)
        target = game["players"].get(target_id)
        await call.answer(f"✅ {target['full_name']} ga ovoz berdingiz!")

    elif data == "admin_panel":
        if uid != ADMIN_ID:
            return
        await edit("🔧 Admin paneli:", admin_menu())

    elif data == "admin_create_card":
        if uid != ADMIN_ID:
            return
        await edit("➕ <b>Karta turi tanlang:</b>", card_type_keyboard())

    elif data.startswith("type_"):
        if uid != ADMIN_ID:
            return
        type_map = {
            "type_kasb":"👮 Kasb","type_salomatlik":"💪 Salomatlik",
            "type_biografiya":"📖 Biografiya","type_hunar":"🎯 Hunar",
            "type_genetika":"🧬 Genetika","type_aql":"🧠 Aql",
            "type_ijtimoiy":"❤️ Ijtimoiy","type_bagaj":"🎒 Bagaj",
        }
        ct = type_map.get(data,"Noma'lum")
        user_states[uid] = {"step":"card_name","type":ct}
        await edit(f"✅ Tur: <b>{ct}</b>\n\nKarta nomini yozing:\nMasalan: Politsiyachi")

    elif data == "admin_view_cards":
        if uid != ADMIN_ID:
            return
        cards = get_recent_cards(10)
        if not cards:
            await edit("📋 Hali kartalar yo'q.", back_keyboard("admin_panel"))
            return
        text = "📋 <b>Oxirgi 10 ta karta:</b>\n\n"
        for c in cards:
            text += f"🆔 <b>ID:{c['id']}</b> | {c['card_type']}\n👤 {c['name']}\n📝 <i>{c['description']}</i>\n\n"
        await edit(text, back_keyboard("admin_panel"))

    elif data == "admin_edit_card":
        if uid != ADMIN_ID:
            return
        user_states[uid] = {"step":"edit_id"}
        await edit("✏️ Tahrirlash uchun karta ID sini yozing:", back_keyboard("admin_panel"))

# ═══════════════════════════════════════════════════════════
# O'YIN FAZALARI
# ═══════════════════════════════════════════════════════════

async def start_voting_phase(chat_id, lobby_id):
    game = get_game(lobby_id)
    if not game:
        return
    game["phase"] = "voting"
    players = [game["players"][uid] for uid in game["alive_players"]]

    await bot.send_message(chat_id,
        f"⏰ <b>1 DAQIQA MUHOKAMA VAQTI! (Raund {game['round']})</b>\n\n"
        "Kimni bunkerdan chiqarasiz? Muhokama qiling!\n"
        "60 soniyadan so'ng ovoz berish boshlanadi...",
        parse_mode="HTML")
    await asyncio.sleep(60)

    game = get_game(lobby_id)
    if not game:
        return

    await bot.send_message(chat_id,
        "🗳️ <b>OVOZ BERISH BOSHLANDI! 60 SONIYA!</b>\n\nKimni o'yindan chiqarasiz?",
        parse_mode="HTML",
        reply_markup=vote_keyboard(lobby_id, players, 0))
    await asyncio.sleep(60)
    await process_votes(chat_id, lobby_id)

async def process_votes(chat_id, lobby_id):
    game = get_game(lobby_id)
    if not game:
        return

    eliminated_id, vote_count = count_votes(lobby_id)

    if vote_count:
        text = "📊 <b>Ovozlar natijasi:</b>\n"
        for pid, v in vote_count.items():
            p = game["players"].get(pid)
            if p:
                text += f"• {p['full_name']}: {v} ovoz\n"
        await bot.send_message(chat_id, text, parse_mode="HTML")

    if not eliminated_id:
        reset_votes(lobby_id)
        await bot.send_message(chat_id, "⚖️ <b>Ovozlar teng! Qayta ovoz berish...</b>", parse_mode="HTML")
        await asyncio.sleep(3)
        asyncio.create_task(start_voting_phase(chat_id, lobby_id))
        return

    eliminated_player = game["players"].get(eliminated_id)
    eliminate(lobby_id, eliminated_id)

    await bot.send_message(chat_id,
        f"❌ <b>{eliminated_player['full_name']}</b> bunkerdan chiqarildi!\n\n"
        f"Karta: {eliminated_player['card_name']}\n<i>{eliminated_player['card_desc']}</i>",
        parse_mode="HTML")

    update_stats(eliminated_id, won=False)
    add_bc(eliminated_id, 10)
    try:
        await bot.send_message(eliminated_id,
            "😔 Siz bunkerdan chiqarildingiz!\n+10 BC oldiniz.\n\nO'yinni kuzatishingiz mumkin.")
    except:
        pass

    alive_count = count_alive_players(lobby_id)
    if alive_count <= 2:
        await finish_game(chat_id, lobby_id)
    else:
        await bot.send_message(chat_id,
            f"✅ Qolgan o'yinchilar: {alive_count}\n\nKeyingi raund boshlanmoqda...",
            parse_mode="HTML")
        await asyncio.sleep(3)
        asyncio.create_task(start_voting_phase(chat_id, lobby_id))

async def finish_game(chat_id, lobby_id):
    game = get_game(lobby_id)
    winners = get_winners(lobby_id)
    winners_data = [game["players"][wid] for wid in winners if wid in game["players"]]
    winner_names = " va ".join([p["full_name"] for p in winners_data])

    await bot.send_message(chat_id,
        f"🎉 <b>O'YIN TUGADI!</b>\n\n"
        f"🏆 G'oliblar: <b>{winner_names}</b>\n\n"
        f"⏳ Grok tahlili boshlanmoqda...",
        parse_mode="HTML")

    analysis = await analyze_winners(winners_data, game["scenario"], game["year"])
    bc_amount = 100 if len(winners_data) == 2 else 50

    for wid in winners:
        update_stats(wid, won=True)
        add_bc(wid, bc_amount)
        try:
            await bot.send_message(wid,
                f"🏆 Tabriklaymiz! G'olib bo'ldingiz!\n+{bc_amount} BC oldiniz!")
        except:
            pass

    await bot.send_message(chat_id,
        f"🔮 <b>KELAJAK TAHLILI (Grok AI):</b>\n\n{analysis}\n\n"
        f"💰 G'oliblar +{bc_amount} BC oldi!",
        parse_mode="HTML")
    end_game(lobby_id)

# ═══════════════════════════════════════════════════════════
# MATN XABARLARI
# ═══════════════════════════════════════════════════════════

@dp.message(F.text)
async def text_handler(msg: Message):
    uid = msg.from_user.id
    state = user_states.get(uid)
    if not state:
        return
    text = msg.text.strip()

    if state == "awaiting_channel_id":
        connect_channel(uid, text, text)
        user_states.pop(uid, None)
        await msg.answer(f"✅ Kanal ulandi: {text}", reply_markup=main_menu())

    elif isinstance(state, dict) and state.get("step") == "card_name":
        user_states[uid]["card_name"] = text
        user_states[uid]["step"] = "card_desc"
        await msg.answer(f"✅ Nom: <b>{text}</b>\n\nKarta tavsifini yozing:", parse_mode="HTML")

    elif isinstance(state, dict) and state.get("step") == "card_desc":
        ctype = state["type"]
        cname = state["card_name"]
        card_id = create_card(ctype, cname, text)
        user_states.pop(uid, None)
        await msg.answer(
            f"✅ <b>Karta yaratildi!</b>\n\n🆔 ID: {card_id}\n🏷️ {ctype}\n👤 {cname}\n📝 {text}",
            parse_mode="HTML", reply_markup=admin_menu())

    elif isinstance(state, dict) and state.get("step") == "edit_id":
        try:
            card_id = int(text)
            card = get_card_by_id(card_id)
            if card:
                user_states[uid] = {"step":"edit_name","card_id":card_id}
                await msg.answer(
                    f"📋 <b>Karta #{card_id}:</b>\n🏷️ {card['card_type']}\n"
                    f"👤 {card['name']}\n📝 {card['description']}\n\n"
                    f"Yangi nomini yozing (o'zgartirmasangiz <code>-</code> yozing):",
                    parse_mode="HTML")
            else:
                await msg.answer(f"❌ ID {card_id} topilmadi!")
        except ValueError:
            await msg.answer("❌ Raqam kiriting!")

    elif isinstance(state, dict) and state.get("step") == "edit_name":
        user_states[uid]["new_name"] = text if text != "-" else None
        user_states[uid]["step"] = "edit_desc"
        await msg.answer("Yangi tavsifini yozing (o'zgartirmasangiz <code>-</code> yozing):", parse_mode="HTML")

    elif isinstance(state, dict) and state.get("step") == "edit_desc":
        card_id = state["card_id"]
        new_name = state.get("new_name")
        new_desc = text if text != "-" else None
        update_card(card_id, name=new_name, description=new_desc)
        user_states.pop(uid, None)
        await msg.answer(f"✅ Karta #{card_id} yangilandi!", reply_markup=admin_menu())

# ═══════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════

async def main():
    init_db()
    init_market_cards()

    private_commands = [
        BotCommand(command="start", description="🏠 Botni boshlash"),
        BotCommand(command="help", description="❓ Yordam"),
        BotCommand(command="admin", description="🔧 Admin paneli"),
    ]
    group_commands = [
        BotCommand(command="newgame", description="🎮 Yangi o'yin boshlash"),
        BotCommand(command="join", description="✅ O'yinga qo'shilish"),
        BotCommand(command="leave", description="🚪 Lobbydan chiqish"),
        BotCommand(command="players", description="👥 O'yinchilar ro'yxati"),
        BotCommand(command="start_game", description="▶️ O'yinni boshlash"),
        BotCommand(command="stop", description="🛑 O'yinni bekor qilish"),
        BotCommand(command="help", description="❓ Yordam"),
    ]
    await bot.set_my_commands(private_commands, scope=BotCommandScopeDefault())
    await bot.set_my_commands(private_commands, scope=BotCommandScopeAllPrivateChats())
    await bot.set_my_commands(group_commands, scope=BotCommandScopeAllGroupChats())
    print("✅ Buyruqlar menyusi o'rnatildi!")
    print("🚀 Bunker Bot ishga tushdi!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
