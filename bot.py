import os
import asyncio
import random
import logging
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher, F, Router
from aiogram.types import Message, CallbackQuery, BotCommand
from aiogram.types import BotCommandScopeDefault, BotCommandScopeAllPrivateChats, BotCommandScopeAllGroupChats
from aiogram.filters import CommandStart, Command
from aiogram.fsm.storage.memory import MemoryStorage

load_dotenv()
logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
MAIN_CHANNEL = "https://t.me/+Ypej9hA5AC8wNTQy"
# Kanal ID olish: kanalga @userinfobot qo'shing va /start yozing
# Yoki kanal ga bot admin qilib, biror xabar forward qilib @RawDataBot ga yuboring
MAIN_CHANNEL_ID = None  # Masalan: -1001234567890

# ── Global bot va dp ───────────────────────────────────────
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

private_router = Router()
group_router = Router()

private_router.message.filter(F.chat.type == "private")
group_router.message.filter(F.chat.type.in_({"group", "supergroup"}))

# ── Guruhda o'yin bo'lsa lobbyga qo'shilmaganlar yoza olmasin ──
@group_router.message(F.text & ~F.text.startswith("/"))
async def block_non_players(msg: Message):
    chat_id = msg.chat.id
    uid = msg.from_user.id

    # Bu guruhda faol o'yin bormi?
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT id FROM lobbies WHERE chat_id=? AND status='active'", (chat_id,))
    active = c.fetchone()
    conn.close()

    if not active:
        return  # O'yin yo'q — hammaga ruxsat

    lobby_id = active[0]
    game = get_game(lobby_id)

    if not game:
        return  # O'yin xotirada yo'q — ruxsat

    # O'yinda qatnashuvchi yoki chiqarilganmi?
    is_participant = (
        uid in game["alive_players"] or
        uid in game.get("eliminated", [])
    )

    if not is_participant:
        # Xabarni o'chir
        try:
            await msg.delete()
        except:
            pass



dp.include_router(group_router)
dp.include_router(private_router)

from database import *
from game import *
from grok_ai import analyze_winners, get_scenario_description, generate_group_result
from keyboards import *

user_states = {}

# ═══════════════════════════════════════════════════════════
# PRIVATE HANDLERS
# ═══════════════════════════════════════════════════════════

@private_router.message(CommandStart())
async def start(msg: Message):
    uid = msg.from_user.id
    args = msg.text.split()
    is_new = get_user(uid) is None
    user = get_or_create_user(uid, msg.from_user.username or "", msg.from_user.full_name)

    # Kanal obunasini tekshirish
    if MAIN_CHANNEL_ID:
        try:
            member = await bot.get_chat_member(MAIN_CHANNEL_ID, uid)
            is_subscribed = member.status not in ("left", "kicked")
        except:
            is_subscribed = True
        if not is_subscribed:
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📢 Kanalga qo'shilish", url=MAIN_CHANNEL)],
                [InlineKeyboardButton(text="✅ Qo'shildim", callback_data="check_sub")],
            ])
            await msg.answer(
                "⚠️ <b>Botdan foydalanish uchun avval kanalga qo'shiling!</b>\n\n"
                "👇 Quyidagi tugmani bosing:",
                parse_mode="HTML", reply_markup=kb)
            return

    if is_new and len(args) > 1 and args[1].startswith("ref_"):
        try:
            referrer_id = int(args[1].replace("ref_", ""))
            if referrer_id != uid:
                success = register_referral(referrer_id, uid)
                if success:
                    ranked_up, bonus, count = check_referral_rank_up(referrer_id)
                    try:
                        await bot.send_message(referrer_id,
                            f"🎁 Do'stingiz qo'shildi! +50 BC oldiniz!\n"
                            f"👥 Jami referallar: {count}\n"
                            f"{'🏅 Referal bonusi: +' + str(bonus) + ' BC!' if ranked_up else ''}",
                            parse_mode="HTML")
                    except:
                        pass
                    user = get_user(uid)
                    await msg.answer(
                        f"🎉 Taklif orqali kelganingiz uchun <b>+30 BC</b> oldiniz!\n\n"
                        f"☢️ <b>BUNKER</b> ga xush kelibsiz, {msg.from_user.first_name}!\n"
                        f"💰 BC: {user['bc_balance']}",
                        parse_mode="HTML", reply_markup=main_menu())
                    return
        except:
            pass

    me = await bot.get_me()
    await msg.answer(
        f"☢️ <b>BUNKER</b> ga xush kelibsiz, {msg.from_user.first_name}!\n\n"
        f"Apokalipsis boshlanmoqda. Bunkerda joy cheklangan.\n"
        f"Faqat eng loyiqlari omon qoladi...\n\n"
        f"💰 BC: {user['bc_balance']}",
        parse_mode="HTML", reply_markup=main_menu(me.username))

