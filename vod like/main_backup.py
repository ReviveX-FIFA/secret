import httpx
import asyncio
import json
import os
import sys
import random
import re
from datetime import datetime

GQL_URL = "https://gql.twitch.tv/gql"
TOKENS_PATH = "tokens.txt"
PROXIES_PATH = "proxies.txt"

CLIENT_ID = "kd1unb4b3q4t58fwlpcbzcbnm76a8fp"
CLIENT_VERSION = "d1cb2181-c708-4417-b0b6-7fe7ddd78637"

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/144.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/118.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/116.0.0.0 Safari/537.36',

    'Mozilla/5.0 (Windows NT 11.0; Win64; x64) AppleWebKit/537.36 Chrome/123.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 11.0; Win64; x64) AppleWebKit/537.36 Chrome/121.0.0.0 Safari/537.36',

    'Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5) AppleWebKit/537.36 Chrome/121.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 12_6) AppleWebKit/537.36 Chrome/119.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 11_7) AppleWebKit/537.36 Chrome/117.0.0.0 Safari/537.36',

    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/118.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/116.0.0.0 Safari/537.36',

    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:119.0) Gecko/20100101 Firefox/119.0',

    'Mozilla/5.0 (Macintosh; Intel Mac OS X 13.5; rv:121.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (X11; Linux x86_64; rv:118.0) Gecko/20100101 Firefox/118.0'
]
def load_proxies():
    proxies = []
    if os.path.exists(PROXIES_PATH):
        with open(PROXIES_PATH, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    proxies.append(line)
    return proxies

async def get_channel_id(client, username):
    headers = {
        'client-id': CLIENT_ID,
        'content-type': 'text/plain;charset=UTF-8',
        'user-agent': random.choice(USER_AGENTS),
    }
    payload = [{
        "operationName": "GetIDFromLogin",
        "variables": {"login": username.lower()},
        "extensions": {
            "persistedQuery": {
                "version": 1,
                "sha256Hash": "94e82a7b1e3c21e186daa73ee2afc4b8f23bade1fbbff6fe8ac133f50a2f58ca"
            }
        }
    }]
    try:
        response = await client.post(GQL_URL, headers=headers, content=json.dumps(payload))
        if response.status_code == 200:
            data = response.json()
            if data and data[0].get('data', {}).get('user'):
                return data[0]['data']['user']['id']
    except:
        pass
    return None

async def like_clip(client, token, channel_id, content_id):
    headers = {
        'authorization': f'OAuth {token}',
        'client-id': CLIENT_ID,
        'client-version': CLIENT_VERSION,
        'content-type': 'text/plain;charset=UTF-8',
        'user-agent': random.choice(USER_AGENTS),
        'x-device-id': ''.join(random.choices('0123456789abcdef', k=32)),
    }

    payload = [{
        "operationName": "updateReactionByContentKey",
        "variables": {
            "input": {
                "channelID": channel_id,
                "contentID": content_id,
                "contentType": "CLIP",
                "reactionType": "LIKE"
            }
        },
        "extensions": {
            "persistedQuery": {
                "version": 1,
                "sha256Hash": "968a80753fdb112103c273fa7cfb202ee7709f92920822e73cda120427daa5bf"
            }
        }
    }]

    try:
        response = await client.post(GQL_URL, headers=headers, content=json.dumps(payload))
        return response.status_code == 200
    except:
        return False

async def worker(client, channel_id, clip_id, token_queue, proxy_queue, stats):
    while True:
        try:
            token = token_queue.get_nowait()
        except asyncio.QueueEmpty:
            break
        
        proxy = None
        if proxy_queue:
            try:
                proxy = proxy_queue.get_nowait()
                proxy_queue.put_nowait(proxy)
            except:
                pass
        
        if await like_clip(client, token, channel_id, clip_id):
            stats['success'] += 1
        else:
            stats['failed'] += 1
        
async def main():
    print("TWITCH CLIP LIKER - FAST")
    print("="*40)
    
    # Check for command line arguments
    if len(sys.argv) > 1:
        # Non-interactive mode
        vod_url = sys.argv[1] if len(sys.argv) > 1 else ""
        amount = int(sys.argv[2]) if len(sys.argv) > 2 else 50
        
        if not vod_url:
            print("VOD URL required")
            return
        
        # Extract clip ID from URL
        if '/' in vod_url:
            clip_id = vod_url.split('/')[-1]
        else:
            clip_id = vod_url
        
        # Load tokens
        tokens = load_tokens()
        if not tokens:
            print("No tokens found")
            return
        
        amount = min(amount, len(tokens))
        
        print(f"Liking clip {clip_id} with {amount} likes...")
        
        # Start liking
        stats = {'success': 0, 'failed': 0, 'total': 0}
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=50) as executor:
            futures = [executor.submit(like_clip, token, clip_id) for token in tokens[:amount]]
            
            for future in as_completed(futures):
                try:
                    if future.result():
                        stats['success'] += 1
                    else:
                        stats['failed'] += 1
                except:
                    stats['failed'] += 1
                
                stats['total'] += 1
                
                # Progress
                elapsed = time.time() - start_time
                rate = stats['success'] / elapsed if elapsed > 0 else 0
                print(f"\rProgress: {stats['success']}/{stats['total']} | Failed: {stats['failed']} | Rate: {rate:.0f}/s", end="", flush=True)
        
        # Results
        print(f"\nCompleted in {time.time() - start_time:.1f} seconds")
        print(f"Successful likes: {stats['success']}/{amount}")
        print(f"Failed likes: {stats['failed']}")
        
        if stats['success'] > 0:
            print(f"Speed: {stats['success']/(time.time() - start_time):.1f}/s")
    else:
        # Interactive mode
        tokens = load_tokens()
        if not tokens:
            print("No tokens found")
            return
        
        print(f"Available tokens: {len(tokens)}")
        
        channel = input("Channel: ").strip()
        clip_id = input("Clip ID: ").strip()
        
        try:
            amount = int(input(f"Likes (max {len(tokens)}): ").strip())
            amount = min(amount, len(tokens))
        except:
            amount = len(tokens)
        
        print(f"Liking clip {clip_id} with {amount} likes...")
        
        # Start liking
        stats = {'success': 0, 'failed': 0, 'total': 0}
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=50) as executor:
            futures = [executor.submit(like_clip, token, clip_id) for token in tokens[:amount]]
            
            for future in as_completed(futures):
                try:
                    if future.result():
                        stats['success'] += 1
                    else:
                        stats['failed'] += 1
                except:
                    stats['failed'] += 1
                
                stats['total'] += 1
                
                # Progress
                elapsed = time.time() - start_time
                rate = stats['success'] / elapsed if elapsed > 0 else 0
                print(f"\rProgress: {stats['success']}/{stats['total']} | Failed: {stats['failed']} | Rate: {rate:.0f}/s", end="", flush=True)
        
        # Results
        print(f"\nCompleted in {time.time() - start_time:.1f} seconds")
        print(f"Successful likes: {stats['success']}/{amount}")
        print(f"Failed likes: {stats['failed']}")
        
        if stats['success'] > 0:
            print(f"Speed: {stats['success']/(time.time() - start_time):.1f}/s")

    proxies = load_proxies()
    print(f"Loaded {len(proxies)} proxies")
    
    if not os.path.exists(TOKENS_PATH):
        print("tokens.txt not found")
        return

    with open(TOKENS_PATH, "r") as f:
        tokens = [line.strip().replace("oauth:", "").strip() for line in f if line.strip()]

    if not tokens:
        print("No tokens found")
        return

    channel = input("Channel: ").strip()
    clip_id = input("Clip ID: ").strip()
    
    try:
        amount = int(input(f"Likes (max {len(tokens)}): ").strip())
        amount = min(amount, len(tokens))
    except:
        amount = len(tokens)
    
    selected_tokens = tokens[:amount]
    print(f"\nTokens: {len(selected_tokens)}")
    print(f"Proxies: {len(proxies)}")
    print("-" * 40)
    
    limits = httpx.Limits(max_keepalive_connections=1000, max_connections=2000)
    
    async with httpx.AsyncClient(
        limits=limits,
        timeout=3.0,
        http2=True
    ) as client:
        
        print("Getting channel ID...")
        channel_id = await get_channel_id(client, channel)
        
        if not channel_id:
            print("Channel not found")
            return
            
        print(f"Channel ID: {channel_id}")
        print("-" * 40)
        
        token_queue = asyncio.Queue()
        for token in selected_tokens:
            token_queue.put_nowait(token)
        
        proxy_queue = None
        if proxies:
            proxy_queue = asyncio.Queue()
            for proxy in proxies:
                proxy_queue.put_nowait(proxy)
        
        stats = {
            'success': 0,
            'failed': 0,
            'total': amount,
            'start': datetime.now()
        }
        
        workers = []
        for i in range(500):
            w = asyncio.create_task(worker(client, channel_id, clip_id, token_queue, proxy_queue, stats))
            workers.append(w)
        
        await asyncio.gather(*workers)
        
        elapsed = (datetime.now() - stats['start']).total_seconds()
        print(f"\n\nCompleted in {elapsed:.1f}s")
        print(f"Success: {stats['success']}")
        print(f"Failed: {stats['failed']}")
        if stats['success'] > 0:
            print(f"Speed: {stats['success']/elapsed:.0f}/s")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nStopped")
        sys.exit(0)
