import asyncio
import json
import random
import aiohttp
import websockets

BASE_URL = "http://localhost:8000"
MATCH_WS_URL = "ws://localhost:8000/matchmaking/ws"
GAME_WS_URL = "ws://localhost:8000/game/ws"


async def login_or_register(session, uniq_id: str):
    async with session.post(f"{BASE_URL}/auth/login-or-register", json={"uniqId": uniq_id}) as resp:
        data = await resp.json()
        print(f"[{uniq_id}] login_or_register →", data)
        return data


async def matchmaking_ws(uniq_id: str, name: str, game_id_box: dict, ready_event: asyncio.Event):
    async with websockets.connect(MATCH_WS_URL) as ws:
        await ws.send(json.dumps({"uniqId": uniq_id, "name": name}))
        while True:
            msg = await ws.recv()
            data = json.loads(msg)
            print(f"[{uniq_id}] matchmaking WS →", data)
            if data.get("type") == "match_found":
                game_id_box["id"] = data["game_session_id"]
                ready_event.set()  # משחק נוצר
                break


async def game_ws(game_id: str, player_name: str):
    url = f"{GAME_WS_URL}/{game_id}"
    async with websockets.connect(url) as ws:
        print(f"[{player_name}] connected to game WS {game_id}")
        try:
            while True:
                msg = await ws.recv()
                print(f"[{player_name}] game WS update:", msg)
        except Exception as e:
            print(f"[{player_name}] game WS closed:", e)


async def make_move(session, game_id: str, uniq_id: str):
    x, y = random.randint(0, 6), random.randint(0, 7)
    payload = {"game_id": game_id, "uniqId": uniq_id, "x": x, "y": y}
    async with session.post(f"{BASE_URL}/game/move", json=payload) as resp:
        data = await resp.json()
        print(f"[{uniq_id}] move ({x},{y}) → HTTP {resp.status}:", json.dumps(data, indent=2))
        return data


async def main():
    async with aiohttp.ClientSession() as session:
        # דואגים ששני השחקנים קיימים
        await login_or_register(session, "player1")
        await login_or_register(session, "player2")

        game_id_box = {}
        ready_event = asyncio.Event()

        # מתחברים ל־matchmaking
        mm1 = asyncio.create_task(matchmaking_ws("player1", "Alice", game_id_box, ready_event))
        mm2 = asyncio.create_task(matchmaking_ws("player2", "Bob", game_id_box, ready_event))

        # מחכים למשחק
        await ready_event.wait()
        game_id = game_id_box["id"]
        print("\n🎮 Match found! Game ID:", game_id, "\n")

        # מתחברים ל־WS של המשחק
        ws1 = asyncio.create_task(game_ws(game_id, "Alice"))
        ws2 = asyncio.create_task(game_ws(game_id, "Bob"))

        # מבצעים כמה מהלכים
        await asyncio.sleep(2)  # שיהיה זמן ל־WS להתחבר
        await make_move(session, game_id, "player1")
        await asyncio.sleep(1)
        await make_move(session, game_id, "player2")
        await asyncio.sleep(1)
        await make_move(session, game_id, "player1")

        # ממתינים קצת לראות הודעות WS
        await asyncio.sleep(10)

        # סוגרים
        mm1.cancel()
        mm2.cancel()
        ws1.cancel()
        ws2.cancel()


if __name__ == "__main__":
    asyncio.run(main())
