import os
import random
import threading
import time
import aiohttp
import asyncio
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
import re
import json


class Logger:
    @staticmethod
    def info(message):
        print(f"[INFO] {message}")
    
    @staticmethod
    def success(message):
        print(f"[SUCCESS] {message}")
    
    @staticmethod
    def error(message):
        print(f"[ERROR] {message}")
    
    @staticmethod
    def warning(message):
        print(f"[WARNING] {message}")


def parse_proxy_string(proxy_string):
    proxy_string = proxy_string.strip()
    if not proxy_string or proxy_string.startswith('#'):
        return None
    
    proxy_string = re.sub(r'\s+', '', proxy_string)
    
    protocol_match = re.match(r'^(https?|socks4|socks5|socks5h)://', proxy_string.lower())
    if protocol_match:
        protocol = protocol_match.group(1)
        rest = proxy_string[len(protocol)+3:]  
        
        if '@' in rest:
            user_pass, host_port = rest.split('@', 1)
            if ':' in user_pass:
                user, password = user_pass.split(':', 1)
                if ':' in host_port:
                    host, port = host_port.split(':', 1)
                    return f"{protocol}://{user}:{password}@{host}:{port}"
        else:
            if ':' in rest:
                host, port = rest.split(':', 1)
                return f"{protocol}://{host}:{port}"
    
    parts = proxy_string.split(':')
    
    if len(parts) == 2:
        host, port = parts
        if re.match(r'^[\w\.-]+$', host) and port.isdigit():
            return f"http://{host}:{port}"
    
    if len(parts) == 4:
        if re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', parts[0]) and parts[1].isdigit():
            host, port, user, password = parts
            return f"http://{user}:{password}@{host}:{port}"
        
        if re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', parts[2]) and parts[3].isdigit():
            user, password, host, port = parts
            return f"http://{user}:{password}@{host}:{port}"
        
        if re.match(r'^[\w\.-]+$', parts[0]) and parts[1].isdigit():
            host, port, user, password = parts
            return f"http://{user}:{password}@{host}:{port}"
    
    if '@' in proxy_string:
        at_parts = proxy_string.split('@', 1)
        if len(at_parts) == 2:
            user_pass, host_port = at_parts
            
            if ':' in user_pass:
                user_pass_parts = user_pass.split(':', 1)
                if len(user_pass_parts) == 2:
                    user, password = user_pass_parts
                    
                    if ':' in host_port:
                        host_port_parts = host_port.split(':', 1)
                        if len(host_port_parts) == 2:
                            host, port = host_port_parts
                            
                            if not proxy_string.startswith(('http://', 'https://', 'socks')):
                                return f"http://{user}:{password}@{host}:{port}"
                            return proxy_string
    
    if len(parts) >= 4:
        if parts[-1].isdigit() and re.match(r'^[\w\.-]+$', parts[-2]):
            port = parts[-1]
            host = parts[-2]
            user_pass = ':'.join(parts[:-2])
            if ':' in user_pass:
                return f"http://{user_pass}@{host}:{port}"
    
    rotating_keywords = ['rotating', 'session', 'residential', 'datacenter', 'static', 'path']
    for keyword in rotating_keywords:
        if proxy_string.lower().startswith(keyword):
            rest = proxy_string[len(keyword):].lstrip(':')
            if '@' in rest:
                return f"http://{rest}"
            if ':' in rest:
                parts2 = rest.split(':')
                if len(parts2) == 4:
                    user, password, host, port = parts2
                    return f"http://{user}:{password}@{host}:{port}"
    
    ipv6_match = re.match(r'^\[([a-fA-F0-9:]+)\]:(\d+)$', proxy_string)
    if ipv6_match:
        host, port = ipv6_match.groups()
        return f"http://[{host}]:{port}"
    
    domain_match = re.match(r'^([\w\.-]+):(\d+)$', proxy_string)
    if domain_match:
        host, port = domain_match.groups()
        return f"http://{host}:{port}"
    
    at_domain_match = re.match(r'^([^:@]+):([^:@]+)@([\w\.-]+):(\d+)$', proxy_string)
    if at_domain_match:
        user, password, host, port = at_domain_match.groups()
        return f"http://{user}:{password}@{host}:{port}"
    
    return None

