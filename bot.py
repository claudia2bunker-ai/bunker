import os
import asyncio
import random
import logging
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command
from aiogram.fsm.storage.memory import MemoryStorage

load_dotenv()

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("8964759983:AAFqwMDuUYQW5dQGBfx_LNeKslGorJ3dSZU")
ADMIN_ID = int(os.getenv("6060306988"))
MAIN_CHANNEL = "@bunker_official"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

from database import *
from game import *
from grok_ai import analyze_winners, get_scenario_description
from keyboards import *

user_states = {}

# ─── /start ──────────────────────────────────────────────
@dp.message(CommandStart())
async def start(msg: Message):
    user = get_or_create_user(msg.from_user.id, msg.from_user.username or "", msg.from_user.full_name)
    await msg.answer(
        f"☢️ *BUNKER* ga xush kelibsiz, {msg.from_user.first_name}\\!\n\n"
        f"Apokalipsis boshlanmoqda\\. Bunkerda joy cheklangan\\.\n"
        f"Faqat eng loyiqlari omon qoladi\\.\\.\\.\n\n"
        f"💰 BC: {user['bc_balance']}",
        parse_mode="MarkdownV2",
        reply_markup=main_menu()
    )

# ─── /admin ──────────────────────────────────────────────
@dp.message(Command("admin"))
async def admin_cmd(msg: Message):
    if msg.from_user.id != ADMIN_ID:
        await msg.answer("❌ Ruxsat yo'q!")
        return
    await msg.answer("🔧 Admin paneli:", reply_markup=admin_menu())

# ─── CALLBACKS ───────────────────────────────────────────
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

    # BACK
    if data == "back_main":
        user = get_user(uid)
        bc = user['bc_balance'] if user else 0
        await edit(f"🏠 Asosiy menyu\n💰 BC: {bc}", main_menu())

    # PROFILE
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

    # RATING
    elif data == "rating":
        top = get_top_users(10)
        medals = ["🥇","🥈","🥉"]
        text = "🏆 <b>TOP 10 O'YINCHILAR</b>\n\n"
        for i, u in enumerate(top):
            m = medals[i] if i < 3 else f"{i+1}."
            text += f"{m} {u['full_name']} — {u['wins']} g'alaba | {u['bc_balance']} BC\n"
        await edit(text, back_keyboard("back_main"))

    # RULES
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

    # CONNECT CHANNEL
    elif data == "connect_channel":
        user_states[uid] = "awaiting_channel_id"
        await edit(
            "🔗 Kanalingizning ID sini yuboring:\n\n"
            "Masalan: @mening_kanalim\n\n"
            "⚠️ Bot kanalga admin bo'lishi kerak!",
            back_keyboard("back_main")
        )

    # JOIN MAIN CHANNEL
    elif data == "join_main_channel":
        await edit(f"📢 Asosiy kanalga qo'shiling:\n{MAIN_CHANNEL}", back_keyboard("back_main"))

    # MARKET
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
            await call.answer("❌ BC yetarli emas!", show_alert=True)

    # CREATE LOBBY
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
            lobby_action_keyboard(lobby_id, is_creator=True)
        )

    # VIEW LOBBIES
    elif data == "view_lobbies":
        lobbies = get_active_lobbies()
        if not lobbies:
            await edit("😔 Hozircha ochiq lobby yo'q.\n\nBirinchi bo'lib lobby oching!", back_keyboard("back_main"))
            return
        for l in lobbies:
            l["player_count"] = get_lobby_player_count(l["id"])
        await edit(f"👥 <b>Ochiq lobbylar:</b> {len(lobbies)} ta", lobbies_keyboard(lobbies))

    # JOIN LOBBY
    elif data.startswith("join_lobby_"):
        lobby_id = int(data.split("_")[-1])
        lobby = get_lobby(lobby_id)
        if not lobby or lobby["status"] != "waiting":
            await call.answer("❌ Bu lobby mavjud emas yoki o'yin boshlangan!", show_alert=True)
            return
        if get_lobby_player_count(lobby_id) >= 7:
            await call.answer("❌ Lobby to'ldi!", show_alert=True)
            return
        cards = get_recent_cards(50)
        if not cards:
            await call.answer("❌ Kartalar yo'q!", show_alert=True)
            return
        rc = random.choice(cards)
        if not join_lobby(lobby_id, uid, rc["id"]):
            await call.answer("❌ Siz allaqachon bu lobbydasiz!", show_alert=True)
            return
        new_count = get_lobby_player_count(lobby_id)
        is_creator = lobby["creator_id"] == uid
        await edit(
            f"✅ Lobby #{lobby_id} ga qo'shildingiz!\n\n"
            f"👥 O'yinchilar: {new_count}/7\n"
            f"⏳ Yaratuvchi o'yinni boshlashini kuting...",
            lobby_action_keyboard(lobby_id, is_creator=is_creator)
        )

    # START GAME
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
        await edit(
            f"🚨 <b>O'YIN BOSHLANDI!</b>\n\n"
            f"📅 Yil: <b>{year}</b>\n"
            f"⚡ Voqea: <b>{scenario}</b>\n\n"
            f"<i>{scenario_desc}</i>\n\n"
            f"👥 Ishtirokchilar:\n{player_list}"
        )
        for player in players:
            try:
                await bot.send_message(
                    player["user_id"],
                    f"🃏 <b>Sizning kartangiz:</b>\n\n"
                    f"🏷️ Tur: {player['card_type']}\n"
                    f"👤 Nom: <b>{player['card_name']}</b>\n"
                    f"📝 Tavsif: {player['card_desc']}\n\n"
                    f"Kartangizni guruhdagi tugma orqali oching!",
                    parse_mode="HTML"
                )
            except Exception as e:
                logging.error(f"Xabar yuborilmadi {player['user_id']}: {e}")
        await send("🃏 Barcha o'yinchilar kartalarini ochinlar!", reveal_card_keyboard(lobby_id))

    # REVEAL CARD
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
        await send(
            f"👁️ <b>{player['full_name']}</b> kartasini ochdi:\n\n"
            f"🏷️ {player['card_type']}\n"
            f"👤 <b>{player['card_name']}</b>\n"
            f"📝 <i>{player['card_desc']}</i>"
        )
        if all_revealed:
            await asyncio.sleep(2)
            asyncio.create_task(start_voting_phase(cid, lobby_id))

    # VOTE
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

    # ADMIN
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
        ct = type_map.get(data, "Noma'lum")
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