@private_router.message(Command("admin"))
async def admin_cmd(msg: Message):
    if msg.from_user.id != ADMIN_ID:
        await msg.answer("❌ Ruxsat yo'q!")
        return
    await msg.answer("🔧 Admin paneli:", reply_markup=admin_menu())

@private_router.message(Command("help"))
async def help_private(msg: Message):
    await msg.answer(
        "🤖 <b>Bunker Bot yordam</b>\n\n"
        "Guruhda o'yin:\n"
        "/newgame — yangi o'yin\n/join — qo'shilish\n"
        "/leave — chiqish\n/players — o'yinchilar\n"
        "/start_game — boshlash\n/stop — bekor qilish\n\n"
        "Private:\n"
        "/bonus — kunlik bonus\n/stats — statistika\n/refer — referal",
        parse_mode="HTML", reply_markup=main_menu())

@private_router.message(Command("bonus"))
async def cmd_bonus(msg: Message):
    uid = msg.from_user.id
    get_or_create_user(uid, msg.from_user.username or "", msg.from_user.full_name)
    bonus, streak = claim_daily_bonus(uid)
    if bonus is None:
        info = get_bonus_info(uid)
        streak = info["streak"] if info else 0
        bonus_map = {1:15,2:20,3:30,4:40,5:50,6:75,7:100}
        tomorrow = bonus_map.get(min(streak+1,7),100)
        await msg.answer(
            f"⏰ Kunlik bonusni allaqachon oldingiz!\n\n"
            f"🔥 Streak: {streak} kun\n⏳ Ertaga: +{tomorrow} BC",
            reply_markup=main_menu())
        return
    user = get_user(uid)
    streak_bar = "🔥"*min(streak,7) + "⬜"*max(0,7-streak)
    bonus_map = {1:15,2:20,3:30,4:40,5:50,6:75,7:100}
    next_b = bonus_map.get(min(streak+1,7),100)
    await msg.answer(
        f"✅ <b>Kunlik bonus!</b>\n\n💰 +{bonus} BC\n"
        f"💳 Jami: {user['bc_balance']} BC\n\n"
        f"🔥 Streak: {streak} kun\n{streak_bar}\n\n"
        f"{'🎉 7 kunlik streak!' if streak>=7 else f'Ertaga: +{next_b} BC'}",
        parse_mode="HTML", reply_markup=main_menu())

@private_router.message(Command("stats"))
async def cmd_stats(msg: Message):
    uid = msg.from_user.id
    u = get_user(uid)
    if not u:
        await msg.answer("❌ Avval /start bosing!")
        return
    rank = get_rank(u["wins"])
    next_rank = get_next_rank(u["wins"])
    pct = round(u['wins']/u['games_played']*100) if u['games_played']>0 else 0
    ref_count = get_referral_count(uid)
    bonus_info = get_bonus_info(uid)
    streak = bonus_info["streak"] if bonus_info else 0
    if next_rank:
        progress = u["wins"] - rank["min_wins"]
        total = next_rank["min_wins"] - rank["min_wins"]
        filled = int(progress/total*10) if total>0 else 0
        bar = "█"*filled + "░"*(10-filled)
        rank_text = f"\n📈 Keyingi: <b>{next_rank['name']}</b>\n{bar} {u['wins']}/{next_rank['min_wins']}"
    else:
        rank_text = "\n🌟 Eng yuqori unvon!"
    await msg.answer(
        f"📊 <b>{u['full_name']} statistikasi</b>\n\n"
        f"🏅 Unvon: {rank['name']}\n🎮 O'yinlar: {u['games_played']}\n"
        f"🏆 G'alabalar: {u['wins']} ({pct}%)\n💰 BC: {u['bc_balance']}\n"
        f"🔥 Streak: {streak} kun\n👥 Referallar: {ref_count}\n{rank_text}",
        parse_mode="HTML", reply_markup=main_menu())

@private_router.message(Command("refer"))
async def cmd_refer(msg: Message):
    uid = msg.from_user.id
    me = await bot.get_me()
    ref_count = get_referral_count(uid)
    thresholds = [3,6,10,15,21,28]
    next_t = next((t for t in thresholds if t>ref_count), None)
    link = f"https://t.me/{me.username}?start=ref_{uid}"
    await msg.answer(
        f"🎁 <b>Referal tizimi</b>\n\n"
        f"Havolangiz:\n<code>{link}</code>\n\n"
        f"👥 Taklif qilganlar: {ref_count} kishi\n\n"
        f"💰 Siz: +50 BC | Do'st: +30 BC\n"
        f"🏅 Har 3 kishi da unvon bonusi!\n"
        f"{'⏳ Keyingi bonus: '+str(next_t)+' kishida' if next_t else '🌟 Barcha bonuslar olindi!'}",
        parse_mode="HTML")

