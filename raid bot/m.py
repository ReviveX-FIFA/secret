import requests, json, random, threading, time, sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import os

def load_tokens():
    try:
        with open("tokens.txt", "r") as f:
            return f.read().splitlines()
    except FileNotFoundError:
        print("tokens.txt not found")
        return []

def load_proxies():
    try:
        with open("proxies.txt", "r") as f:
            return f.read().splitlines()
    except FileNotFoundError:
        print("proxies.txt not found")
        return []

token_list = load_tokens()
proxy_list = load_proxies()
token_index = 0
proxy_index = 0

def get_token():
    global token_index
    if not token_list:
        return ""
    token = token_list[token_index % len(token_list)]
    token_index += 1
    if '|' in token:
        return token.split('|')[1]
    else:
        return token.strip()

def get_proxy():
    global proxy_index
    if not proxy_list:
        return None
    proxy = proxy_list[proxy_index % len(proxy_list)]
    proxy_index += 1
    if len(proxy.split(':')) == 4:
        ip, port, user, pw = proxy.split(':')
        proxy = f"{user}:{pw}@{ip}:{port}"
    return {"http": f"http://{proxy}", "https": f"http://{proxy}"}

if len(sys.argv) > 1:
    raid = sys.argv[1] if len(sys.argv) > 1 else ""
    amt = int(sys.argv[2]) if len(sys.argv) > 2 else 10
else:
    raid = input("raid id: ")
    amt = int(input("joins: "))

url = "https://gql.twitch.tv/gql"

def create_session():
    session = requests.Session()
    
    session.verify = False
    
    retry_strategy = Retry(
        total=1, 
        backoff_factor=0.05,
        status_forcelist=[429, 500, 502, 503, 504],
    )
    adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=100, pool_maxsize=100)
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    })
    
    return session

session = create_session()

def join(raid_id, url, thread_id):
    try:
        payload = [
            {
                "operationName": "JoinRaid",
                "variables": {
                    "input": {
                        "raidID": raid_id
                    }
                },
                "extensions": {
                    "persistedQuery": {
                        "version": 1,
                        "sha256Hash": "c6a332a86d1087fbbb1a8623aa01bd1313d2386e7c63be60fdb2d1901f01a4ae"
                    }
                }
            }
        ]

        headers = {
            "Accept": "application/json",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Accept-Language": "en-US",
            "Authorization": "OAuth " + get_token(),
            "Connection": "keep-alive",
            "Content-Type": "application/json",
            "Host": "gql.twitch.tv",
        }

        proxy = get_proxy()
        response = session.post(url, json=payload, headers=headers, proxies=proxy, timeout=3)
        result = response.json()
        print(f"Thread {thread_id}: {result}")
        return True
    except Exception as e:
        print(f"Thread {thread_id} failed: {e}")
        return False

print(f"Starting raid with {amt} joins by daddy ReviveX...")
start_time = time.time()

max_workers = min(100, amt)  
successful_joins = 0
failed_joins = 0

with ThreadPoolExecutor(max_workers=max_workers) as executor:
    
    futures = [executor.submit(join, raid, url, i+1) for i in range(amt)]
    
    for future in as_completed(futures):
        try:
            if future.result():
                successful_joins += 1
            else:
                failed_joins += 1
        except Exception as e:
            print(f"Thread error: {e}")
            failed_joins += 1

        total_processed = successful_joins + failed_joins
        if total_processed % 10 == 0 or total_processed == amt:
            elapsed = time.time() - start_time
            print(f"Progress: {total_processed}/{amt} | Success: {successful_joins} | Failed: {failed_joins} | Time: {elapsed:.1f}s")

end_time = time.time()
total_time = end_time - start_time
print(f"\nRaid completed in {total_time:.1f} seconds by ReviveX")
print(f"Successful joins: {successful_joins}/{amt}")
print(f"Failed joins: {failed_joins}")
print(f"Success rate: {(successful_joins/amt)*100:.1f}%")
