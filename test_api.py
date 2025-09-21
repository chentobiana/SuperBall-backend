import asyncio, websockets, json, aiohttp

HTTP_BASE = "http://localhost:8000"
WS_URI = "ws://localhost:8000/matchmaking/ws"

async def player(uniqId, name):
    async with websockets.connect(WS_URI) as ws:
        await ws.send(json.dumps({"uniqId": uniqId, "name": name}))
        # הצטרפות לתור ב-HTTP
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{HTTP_BASE}/matchmaking/join",
                                    json={"uniqId": uniqId, "name": name}) as resp:
                print(name, "join status:", resp.status, await resp.text())
        # קבלת match_found
        while True:
            msg = await ws.recv()
            print(f"[{name}] <- {msg}")

async def main():
    await asyncio.gather(
        player("abc123", "Chen"),
    )

asyncio.run(main())