@private_router.message(F.text)
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
                    f"Yangi nomini yozing (<code>-</code> = o'zgartirma):",
                    parse_mode="HTML")
            else:
                await msg.answer(f"❌ ID {card_id} topilmadi!")
        except ValueError:
            await msg.answer("❌ Raqam kiriting!")

    elif isinstance(state, dict) and state.get("step") == "edit_name":
        user_states[uid]["new_name"] = text if text != "-" else None
        user_states[uid]["step"] = "edit_desc"
        await msg.answer("Yangi tavsifini yozing (<code>-</code> = o'zgartirma):", parse_mode="HTML")

    elif isinstance(state, dict) and state.get("step") == "edit_desc":
        card_id = state["card_id"]
        update_card(card_id, name=state.get("new_name"), description=text if text!="-" else None)
        user_states.pop(uid, None)
        await msg.answer(f"✅ Karta #{card_id} yangilandi!", reply_markup=admin_menu())

# ═══════════════════════════════════════════════════════════
# GROUP HANDLERS
# ═══════════════════════════════════════════════════════════

@group_router.message(Command("newgame"))
async def cmd_newgame(msg: Message):
    cards = get_recent_cards(50)
    if not cards:
        await msg.answer("❌ Hali kartalar yo'q! Admin avval karta yaratsin.")
        return
    existing = get_active_lobbies(chat_id=msg.chat.id)
    if existing:
        await msg.answer(
            f"❌ Bu guruhda allaqachon ochiq lobby bor!\n"
            f"Qo'shilish: /join | Ko'rish: /players")
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
        parse_mode="HTML")

@group_router.message(Command("join"))
async def cmd_join(msg: Message):
    lobbies = get_active_lobbies(chat_id=msg.chat.id)
    if not lobbies:
        await msg.answer("❌ Bu guruhda ochiq lobby yo'q!\nYangi o'yin: /newgame")
        return
    lobby_id = lobbies[0]["id"]
    if get_lobby_player_count(lobby_id) >= 7:
        await msg.answer("❌ Lobby to'ldi!")
        return
    get_or_create_user(msg.from_user.id, msg.from_user.username or "", msg.from_user.full_name)
    if is_in_lobby(lobby_id, msg.from_user.id):
        await msg.answer(f"❌ {msg.from_user.first_name}, siz allaqachon lobbydasiz!\nChiqish: /leave")
        return
    cards = get_recent_cards(50)
    if not cards:
        await msg.answer("❌ Kartalar yo'q!")
        return
    join_lobby(lobby_id, msg.from_user.id, random.choice(cards)["id"])
    count = get_lobby_player_count(lobby_id)
    await msg.answer(
        f"✅ <b>{msg.from_user.full_name}</b> lobbyga qo'shildi!\n👥 O'yinchilar: {count}/7",
        parse_mode="HTML")

@group_router.message(Command("leave"))
async def cmd_leave(msg: Message):
    lobbies = get_active_lobbies(chat_id=msg.chat.id)
    if not lobbies:
        await msg.answer("❌ Ochiq lobby yo'q!")
        return
    lobby = lobbies[0]
    if lobby["creator_id"] == msg.from_user.id:
        await msg.answer("❌ Yaratuvchi chiqolmaydi!\nBekor qilish: /stop")
        return
    if not is_in_lobby(lobby["id"], msg.from_user.id):
        await msg.answer("❌ Siz bu lobbyda emassiz!")
        return
    leave_lobby(lobby["id"], msg.from_user.id)
    count = get_lobby_player_count(lobby["id"])
    await msg.answer(
        f"🚪 <b>{msg.from_user.full_name}</b> lobbydan chiqdi.\n👥 Qolgan: {count}/7",
        parse_mode="HTML")

@group_router.message(Command("players"))
async def cmd_players(msg: Message):
    lobbies = get_active_lobbies(chat_id=msg.chat.id)
    if not lobbies:
        await msg.answer("❌ Ochiq lobby yo'q!")
        return
    lobby_id = lobbies[0]["id"]
    players = get_lobby_players(lobby_id)
    if not players:
        await msg.answer("👥 Hali hech kim qo'shilmagan!")
        return
    text = f"👥 <b>Lobby #{lobby_id} ({len(players)}/7):</b>\n\n"
    for i, p in enumerate(players, 1):
        text += f"{i}. {p['full_name']}\n"
    needed = max(0, 4-len(players))
    text += f"\n{'⏳ Yana '+str(needed)+' kishi kerak' if needed>0 else '✅ /start_game bilan boshlang!'}"
    await msg.answer(text, parse_mode="HTML")

