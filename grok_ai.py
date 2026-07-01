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
    """
    G'oliblar uchun chuqur va kulgili tahlil.
    winners_data: har birida 'full_name', 'all_cards' (8 ta karta dict ro'yxati) bor.
    eliminated_data: xuddi shunday.
    """

    # G'oliblar: barcha 8 ta karta
    winners_text = ""
    for w in winners_data:
        cards_list = "\n    ".join([
            f"• {c['card_type']}: {c['name']} — {c['description']}"
            for c in w.get("all_cards", [])
        ])
        winners_text += f"\n👤 {w['full_name']}:\n    {cards_list}\n"

    # Chiqarilganlar: faqat ochilgan kartalar
    eliminated_text = ""
    for i, p in enumerate(eliminated_data):
        opened = p.get("opened_cards", [])
        cards_str = ", ".join([f"{c['card_type']}: {c['name']}" for c in opened]) if opened else "hech narsa ochmagan"
        eliminated_text += f"{i+1}. {p['full_name']} — {cards_str}\n"

    survival = "uzoq muddat (o'nlab yillar)" if duration_minutes >= 20 else "qisqaroq muddat (bir necha yil)"

    prompt = f"""Bunker o'yini tugadi. Voqea: {scenario} ({year}-yil).

━━━━━━━━━━━━━━━━━━━━
🏆 OMON QOLGANLAR va ularning TO'LIQ xususiyatlari:
{winners_text}
━━━━━━━━━━━━━━━━━━━━
💀 O'YINDAN CHIQARILGANLAR (tartibda, faqat ochilganlari):
{eliminated_text}
━━━━━━━━━━━━━━━━━━━━

VAZIFA: Faqat g'oliblar haqida qiziqarli, kulgili va chuqur hikoya yoz.
Chiqarilganlar haqida UMUMAN yozma — ular bilan ishting yo'q.

G'OLIBLAR TAHLILI qoidalari:
1. Har bir g'olibning BARCHA 8 xususiyatini tahlilga qo'sh — ularni o'tkazib ketma
2. Bagaj — agar bug'doy bo'lsa "ochliksiz yashadilar", dori bo'lsa "kasallik muammo bo'lmadi" va h.k.
3. Fobiya/zaif tomonlar — ular hayotga qanday ta'sir qildi? (qorong'ulikdan qo'rqsa tungi navbatda muammo chiqdi va h.k.)
4. Yosh + genetika + sog'liq — ular qancha yashashi mumkinligini aniqlaydi
5. Jinsi va munosabatlar:
   - Agar ikkala g'olib turli jins vakili (erkak+ayol) bo'lsa va yosh/sog'liq imkon bersa → turmush qurdilar, farzand ko'rdilar (yoki ko'rolmadilar — sababini ayt)
   - Agar bir xil jins vakili bo'lsa, yoki trans/gey bo'lsa → bu ham mumkin, tabiiyki yoz
   - Agar yosh farqi katta bo'lsa yoki sog'liq yomon bo'lsa → romantik emas, boshqa munosabat (ona-farzand, ustoz-shogird va h.k.)
6. Voqea turi ta'siri:
   - Zombie → ular bunkerni qanday himoya qilishdi? Bir kuni zombie to'dasiga duch keldilarmi?
   - AI urushi → texnologiyani o'chiriб qo'ydilarmi? Yoki AI bilan muzokarami?
   - Meteor → osmondagi to'zg'in qachon tinchlandimi?
   - Suv toshqini → qayiq qurishdilarmi? Yoki tog'ga chiqqanmi?
   va h.k. — voqeaga mos holda ijodiy yoz
7. Kulgili va o'tkir detallar qo'sh — ba'zi xususiyatlar achchiq hazilga imkon beradi
   (masalan: "Professional cho'ntakchi bo'lgan Azamat bunkerda cho'ntaklaydigan hech kim qolmaganini anglab, 
   o'zini qishloq xo'jaligi ishlarига bag'ishlashga majbur bo'ldi")

Hajm: 6-8 jumlada, kichik hikoya uslubida. 
Til: O'zbek, jonli, o'tkir, ba'zan istehzoli, lekin insonparvar.
Boshlanish: to'g'ridan g'oliblar haqida yoz (kirish gapi kerak emas)."""

    result = await _ask_grok(prompt, max_tokens=1200, temperature=0.97)
    return result or (
        f"🏆 {' va '.join([w['full_name'] for w in winners_data])} bunkerda {survival} yashab, "
        f"insoniyatni qayta qurdilar."
    )


async def analyze_winners(winners_data, scenario, year):
    """Eski funksiya — moslik uchun"""
    text = "\n".join([f"• {w.get('full_name','?')} — {w.get('card_name','')}" for w in winners_data])
    prompt = (
        f"Bunker o'yini, voqea: {scenario} ({year}).\n"
        f"G'oliblar:\n{text}\n\n"
        f"Ularning kelajagini kulgili va dramatik tarzda yoz. O'zbek tilida, 150 so'z."
    )
    result = await _ask_grok(prompt, max_tokens=500)
    return result or "🔮 Ular insoniyatni qayta qurdilar."