# ─── GAME PHASES ─────────────────────────────────────────
async def start_voting_phase(chat_id, lobby_id):
    game = get_game(lobby_id)
    if not game:
        return
    game["phase"] = "voting"
    players = [game["players"][uid] for uid in game["alive_players"]]

    await bot.send_message(chat_id,
        "⏰ <b>1 DAQIQA MUHOKAMA VAQTI!</b>\n\n"
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
        await bot.send_message(eliminated_id, "😔 Siz bunkerdan chiqarildingiz!\n+10 BC oldiniz.")
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
        f"🎉 <b>O'YIN TUGADI!</b>\n\n🏆 G'oliblar: <b>{winner_names}</b>\n\n⏳ Grok tahlili boshlanmoqda...",
        parse_mode="HTML")

    analysis = await analyze_winners(winners_data, game["scenario"], game["year"])
    bc_amount = 100 if len(winners_data) == 2 else 50

    for wid in winners:
        update_stats(wid, won=True)
        add_bc(wid, bc_amount)
        try:
            await bot.send_message(wid, f"🏆 Tabriklaymiz! G'olib bo'ldingiz!\n+{bc_amount} BC oldiniz!")
        except:
            pass

    await bot.send_message(chat_id,
        f"🔮 <b>KELAJAK TAHLILI (Grok AI):</b>\n\n{analysis}\n\n💰 G'oliblar +{bc_amount} BC oldi!",
        parse_mode="HTML")
    end_game(lobby_id)

# ─── TEXT MESSAGES ────────────────────────────────────────
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

# ─── MAIN ────────────────────────────────────────────────
async def main():
    init_db()
    init_market_cards()
    print("🚀 Bunker Bot ishga tushdi!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