def get_proxy_list():
    proxies = []
    if os.path.exists("proxies.txt"):
        try:
            with open("proxies.txt", "r", encoding='utf-8', errors='ignore') as f:
                for line in f:
                    proxy = parse_proxy_string(line)
                    if proxy:
                        proxies.append(proxy)
        except Exception as e:
            Logger.error(f"Failed to load proxies: {e}")
    return proxies

def get_auth_tokens():
    tokens = []
    if os.path.exists("tokens.txt"):
        try:
            with open("tokens.txt", "r", encoding='utf-8', errors='ignore') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.isspace():
                        token = line.replace("oauth:", "").strip()
                        if token:
                            tokens.append(token)
        except Exception as e:
            Logger.error(f"Failed to load tokens: {e}")
    return tokens


class TwitchFollowBot:
    def __init__(self, logger=Logger):
        self.logger = logger
        self.followed_records = defaultdict(set)
        self.lock = threading.Lock()
        self.running = False
        self.proxies = get_proxy_list()
        self.session_pool = None
        self.executor = ThreadPoolExecutor(max_workers=200)
        self.follow_counter = 0

    def log_message(self, message):
        self.logger.info(message)

    def fetch_user_id(self, username):
        headers = {
            "Client-Id": "kimne78kx3ncx6brgo4mv6wki5h1ko",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        }

        payload = json.dumps([{
            "operationName": "GetIDFromLogin",
            "variables": {"login": username},
            "extensions": {
                "persistedQuery": {
                    "version": 1,
                    "sha256Hash": "94e82a7b1e3c21e186daa73ee2afc4b8f23bade1fbbff6fe8ac133f50a2f58ca"
                }
            }
        }])

        try:
            return self.executor.submit(self._sync_fetch_user_id, username, headers, payload).result(timeout=30)
        except Exception as e:
            self.logger.error(f"Error getting user ID: {e}")
            return False

    def _sync_fetch_user_id(self, username, headers, payload):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(self._async_fetch_user_id(username, headers, payload))
        finally:
            loop.close()

    async def _async_fetch_user_id(self, username, headers, payload):
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
                async with session.post(
                    "https://gql.twitch.tv/gql",
                    headers=headers,
                    data=payload
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data and len(data) > 0 and 'data' in data[0]:
                            user_data = data[0]['data'].get('user')
                            if user_data:
                                return user_data.get('id')
        except Exception as e:
            self.logger.error(f"Network error: {e}")
        return False

    async def send_follow_request(self, target_id, token, session):
        try:
            headers = {
                "Accept": "application/json",
                "Authorization": f"OAuth {token}",
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0"
            }

            payload = json.dumps([{
                "operationName": "FollowUserMutation",
                "variables": {
                    "targetId": str(target_id),
                    "disableNotifications": False
                },
                "extensions": {
                    "persistedQuery": {
                        "version": 1,
                        "sha256Hash": "cd112d9483ede85fa0da514a5657141c24396efbc7bac0ea3623e839206573b8"
                    }
                }
            }])

            proxy_url = None
            if self.proxies:
                proxy = random.choice(self.proxies)
                proxy_url = proxy
                
            async with session.post(
                "https://gql.twitch.tv/gql",
                data=payload,
                headers=headers,
                proxy=proxy_url,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                return response.status in (200, 204)
                
        except Exception:
            return False

    async def follow_worker(self, target_id, tokens, target_username, max_follows, stats, session):
        while True:
            if stats["completed"] >= max_follows:
                return

            token = random.choice(tokens)

            if stats["completed"] >= max_follows:
                return

            success = await self.send_follow_request(target_id, token, session)

            if success:
                with self.lock:
                    if stats["completed"] < max_follows:
                        stats["completed"] += 1
                        current = stats["completed"]
                        self.follow_counter += 1
                        
                        
                        if current % 10 == 0 or current == max_follows:
                            msg = f"Progress: {current}/{max_follows} - {target_username}"
                            self.log_message(msg)

    async def create_http_session(self):
        connector = aiohttp.TCPConnector(
            limit=1000,
            limit_per_host=500,
            ttl_dns_cache=300,
            use_dns_cache=True,
            ssl=False,
            keepalive_timeout=30,
            enable_cleanup_closed=True,
            force_close=False
        )
        timeout = aiohttp.ClientTimeout(total=15, connect=5)
        return aiohttp.ClientSession(connector=connector, timeout=timeout)

    def process_follow_operation(self, target_id, follow_count, tokens, target_username):
        completion_event = threading.Event()
        
        def run_async():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            async def main_async():
                stats = {"completed": 0}
                
                session = await self.create_http_session()
                
                worker_count = min(1000, follow_count)
                
                tasks = []
                for _ in range(worker_count):
                    tasks.append(self.follow_worker(target_id, tokens, target_username, follow_count, stats, session))
                
                await asyncio.gather(*tasks)
                await session.close()
                completion_event.set()
            
            try:
                loop.run_until_complete(main_async())
            finally:
                loop.close()
        
        self.running = True
        self.logger.info(f"Starting {follow_count} follows for {target_username}")
        
        threading.Thread(target=run_async, daemon=True).start()
        return completion_event

    def execute_bot_operation(self, username, count):
        self.logger.info(f"Fetching ID for {username}...")
        user_id = self.fetch_user_id(username)
        
        if not user_id:
            self.logger.error(f"Failed to get ID for {username}")
            self.running = False
            return
        
        self.logger.success(f"User ID: {user_id}")
        
        tokens = get_auth_tokens()
        if not tokens:
            self.logger.error("No tokens found")
            self.running = False
            return
        
        completion = self.process_follow_operation(user_id, count, tokens, username)
        
        completion.wait()
        self.running = False
        self.logger.success(f"Finished! {self.follow_counter}/{count} follows")

    def launch_bot(self, username, count):
        if self.running:
            self.logger.warning("Already running")
            return

        self.running = True
        self.follow_counter = 0
        thread = threading.Thread(target=self.execute_bot_operation, args=(username, count), daemon=True)
        thread.start()
        return thread

    def shutdown_bot(self):
        self.running = False
        self.logger.info("Stopping...")
        if hasattr(self, 'executor'):
            self.executor.shutdown(wait=False)


def display_banner():
    print("""
    ╔══════════════════════════════════════════════════════════╗
    ║                                                          ║
    ║           TWITCH FOLLOW AUTOMATION TOOL                  ║
    ║                                                          ║
    ║                    Version 2.0  BY ReviveX                 ║
    ║                                                          ║
    ╚══════════════════════════════════════════════════════════╝
    """)


if __name__ == "__main__":
    import sys
    
    display_banner()
    
    bot = TwitchFollowBot()
    
    if len(sys.argv) >= 2:
        username = sys.argv[1]
        count = int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2].isdigit() else 10
    else:
        username = input("Please enter user: ").strip()
        
        try:
            count = int(input("Please enter amount max 730,000: ").strip())
            if count > 730000:
                print("Maximum amount is 730,000. Setting to 730,000.")
                count = 730000
        except ValueError:
            print("Invalid number. Using 10")
            count = 10
    
    bot.launch_bot(username, count)
    
    print("Started. Press Ctrl+C to stop.")
    
    try:
        while bot.running:
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\nStopping...")
        bot.shutdown_bot()
        time.sleep(0.5)
    
    print("Bot stopped.")
