import aiohttp
import os

GROK_API_KEY = os.getenv("GROK_API_KEY")
GROK_API_URL = "https://api.x.ai/v1/chat/completions"

async def _ask_grok(prompt, max_tokens=800, temperature=0.9):
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
                    "content": "Sen Bunker o'yinining hikoyachi AI assistantisan. O'zbek tilida yozasan. Dramatik, qiziqarli va hissiy uslubda yozasan."
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
    """O'yin boshlanishida voqea tavsifi"""
    prompt = (
        f"Bunker o'yini boshlanmoqda. Qisqacha dramatik kirish yoz:\n"
        f"Voqea: {scenario}\n"
        f"Yil: {year}\n\n"
        f"2-3 jumlada dramatik va qo'rqinchli tarzda tasvirla. "
        f"Odamlar bunkerga qochyapti, vaqt oz. O'zbek tilida."
    )
    result = await _ask_grok(prompt, max_tokens=200, temperature=0.8)
    return result or f"{year}-yilda {scenario} boshlandi. Bunker eshiklari yopilmoqda..."

async def generate_group_result(winners_data, eliminated_data, scenario, year, duration_minutes):
    """
    O'yin tugagach guruhga yuborish uchun Grok tahlili.
    - G'oliblar kelajagi (bolali, insoniyatga yordam...)
    - Chiqarilganlar taqdiri (birinchi kim o'ldi, qanday halok bo'ldi...)
    """
    # G'oliblar
    winners_text = ""
    for w in winners_data:
        winners_text += f"• {w['full_name']} — {w['card_type']}: {w['card_name']} ({w['card_desc']})\n"

    # Chiqarilganlar — tartibda (birinchi chiqarilgan = birinchi o'lgan)
    eliminated_text = ""
    for i, p in enumerate(eliminated_data):
        eliminated_text += f"{i+1}. {p['full_name']} — {p['card_type']}: {p['card_name']} ({p['card_desc']})\n"

    survival_quality = "uzoq muddat (bir necha o'n yil)" if duration_minutes >= 20 else "qisqa muddat (bir necha yil)"

    prompt = f"""Bunker o'yini tugadi. Sen bu voqeaning hikoyachisissan.

🌍 Voqea: {scenario}
📅 Yil: {year}

🏆 BUNKERDA OMON QOLGANLAR:
{winners_text}

💀 CHIQARILGANLAR (birinchi chiqarilgandan oxirigacha):
{eliminated_text}

Endi IKKITA ALOHIDA qism yoz:

**1. CHIQARILGANLAR TAQDIRI:**
Har bir chiqarilgan odam {scenario} da qanday halok bo'ldi? 
Birinchi chiqarilgan birinchi o'ldi. Ularning kasbı, salomatligi, bagaji va boshqa xususiyatlarini hisobga ol.
Masalan: zombie larga yem bo'ldimi, radiatsiyadan o'ldimi, boshqalari tomonidan o'ldirildi, qochib ketdimi...
Har bir kishi uchun 1-2 jumlada yoz.

**2. G'OLIBLAR KELAJAGI:**
Omon qolgan {len(winners_data)} kishi {survival_quality} yashadi.
Ularning kartalarini hisobga olib kelajagini yoz:
- Oila qurdilarmi, bolali bo'ldilarmi?
- Insoniyatni qayta qurdilarmi?
- Bunkerdan qachon chiqdilar?
- Ularning eng katta yutuqlari nima bo'ldi?
3-4 jumlada yoz.

Dramatik, hissiy va qiziqarli uslubda yoz. O'zbek tilida."""

    result = await _ask_grok(prompt, max_tokens=900, temperature=0.9)
    return result or (
        f"💀 **Chiqarilganlar:** {scenario} da halok bo'ldilar — "
        f"{', '.join([p['full_name'] for p in eliminated_data])}.\n\n"
        f"🏆 **G'oliblar:** {' va '.join([p['full_name'] for p in winners_data])} "
        f"bunkerda {survival_quality} yashab, insoniyatni qayta qurdilar."
    )

async def analyze_winners(winners_data, scenario, year):
    """Faqat g'oliblar uchun (eski funksiya — hali ishlatiladi)"""
    winners_text = ""
    for w in winners_data:
        winners_text += f"• {w['full_name']} — {w['card_name']} ({w['card_desc']})\n"

    prompt = (
        f"Bunker o'yinida voqea: {scenario} ({year}-yil)\n\n"
        f"Omon qolganlar:\n{winners_text}\n\n"
        f"Ularning kelajagini yoz: oila qurdilarmi, insoniyatga qanday yordam berdilar, "
        f"qancha yashashdi. Har birining karta xususiyatlarini hisobga ol. "
        f"O'zbek tilida, 150-200 so'z, dramatik uslubda."
    )
    result = await _ask_grok(prompt, max_tokens=600)
    return result or "🔮 Ular insoniyatni qayta qurdilar va avlodlar ularni eslab qoldi."
