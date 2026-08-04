import asyncio
from kahoot import KahootClient # type: ignore
import random
import time
import threading
import sys

print ("made by ReviveX")

async def join_one(pin, name, retry=2):
    for attempt in range(retry):
        try:
            client = KahootClient()
            await client.join_game(pin, name)
            print(f"{name} joined")
            return True
        except:
            await asyncio.sleep(0.5)
            return False

def worker(pin, name):
    asyncio.run(join_one(pin, name))

def raid(pin, total, bot_name="ReviveX"):
    threads = []
    for i in range(total):
        name = f"{bot_name}{random.randint(1000,9999)}"
        t = threading.Thread(target=worker, args=(pin,name))
        t.start()
        threads.append(t)
        time.sleep(0.1)
    
    for t in threads:
        t.join()
    
    print(f"\ndone join https://discord.gg/aEPbnuH2Ws for support")

if __name__ == "__main__":
    if len(sys.argv) >= 3:
        pin = sys.argv[1]
        count = int(sys.argv[2])
        bot_name = sys.argv[3] if len(sys.argv) > 3 else "ReviveX"
        raid(pin, count, bot_name)
    else:
        pin = input("Game pin please: ").strip()
        count = int(input("how many bots? "))
        bot_name = input("bot name (default: ReviveX): ").strip() or "ReviveX"
        raid(pin, count, bot_name)