@group_router.message(Command("start_game"))
async def cmd_start_game(msg: Message):
    lobbies = get_active_lobbies(chat_id=msg.chat.id)
    if not lobbies:
        await msg.answer("❌ Ochiq lobby yo'q!")
        return
    lobby = lobbies[0]
    lobby_id = lobby["id"]
    if lobby["creator_id"] != msg.from_user.id:
        await msg.answer("❌ Faqat yaratuvchi boshlaydi!")
        return
    count = get_lobby_player_count(lobby_id)
    if count < 4:
        await msg.answer(f"❌ Kamida 4 kishi kerak! Hozir: {count}")
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
        f"📅 Yil: <b>{year}</b>\n⚡ Voqea: <b>{scenario}</b>\n\n"
        f"<i>{scenario_desc}</i>\n\n"
        f"👥 Ishtirokchilar:\n{player_list}\n\n"
        f"⚠️ Har bir o'yinchi botga o'tib kartasini ochsin!\n👉 @{me.username}",
        parse_mode="HTML")
    failed = []
    for player in players:
        try:
            await bot.send_message(
                chat_id=player["user_id"],
                text=f"🃏 <b>Sizning kartangiz:</b>\n\n"
                     f"🏷️ Tur: {player['card_type']}\n"
                     f"👤 Nom: <b>{player['card_name']}</b>\n"
                     f"📝 Tavsif: {player['card_desc']}\n\n"
                     f"Kartangizni ochish uchun quyidagi tugmani bosing:",
                parse_mode="HTML",
                reply_markup=reveal_card_keyboard(lobby_id))
        except Exception as e:
            logging.error(f"PM yuborilmadi {player['user_id']}: {e}")
            failed.append(player['full_name'])
    if failed:
        await msg.answer(
            f"⚠️ Quyidagilarga xabar yuborilmadi (avval botga /start yuborishsin):\n"
            f"{chr(10).join(failed)}\n👉 @{me.username}",
            parse_mode="HTML")

@group_router.message(Command("stop"))
async def cmd_stop(msg: Message):
    lobbies = get_active_lobbies(chat_id=msg.chat.id)
    if not lobbies:
        # Active o'yinni ham tekshir
        await msg.answer("❌ Ochiq lobby yo'q!")
        return
    lobby = lobbies[0]
    if lobby["creator_id"] != msg.from_user.id and msg.from_user.id != ADMIN_ID:
        await msg.answer("❌ Faqat yaratuvchi yoki admin bekor qila oladi!")
        return
    update_lobby_status(lobby["id"], "finished")
    end_game(lobby["id"])
    await msg.answer("🛑 O'yin bekor qilindi!")

