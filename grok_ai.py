import aiohttp
import os

GROK_API_KEY = os.getenv("GROK_API_KEY")
GROK_API_URL = "https://api.x.ai/v1/chat/completions"

async def _ask_grok(prompt, max_tokens=1200, temperature=0.97):
    try:
        headers = {
            "Authorization": f"Bearer {GROK_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "grok-3",
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Sen Bunker o'yinining iste'dodli va hazilkash hikoyachi assistantisan. "
                        "O'zbek tilida yozasan. Uslub: dramatik, o'tkir, ba'zan kulgili va istehzoli — "
                        "xuddi yaxshi yozuvchi kabi. Personajlarning barcha xususiyatlarini (kasb, sog'liq, "
                        "yosh, bagaj, genetika, fobiya, ijtimoiy holat va boshqalar) tahlilga to'liq qo'shasan. "
                        "Voqea turining xarakterini — zombie, AI, meteor, suv toshqini va h.k. — "
                        "hikoyaga organik ravishda singdirassan. "
                        "Hazil va drama uyg'unlashganda eng yaxshi chiqadi."
                    )
                },
                {"role": "user", "content": prompt}
            ],
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(GROK_API_URL, headers=headers, json=payload) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data["choices"][0]["message"]["content"]
                else:
                    return None
    except Exception:
        return None


async def get_scenario_description(scenario, year):
    prompt = (
        f"Bunker o'yini boshlanmoqda. Qisqacha dramatik kirish yoz:\n"
        f"Voqea: {scenario}\nYil: {year}\n\n"
        f"2-3 jumlada dramatik va qo'rqinchli tarzda tasvirla. "
        f"Odamlar bunkerga qochyapti, vaqt oz qoldi. O'zbek tilida."
    )
    result = await _ask_grok(prompt, max_tokens=220, temperature=0.9)
    return result or f"{year}-yilda {scenario} boshlandi. Bunker eshiklari yopilmoqda..."


async def generate_group_result(winners_data, eliminated_data, scenario, year, duration_minutes):
    """G'oliblar uchun chuqur va kulgili tahlil."""

    winners_text = ""
    for w in winners_data:
        cards = w.get("all_cards", [])
        cards_lines = "\n    ".join([
            f"• {c.get('card_type','?')}: {c.get('name','?') } — {c.get('description','')}"
            for c in cards
        ])
        winners_text += f"\n👤 {w['full_name']}:\n    {cards_lines}\n"

    survival = "uzoq muddat (o'nlab yillar)" if duration_minutes >= 20 else "bir necha yil"

    prompt = f"""Bunker o'yini tugadi.
Voqea: {scenario} | Yil: {year}

━━━ OMON QOLGANLAR (barcha xususiyatlari) ━━━
{winners_text}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Faqat g'oliblar haqida KULGILI VA CHUQUR hikoya yoz — {survival} davomida.

QOIDALAR:
1. Har bir xususiyatni (kasb, sog'liq, yosh, bagaj, genetika, hunar, ijtimoiy) hikoyaga qo'sh
2. Kulgili xususiyatlardan maksimal foydalanlan — masalan bagajda "yashil soyabon" bor bo'lsa meteordan saqladimi? "Qunduz tishlari" genetikasi hayotda qanday yordam berdi? Hazilga aylantir!
3. Sog'liq ta'siri: anemiya=ko'p charchaydi, yurak yetishmovchiligi=og'ir ish qila olmaydi
4. Yosh + jins + sog'liq asosida turmush/farzand masalasi — ANIQ ayt, umumiy gaplar emas
5. Bagaj amaliy foydasi: durbin→uzoqni ko'rdi, soyabon→kul yomg'iridan himoya va h.k.
6. Kasb va hunar → bunkerdagi aniq roli
7. Voqeaga mos detal: meteor→toshlar yog'di, atmosfera o'zgardi
8. Kulgili + dramatik = mukammal hikoya

Uslub: kichik hikoya, o'tkir, ba'zan istehzoli. 6-8 jumla. O'zbek tilida.
To'g'ridan personajlar haqida boshlang."""

    result = await _ask_grok(prompt, max_tokens=1400, temperature=0.97)
    return result or f"🏆 G'oliblar bunkerda {survival} yashab, insoniyatni qayta qurdilar."


async def analyze_winners(winners_data, scenario, year):
    """Eski funksiya — moslik uchun"""
    text = "\n".join([f"• {w.get('full_name','?')}" for w in winners_data])
    prompt = f"Bunker o'yini, voqea: {scenario} ({year}).\nG'oliblar:\n{text}\nKelajagini yoz. O'zbek tilida, 150 so'z."
    result = await _ask_grok(prompt, max_tokens=500)
    return result or "🔮 Ular insoniyatni qayta qurdilar."
