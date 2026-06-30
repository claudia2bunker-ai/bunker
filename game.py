import random
from database import get_8_cards_for_player, eliminate_player, update_lobby_status

SCENARIOS = [
    {"event": "☢️ Yadro urushi boshlandi", "years": ["2031","2045","2067","2089"]},
    {"event": "🧟 Zombie apokalipsisi", "years": ["2025","2033","2041","2055"]},
    {"event": "🤖 AI ga qarshi jang", "years": ["2035","2048","2060","2075"]},
    {"event": "☄️ Meteor yerlarga yaqinlashmoqda", "years": ["2029","2038","2052","2071"]},
    {"event": "🦖 Dinozavrlar qayta tirildi", "years": ["2027","2044","2058","2083"]},
    {"event": "👽 O'zga sayyoraliklar hujumi", "years": ["2030","2047","2063","2091"]},
    {"event": "🌊 Global suv toshqini", "years": ["2026","2039","2054","2078"]},
    {"event": "🦠 Noma'lum virus pandemiyasi", "years": ["2026","2031","2043","2066"]},
    {"event": "🌋 Super vulqon otilishi", "years": ["2028","2037","2049","2072"]},
    {"event": "🌑 Quyosh so'nmoqda", "years": ["2040","2055","2070","2090"]},
    {"event": "🧫 Mutant o'simliklar insonlarni yemoqda", "years": ["2032","2046","2059","2080"]},
    {"event": "💻 Global internet qulab tushdi", "years": ["2025","2030","2042","2065"]},
]

active_games = {}

def get_random_scenario():
    s = random.choice(SCENARIOS)
    return s["event"], random.choice(s["years"])

def init_game_state(lobby_id, players, scenario, year):
    """
    Har o'yinchiga 8 ta karta (har turdan bittadan) beriladi.
    game["players"][uid] = {
        "user_id", "full_name",
        "cards": [8 ta karta dict],
        "opened_indices": set(),  # ochilgan kartalar indeksi
    }
    """
    game_players = {}
    for p in players:
        cards = get_8_cards_for_player()
        game_players[p["user_id"]] = {
            "user_id": p["user_id"],
            "full_name": p["full_name"],
            "cards": cards,
            "opened_indices": set(),
        }

    active_games[lobby_id] = {
        "lobby_id": lobby_id,
        "players": game_players,
        "alive_players": [p["user_id"] for p in players],
        "scenario": scenario,
        "year": year,
        "phase": "card_reveal",
        "revealed_this_round": set(),  # shu raundda kim ochdi
        "votes": {},
        "round": 1,
        "eliminated": [],
        "market_card_used": {},
    }
    return active_games[lobby_id]

def get_game(lobby_id):
    return active_games.get(lobby_id)

def get_unopened_cards(lobby_id, user_id):
    """O'yinchining hali ochmagan kartalari ro'yxati (index, karta)"""
    game = active_games.get(lobby_id)
    if not game:
        return []
    player = game["players"].get(user_id)
    if not player:
        return []
    return [(i, c) for i, c in enumerate(player["cards"]) if i not in player["opened_indices"]]

def open_card_by_index(lobby_id, user_id, card_index):
    """O'yinchi xohlagan kartasini tanlab ochadi"""
    game = active_games.get(lobby_id)
    if not game:
        return None
    player = game["players"].get(user_id)
    if not player or card_index in player["opened_indices"]:
        return None
    player["opened_indices"].add(card_index)
    game["revealed_this_round"].add(user_id)
    return player["cards"][card_index]

def all_alive_revealed_this_round(lobby_id):
    game = active_games.get(lobby_id)
    if not game:
        return False
    return game["revealed_this_round"].issuperset(set(game["alive_players"]))

def reset_round_reveals(lobby_id):
    """Yangi raund uchun ochish holatini tozalash"""
    game = active_games.get(lobby_id)
    if game:
        game["revealed_this_round"] = set()

def add_vote(lobby_id, voter_id, target_id):
    game = active_games.get(lobby_id)
    if game:
        game["votes"][voter_id] = target_id

def count_votes(lobby_id):
    game = active_games.get(lobby_id)
    if not game:
        return None, None
    vote_count = {}
    for target in game["votes"].values():
        vote_count[target] = vote_count.get(target, 0) + 1
    if not vote_count:
        return None, None
    max_votes = max(vote_count.values())
    top = [pid for pid, v in vote_count.items() if v == max_votes]
    if len(top) > 1:
        return None, vote_count
    return top[0], vote_count

def eliminate(lobby_id, user_id):
    game = active_games.get(lobby_id)
    if game and user_id in game["alive_players"]:
        game["alive_players"].remove(user_id)
        game["eliminated"].append(user_id)
        eliminate_player(lobby_id, user_id)
        game["votes"] = {}
        game["round"] += 1
        return True
    return False

def reset_votes(lobby_id):
    game = active_games.get(lobby_id)
    if game:
        game["votes"] = {}

def get_winners(lobby_id):
    game = active_games.get(lobby_id)
    return game["alive_players"] if game else []

def end_game(lobby_id):
    if lobby_id in active_games:
        del active_games[lobby_id]
    update_lobby_status(lobby_id, "finished")
