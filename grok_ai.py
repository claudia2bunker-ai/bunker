import aiohttp
import os

GROK_API_KEY = os.getenv("GROK_API_KEY")
GROK_API_URL = "https://api.x.ai/v1/chat/completions"

async def analyze_winners(winners_data, scenario, year):
    winners_text = ""
    for w in winners_data:
        winners_text += f"\n👤 {w['full_name']}:\n   - Karta: {w['card_name']} ({w['card_type']})\n   - Tavsif: {w['card_desc']}\n"

    prompt = (f"Bunker o'yinida voqea: {scenario} ({year}-yil)\n\n"
              f"Omon qolgan ishtirokchilar:\n{winners_text}\n\n"
              f"Ularning bunkerdan chiqqandan keyingi hayotini qiziqarli va ijodiy tarzda yoz. "
              f"Har bir kishining karta xususiyatlarini hisobga ol. "
              f"Ular qancha yashashdi, nima qilishdi, insoniyatga qanday foyda keltirdi. "
              f"Javob O'zbek tilida, 200-300 so'z, emotsional uslubda.")
    try:
        headers = {
            "Authorization": f"Bearer {GROK_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "grok-3",
            "messages": [
                {"role": "system", "content": "Sen Bunker o'yinining hikoyachi AI assistantisan. O'zbek tilida yozasan."},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 800,
            "temperature": 0.9
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(GROK_API_URL, headers=headers, json=payload) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data["choices"][0]["message"]["content"]
                else:
                    return f"🔮 G'oliblar omon qolishdi va insoniyatni qayta qurdi!"
    except Exception as e:
        return f"🔮 G'oliblar omon qolishdi va insoniyatni qayta qurdi!"

async def get_scenario_description(scenario, year):
    prompt = (f"Bunker o'yini uchun qisqacha kirish yoz:\n"
              f"Voqea: {scenario}\nYil: {year}\n\n"
              f"2-3 jumlada dramatik va hayajonli tarzda voqeani tasvirla. O'zbek tilida.")
    try:
        headers = {
            "Authorization": f"Bearer {GROK_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "grok-3",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 200,
            "temperature": 0.8
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(GROK_API_URL, headers=headers, json=payload) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data["choices"][0]["message"]["content"]
                else:
                    return f"{year}-yilda {scenario} boshlandi. Bunker eshiklari yopilmoqda..."
    except Exception:
        return f"{year}-yilda {scenario} boshlandi. Bunker eshiklari yopilmoqda..."