@group_router.message(Command("help"))
async def help_group(msg: Message):
    await msg.answer(
        "🤖 <b>Bunker Bot buyruqlari:</b>\n\n"
        "/newgame — yangi o'yin\n/join — qo'shilish\n"
        "/leave — chiqish\n/players — o'yinchilar\n"
        "/start_game — boshlash (yaratuvchi)\n"
        "/stop — bekor qilish",
        parse_mode="HTML")

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

    # ── DAILY BONUS ──
    if data == "check_sub":
        uid = call.from_user.id
        try:
            member = await bot.get_chat_member(MAIN_CHANNEL_ID, uid)
            is_subscribed = member.status not in ("left", "kicked")
        except:
            is_subscribed = True
        if is_subscribed:
            user = get_or_create_user(uid, call.from_user.username or "", call.from_user.full_name)
            await edit(
                f"✅ Rahmat! Xush kelibsiz!\n\n"
                f"☢️ <b>BUNKER</b> ga xush kelibsiz, {call.from_user.first_name}!\n"
                f"💰 BC: {user['bc_balance']}",
                main_menu())
        else:
            await call.answer("❌ Siz hali kanalga qo'shilmagansiz!", show_alert=True)

    elif data == "daily_bonus":
        get_or_create_user(uid, call.from_user.username or "", call.from_user.full_name)
        bonus, streak = claim_daily_bonus(uid)
        if bonus is None:
            info = get_bonus_info(uid)
            streak = info["streak"] if info else 0
            bonus_map = {1:15,2:20,3:30,4:40,5:50,6:75,7:100}
            tomorrow = bonus_map.get(min(streak+1,7),100)
            await edit(
                f"⏰ Kunlik bonusni allaqachon oldingiz!\n\n"
                f"🔥 Streak: {streak} kun\n⏳ Ertaga: +{tomorrow} BC",
                back_keyboard("back_main"))
        else:
            user = get_user(uid)
            streak_bar = "🔥"*min(streak,7) + "⬜"*max(0,7-streak)
            bonus_map = {1:15,2:20,3:30,4:40,5:50,6:75,7:100}
            next_b = bonus_map.get(min(streak+1,7),100)
            await edit(
                f"✅ <b>Kunlik bonus!</b>\n\n💰 +{bonus} BC\n"
                f"💳 Jami: {user['bc_balance']} BC\n\n"
                f"🔥 Streak: {streak} kun\n{streak_bar}\n\n"
                f"{'🎉 7 kunlik streak!' if streak>=7 else f'Ertaga: +{next_b} BC'}",
                back_keyboard("back_main"))

    # ── STATS ──
    elif data == "stats":
        u = get_user(uid)
        if not u:
            await edit("❌ Avval /start bosing!")
            return
        rank = get_rank(u["wins"])
        next_rank = get_next_rank(u["wins"])
        pct = round(u['wins']/u['games_played']*100) if u['games_played']>0 else 0
        ref_count = get_referral_count(uid)
        bonus_info = get_bonus_info(uid)
        streak = bonus_info["streak"] if bonus_info else 0
        if next_rank:
            progress = u["wins"] - rank["min_wins"]
            total = next_rank["min_wins"] - rank["min_wins"]
            filled = int(progress/total*10) if total>0 else 0
            bar = "█"*filled + "░"*(10-filled)
            rank_text = f"\n📈 Keyingi: <b>{next_rank['name']}</b>\n{bar} {u['wins']}/{next_rank['min_wins']}"
        else:
            rank_text = "\n🌟 Eng yuqori unvon!"
        await edit(
            f"📊 <b>{u['full_name']} statistikasi</b>\n\n"
            f"🏅 Unvon: {rank['name']}\n🎮 O'yinlar: {u['games_played']}\n"
            f"🏆 G'alabalar: {u['wins']} ({pct}%)\n💰 BC: {u['bc_balance']}\n"
            f"🔥 Streak: {streak} kun\n👥 Referallar: {ref_count}\n{rank_text}",
            back_keyboard("back_main"))

    # ── REFERRAL ──
    elif data == "referral":
        me = await bot.get_me()
        ref_count = get_referral_count(uid)
        thresholds = [3,6,10,15,21,28]
        next_t = next((t for t in thresholds if t>ref_count), None)
        link = f"https://t.me/{me.username}?start=ref_{uid}"
        await edit(
            f"🎁 <b>Referal tizimi</b>\n\nHavolangiz:\n<code>{link}</code>\n\n"
            f"👥 Taklif qilganlar: {ref_count} kishi\n\n"
            f"💰 Siz: +50 BC | Do'st: +30 BC\n"
            f"🏅 Har 3 kishi da unvon bonusi!\n"
            f"{'⏳ Keyingi bonus: '+str(next_t)+' kishida' if next_t else '🌟 Barcha bonuslar olindi!'}",
            back_keyboard("back_main"))

    # ── BACK ──
    elif data == "back_main":
        user = get_user(uid)
        bc = user['bc_balance'] if user else 0
        await edit(f"🏠 Asosiy menyu\n💰 BC: {bc}", main_menu())

    elif data == "profile":
        u = get_user(uid)
        pct = round(u['wins']/u['games_played']*100) if u['games_played']>0 else 0
        rank = get_rank(u["wins"])
        await edit(
            f"👤 <b>Profilingiz</b>\n\n📛 {u['full_name']}\n"
            f"🏅 Unvon: {rank['name']}\n💰 BC: {u['bc_balance']}\n"
            f"🎮 O'yinlar: {u['games_played']}\n🏆 G'alabalar: {u['wins']} ({pct}%)",
            back_keyboard("back_main"))

    elif data == "rating":
        top = get_top_users(10)
        medals = ["🥇","🥈","🥉"]
        text = "🏆 <b>TOP 10 O'YINCHILAR</b>\n\n"
        for i, u in enumerate(top):
            m = medals[i] if i<3 else f"{i+1}."
            rank = get_rank(u["wins"])
            text += f"{m} {u['full_name']} {rank['name']}\n   🏆 {u['wins']} | 💰 {u['bc_balance']} BC\n"
        await edit(text, back_keyboard("back_main"))

    elif data == "rules":
        await edit("📜 <b>Qoidalar bo'limlari:</b>", rules_keyboard())

    elif data.startswith("rules_"):
        section = data.replace("rules_","")
        rules_map = {
            "bot":"🤖 Bot qoidalari","kasb":"👮 Kasb qoidalari",
            "salomatlik":"💪 Salomatlik qoidalari","hunar":"🎯 Hunar qoidalari",
            "biografiya":"📖 Biografiya qoidalari",
        }
        key = rules_map.get(section)
        if key and key in RULES:
            await edit(f"<b>{key}</b>\n\n"+"\n".join(RULES[key]), back_keyboard("rules"))

    elif data == "connect_channel":
        user_states[uid] = "awaiting_channel_id"
        await edit(
            "🔗 Kanalingizning ID sini yuboring:\nMasalan: @mening_kanalim\n\n"
            "⚠️ Bot kanalga admin bo'lishi kerak!",
            back_keyboard("back_main"))

    elif data == "add_to_group":
        me = await bot.get_me()
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="➕ Guruhni tanlang",
                url=f"https://t.me/{me.username}?startgroup=start"
            )],
            [InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_main")]
        ])
        await edit(
            "➕ <b>Botni guruhga qo'shish</b>\n\n"
            "Quyidagi tugmani bosing — guruhlaringiz ro'yxati chiqadi.\n"
            "Kerakli guruhni tanlang, bot qo'shiladi!\n\n"
            "Qo'shilgandan so'ng guruhda /newgame yozing.",
            kb
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
        await edit(f"🛒 <b>MARKET</b> ({len(cards)} ta karta)", market_keyboard(cards, page))

    elif data.startswith("buy_card_"):
        card_id = int(data.split("_")[-1])
        card = get_market_card(card_id)
        u = get_user(uid)
        rank = get_rank(u["wins"])
        price = card["price"]
        discount_text = ""
        if rank.get("perk") == "discount" and discount_available(uid):
            price = int(price*0.9)
            discount_text = f"\n🎁 <b>Chegirma!</b> → {price} BC (-10%)"
        await edit(
            f"{card['emoji']} <b>{card['name']}</b>\n\n📝 {card['description']}\n\n"
            f"💰 Narx: {price} BC\n💳 Sizda: {u['bc_balance']} BC{discount_text}\n\nSotib olasizmi?",
            confirm_buy_keyboard(card_id))

    elif data.startswith("confirm_buy_"):
        card_id = int(data.split("_")[-1])
        card = get_market_card(card_id)
        u = get_user(uid)
        rank = get_rank(u["wins"])
        price = card["price"]
        if rank.get("perk") == "discount" and discount_available(uid):
            price = int(price*0.9)
            use_discount(uid)
        if spend_bc(uid, price):
            buy_market_card(uid, card_id)
            await call.answer(f"✅ {card['name']} sotib olindi!", show_alert=True)
            await edit("🛒 <b>MARKET</b>", market_keyboard(get_all_market_cards()))
        else:
            u = get_user(uid)
            needed = price - u['bc_balance']
            await edit(
                f"{card['emoji']} <b>{card['name']}</b>\n\n❌ <b>BC yetarli emas!</b>\n\n"
                f"💰 Narx: {price} BC\n💳 Sizda: {u['bc_balance']} BC\n"
                f"📉 Yetishmaydi: {needed} BC\n\n"
                f"O'yin o'ynab BC to'plang:\n• G'alaba: +75-125 BC\n• Kunlik bonus: /bonus",
                back_keyboard("market"))

    # ── LOBBY (private) ──
    elif data == "create_lobby":
        cards = get_recent_cards(50)
        if not cards:
            await call.answer("❌ Admin karta yaratsin!", show_alert=True)
            return
        existing = [l for l in get_active_lobbies() if l["creator_id"] == uid]
        if existing:
            await call.answer("❌ Sizda allaqachon ochiq lobby bor!", show_alert=True)
            return
        lobby_id = create_lobby(uid, cid)
        join_lobby(lobby_id, uid, random.choice(cards)["id"])
        await edit(
            f"🏠 <b>Lobby #{lobby_id} yaratildi!</b>\n\n"
            f"👤 Yaratuvchi: {call.from_user.full_name}\n"
            f"👥 O'yinchilar: 1/7 | ⏳ Min: 4 kishi\n\n"
            f"Boshqalar qo'shilishini kuting!",
            lobby_action_keyboard(lobby_id, is_creator=True, joined=True))

    elif data == "view_lobbies":
        lobbies = get_active_lobbies()
        if not lobbies:
            await edit("😔 Hozircha ochiq lobby yo'q.", back_keyboard("back_main"))
            return
        for l in lobbies:
            l["player_count"] = get_lobby_player_count(l["id"])
        await edit(f"👥 <b>Ochiq lobbylar:</b> {len(lobbies)} ta", lobbies_keyboard(lobbies))

    elif data.startswith("join_lobby_"):
        lobby_id = int(data.split("_")[-1])
        lobby = get_lobby(lobby_id)
        if not lobby or lobby["status"] != "waiting":
            await call.answer("❌ Lobby mavjud emas yoki o'yin boshlangan!", show_alert=True)
            return
        if get_lobby_player_count(lobby_id) >= 7:
            await call.answer("❌ Lobby to'ldi!", show_alert=True)
            return
        if not is_in_lobby(lobby_id, uid):
            cards = get_recent_cards(50)
            if not cards:
                await call.answer("❌ Kartalar yo'q!", show_alert=True)
                return
            join_lobby(lobby_id, uid, random.choice(cards)["id"])
        new_count = get_lobby_player_count(lobby_id)
        is_creator = lobby["creator_id"] == uid
        await edit(
            f"🏠 <b>Lobby #{lobby_id}</b>\n\n👥 O'yinchilar: {new_count}/7\n✅ Siz lobbydasiz!",
            lobby_action_keyboard(lobby_id, is_creator=is_creator, joined=True))

    elif data.startswith("leave_lobby_"):
        lobby_id = int(data.split("_")[-1])
        lobby = get_lobby(lobby_id)
        if not lobby:
            await edit("❌ Lobby topilmadi.", back_keyboard("back_main"))
            return
        if lobby["status"] != "waiting":
            await call.answer("❌ O'yin boshlangan!", show_alert=True)
            return
        # Yaratuvchi chiqsa — lobby bekor qilinadi
        if lobby["creator_id"] == uid:
            update_lobby_status(lobby_id, "finished")
            end_game(lobby_id)
            await edit("🛑 Lobby bekor qilindi!", back_keyboard("back_main"))
            return
        if leave_lobby(lobby_id, uid):
            await call.answer("✅ Lobbydan chiqdingiz!")
            new_count = get_lobby_player_count(lobby_id)
            await edit(
                f"🏠 <b>Lobby #{lobby_id}</b>\n\n👥 O'yinchilar: {new_count}/7\n\n"
                f"Qaytib qo'shilish uchun tugmani bosing:",
                lobby_action_keyboard(lobby_id, joined=False))
        else:
            await call.answer("❌ Siz bu lobbyda emassiz!", show_alert=True)

    elif data.startswith("start_game_"):
        lobby_id = int(data.split("_")[-1])
        lobby = get_lobby(lobby_id)
        if not lobby or lobby["creator_id"] != uid:
            await call.answer("❌ Faqat yaratuvchi boshlaydi!", show_alert=True)
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
            f"🚨 <b>O'YIN BOSHLANDI!</b>\n\n📅 Yil: <b>{year}</b>\n"
            f"⚡ Voqea: <b>{scenario}</b>\n\n<i>{scenario_desc}</i>\n\n"
            f"👥 Ishtirokchilar:\n{player_list}\n\n"
            f"⚠️ Har bir o'yinchi botga o'tib kartasini ochsin!\n👉 @{me.username}")
        for player in players:
            try:
                await bot.send_message(
                    chat_id=player["user_id"],
                    text=f"🃏 <b>Sizning kartangiz:</b>\n\n"
                         f"🏷️ Tur: {player['card_type']}\n"
                         f"👤 Nom: <b>{player['card_name']}</b>\n"
                         f"📝 Tavsif: {player['card_desc']}\n\n"
                         f"Kartangizni ochish uchun tugmani bosing:",
                    parse_mode="HTML",
                    reply_markup=reveal_card_keyboard(lobby_id))
            except Exception as e:
                logging.error(f"PM yuborilmadi {player['user_id']}: {e}")

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
        await call.answer(f"✅ Ochildi: {player['card_name']}")

        # Tezlik bonusi
        first = give_first_reveal_bonus(lobby_id, uid)
        if first:
            try:
                await bot.send_message(uid, "⚡ Birinchi karta ochdingiz! +3 BC!")
            except:
                pass

        lobby = get_lobby(lobby_id)
        group_chat_id = lobby["chat_id"] if lobby else cid
        await bot.send_message(group_chat_id,
            f"👁️ <b>{player['full_name']}</b> kartasini ochdi:\n\n"
            f"🏷️ {player['card_type']}\n👤 <b>{player['card_name']}</b>\n"
            f"📝 <i>{player['card_desc']}</i>",
            parse_mode="HTML")
        if all_revealed:
            await asyncio.sleep(2)
            asyncio.create_task(start_voting_phase(group_chat_id, lobby_id))

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
            await call.answer("😱 Bu raundda ovoz bera olmaysiz!", show_alert=True)
            return
        add_vote(lobby_id, uid, target_id)
        target = game["players"].get(target_id)
        await call.answer(f"✅ {target['full_name']} ga ovoz berdingiz!")

    # ── ADMIN ──
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
        await edit(f"✅ Tur: <b>{ct}</b>\n\nKarta nomini yozing:")

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
        await edit("✏️ Karta ID sini yozing:", back_keyboard("admin_panel"))

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
        f"⏰ <b>1 DAQIQA MUHOKAMA! (Raund {game['round']})</b>\n\n"
        "Kimni bunkerdan chiqarasiz? Muhokama qiling!\n60 soniyadan so'ng ovoz berish boshlanadi...",
        parse_mode="HTML")
    await asyncio.sleep(60)

    game = get_game(lobby_id)
    if not game:
        return

    await bot.send_message(chat_id,
        "🗳️ <b>OVOZ BERISH! 60 SONIYA!</b>\n\nKimni o'yindan chiqarasiz?",
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
            f"✅ Qolgan o'yinchilar: {alive_count}\nKeyingi raund boshlanmoqda...",
            parse_mode="HTML")
        await asyncio.sleep(3)
        asyncio.create_task(start_voting_phase(chat_id, lobby_id))

