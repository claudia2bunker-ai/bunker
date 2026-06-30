import aiohttp
import os

GROK_API_KEY = os.getenv("GROK_API_KEY")
GROK_API_URL = "https://api.x.ai/v1/chat/completions"

async def _ask_grok(prompt, max_tokens=900, temperature=0.95):
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
                        "Sen Bunker o'yinining hikoyachi AI assistantisan. O'zbek tilida yozasan. "
                        "Insonparvar, dramatik, hissiy va batafsil uslubda yozasan — xuddi kichik "
                        "hikoya yozayotgandek. Personajlarning his-tuyg'ulari, taqdiri, "
                        "munosabatlari (turmush qurish, do'stlik, dushmanlik, kasallik, "
                        "farzand ko'rish yoki ko'rolmaslik kabi) haqida ijodiy va to'liq yoz."
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
        f"Odamlar bunkerga qochyapti, vaqt oz. O'zbek tilida."
    )
    result = await _ask_grok(prompt, max_tokens=200, temperature=0.8)
    return result or f"{year}-yilda {scenario} boshlandi. Bunker eshiklari yopilmoqda..."

async def generate_group_result(winners_data, eliminated_data, scenario, year, duration_minutes):
    """
    O'yin tugagach guruhga yuborish uchun Grok tahlili.
    Har bir o'yinchining 'card_name' maydonida barcha ochilgan xususiyatlari bor
    (masalan: "Kasb: Shifokor; Salomatlik: Sog'lom; Biografiya: Yosh...").
    """
    winners_text = ""
    for w in winners_data:
        winners_text += f"• {w['full_name']} — {w['card_name']}\n"

    eliminated_text = ""
    for i, p in enumerate(eliminated_data):
        eliminated_text += f"{i+1}. {p['full_name']} — {p['card_name']}\n"

    survival_quality = "uzoq muddat (bir necha o'n yil)" if duration_minutes >= 20 else "qisqa muddat (bir necha yil)"

    prompt = f"""Bunker o'yini tugadi. Sen bu voqeaning hikoyachisissan. Hikoyani BOYITIB, batafsil va his-tuyg'ularga boy qilib yoz.

🌍 Voqea: {scenario}
📅 Yil: {year}

🏆 BUNKERDA OMON QOLGANLAR (xususiyatlari):
{winners_text}

💀 CHIQARILGANLAR (birinchi chiqarilgandan oxirigacha, xususiyatlari):
{eliminated_text}

Endi IKKITA ALOHIDA qism yoz — har biri kichik hikoyachalar kabi bo'lsin:

**1. CHIQARILGANLAR TAQDIRI:**
Har bir chiqarilgan odam {scenario} sharoitida qanday halok bo'ldi yoki nima bo'ldi?
Birinchi chiqarilgan birinchi halok bo'ldi (yoki eng og'ir holatga tushdi).
Ularning kasbi, salomatligi, bagaji va boshqa xususiyatlarini albatta hisobga ol va ulardan foydalan.
Masalan: zombie larga yem bo'ldimi, radiatsiyadan o'ldimi, boshqa omon qolganlar tomonidan o'ldirildimi, 
qochib ketib boshqa joyda halok bo'ldimi, kasalligi tufayli chiday olmadimi...
Har bir kishi uchun 1-2 jumlada, lekin his-tuyg'uli va aniq yoz.

**2. G'OLIBLAR KELAJAGI — BU QISMNI ALOHIDA BOYITIB YOZ:**
Omon qolgan {len(winners_data)} kishi {survival_quality} yashadi.
Ularning xususiyatlarini chuqur hisobga olib, KICHIK HIKOYA kabi yoz:
- Agar ular turli jinsdagi bo'lsa va yosh/sog'lom bo'lsa — turmush qurdilarmi? Farzand ko'rdilarmi?
- Agar ulardan biri kasal yoki sog'lig'i yomon bo'lsa — bu ularning kelajagiga (masalan farzand ko'rish, 
  uzoq yashash) qanday ta'sir qildi? Aniq ayt — masalan "X kasalligi tufayli farzand ko'ra olmadilar" yoki 
  "Y dan biri erta vafot etdi, ikkinchisi yolg'iz qoldi".
- Agar ikkalasi ham bir xil jinsdan bo'lsa yoki yosh farqi katta bo'lsa — birodarlik, do'stlik, 
  hamkorlik asosida insoniyatni qayta qurdilarmi?
- Insoniyatga qanday foyda keltirdilar? (yangi qishloq qurish, davolash, ta'lim berish va h.k.)
- Ularning eng katta yutug'i yoki fojiasi nima bo'ldi?
- Bunkerdan qachon va qanday chiqdilar?

4-6 jumlada, chuqur va his-tuyg'uli, kichik hikoya uslubida yoz. Aniq tafsilotlar bilan to'ldir 
(umumiy gaplar emas, balki "kim, nima qildi, nima natija berdi" kabi konkret). O'zbek tilida."""

    result = await _ask_grok(prompt, max_tokens=1100, temperature=0.95)
    return result or (
        f"💀 **Chiqarilganlar:** {scenario} sharoitida halok bo'ldilar — "
        f"{', '.join([p['full_name'] for p in eliminated_data])}.\n\n"
        f"🏆 **G'oliblar:** {' va '.join([p['full_name'] for p in winners_data])} "
        f"bunkerda {survival_quality} yashab, insoniyatni qayta qurdilar."
    )

async def analyze_winners(winners_data, scenario, year):
    """Eski funksiya — moslik uchun saqlanadi"""
    winners_text = ""
    for w in winners_data:
        winners_text += f"• {w['full_name']} — {w.get('card_name', '')}\n"

    prompt = (
        f"Bunker o'yinida voqea: {scenario} ({year}-yil)\n\n"
        f"Omon qolganlar:\n{winners_text}\n\n"
        f"Ularning kelajagini yoz: oila qurdilarmi, insoniyatga qanday yordam berdilar, "
        f"qancha yashashdi. Har birining xususiyatlarini hisobga ol. "
        f"O'zbek tilida, 150-200 so'z, dramatik uslubda."
    )
    result = await _ask_grok(prompt, max_tokens=600)
    return result or "🔮 Ular insoniyatni qayta qurdilar va avlodlar ularni eslab qoldi."