async def finish_game(chat_id, lobby_id):
    game = get_game(lobby_id)
    winners = get_winners(lobby_id)
    winners_data = [game["players"][wid] for wid in winners if wid in game["players"]]
    # Birinchi chiqarilgandan oxirigacha
    eliminated_data = [game["players"][uid] for uid in game["eliminated"] if uid in game["players"]]
    winner_names = " va ".join([p["full_name"] for p in winners_data])
    duration_minutes = game["round"] * 2

    await bot.send_message(chat_id,
        f"🎉 <b>O'YIN TUGADI!</b>\n\n🏆 G'oliblar: <b>{winner_names}</b>\n\n⏳ Grok tahlili...",
        parse_mode="HTML")

    grok_analysis = await generate_group_result(
        winners_data, eliminated_data, game["scenario"], game["year"], duration_minutes)

    bc_amount = 125 if duration_minutes >= 20 else 75

    eliminated_list = "\n".join([
        f"{i+1}. {p['full_name']} ({p['card_name']})"
        for i, p in enumerate(eliminated_data)])
    winners_list = "\n".join([f"🥇 {p['full_name']} ({p['card_name']})" for p in winners_data])

    await bot.send_message(chat_id,
        f"📊 <b>O'YIN NATIJASI</b>\n\n"
        f"☢️ {game['scenario']} ({game['year']})\n"
        f"⏱️ {duration_minutes} daqiqa | {game['round']-1} raund\n\n"
        f"🏆 <b>G'oliblar:</b>\n{winners_list}\n\n"
        f"💀 <b>Chiqarilganlar (tartibda):</b>\n{eliminated_list}\n\n"
        f"🔮 <b>Grok tahlili:</b>\n<i>{grok_analysis}</i>\n\n"
        f"💰 G'oliblar +{bc_amount} BC oldi!\n👉 Keyingi o'yin: /newgame",
        parse_mode="HTML")

    for wid in winners:
        update_stats(wid, won=True)
        add_bc(wid, bc_amount)
        u = get_user(wid)
        if u:
            await check_and_notify_rank(wid, u["wins"])
            rank = get_rank(u["wins"])
            if rank.get("bonus_bc", 0) > 0:
                add_bc(wid, rank["bonus_bc"])
        try:
            await bot.send_message(wid,
                f"🏆 G'olib bo'ldingiz! +{bc_amount} BC!\n"
                f"💰 Jami: {u['bc_balance'] if u else '?'} BC")
        except:
            pass

    for p in eliminated_data:
        update_stats(p["user_id"], won=False)

    end_game(lobby_id)

async def check_and_notify_rank(user_id, wins):
    rank = get_rank(wins)
    prev_rank = get_rank(wins-1)
    if rank["name"] != prev_rank["name"]:
        perk_text = {
            "discount": "\n🎁 Imtiyoz: Marketda bir marta -10% chegirma!",
            "see_votes": "\n🎁 Imtiyoz: Ovoz natijasini ko'rish!",
            "special_card": "\n🎁 Imtiyoz: Lobby yaratganda maxsus karta!",
            "legend_card": "\n🎁 Imtiyoz: Maxsus Legend karta!",
        }.get(rank.get("perk",""), "")
        try:
            await bot.send_message(user_id,
                f"🎉 <b>YANGI UNVON!</b>\n\nSiz endi: {rank['name']}\n"
                f"G'alabalar: {wins}{perk_text}",
                parse_mode="HTML")
        except:
            pass

# ═══════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════

# ═══════════════════════════════════════════════════════════
# BOT GURUHGA QO'SHILGANDA
# ═══════════════════════════════════════════════════════════

@dp.my_chat_member()
async def on_bot_added(event):
    from aiogram.types import ChatMemberUpdated
    new_status = event.new_chat_member.status
    chat = event.chat
    chat_type = chat.type

    if chat_type not in ("group", "supergroup"):
        return

    if new_status == "member" or new_status == "administrator":
        # Guruh bazaga yoziladi
        conn = get_conn()
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS groups (
            chat_id INTEGER PRIMARY KEY,
            title TEXT,
            added_at TEXT DEFAULT CURRENT_TIMESTAMP
        )''')
        c.execute("INSERT OR REPLACE INTO groups (chat_id, title) VALUES (?,?)",
                  (chat.id, chat.title or "Nomsiz guruh"))
        conn.commit()
        conn.close()

        # Xush kelibsiz xabari
        try:
            await bot.send_message(
                chat.id,
                f"☢️ <b>BUNKER</b> boti guruhga qo'shildi!\n\n"
                f"O'yin boshlash uchun:\n"
                f"1️⃣ /newgame — yangi o'yin oching\n"
                f"2️⃣ /join — qo'shiling\n"
                f"3️⃣ /start_game — boshlang!\n\n"
                f"Kamida 4 kishi kerak. Omad! 🏆",
                parse_mode="HTML"
            )
        except:
            pass

    elif new_status in ("left", "kicked"):
        # Guruhdan chiqarildi — lobbylarni bekor qil
        conn = get_conn()
        c = conn.cursor()
        c.execute("UPDATE lobbies SET status='finished' WHERE chat_id=? AND status='waiting'",
                  (chat.id,))
        conn.commit()
        conn.close()
        end_game(chat.id)

async def main():
    init_db()
    init_market_cards()
    init_bonus_tables()

    private_commands = [
        BotCommand(command="start", description="🏠 Botni boshlash"),
        BotCommand(command="bonus", description="☀️ Kunlik bonus"),
        BotCommand(command="stats", description="📊 Statistikam"),
        BotCommand(command="refer", description="🎁 Do'st taklif qilish"),
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

    print("🚀 Bunker Bot ishga tushdi!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
