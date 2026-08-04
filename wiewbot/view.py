import aiohttp
import asyncio
import random
import sys
import os
import hashlib
import time
import re
from datetime import datetime

class Colors:
    RED = '\033[91m'
    DARK_RED = '\033[31m'
    BRIGHT_RED = '\033[1;91m'
    PINK = '\033[95m'
    WHITE = '\033[97m'
    GRAY = '\033[90m'
    BOLD = '\033[1m'
    RESET = '\033[0m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    CYAN = '\033[96m'

BANNER = f"""
{Colors.BRIGHT_RED}╔══════════════════════════════════════════════════════════╗
║                                                          ║
║  {Colors.BOLD}██╗   ██╗██╗███████╗██╗    ██╗    ██████╗  ██████╗ ████████╗{Colors.RESET}{Colors.BRIGHT_RED}  
║  {Colors.BOLD}██║   ██║██║██╔════╝██║    ██║    ██╔══██╗██╔═══██╗╚══██╔══╝{Colors.RESET}{Colors.BRIGHT_RED}  
║  {Colors.BOLD}██║   ██║██║█████╗  ██║ █╗ ██║    ██████╔╝██║   ██║   ██║   {Colors.RESET}{Colors.BRIGHT_RED}  
║  {Colors.BOLD}╚██╗ ██╔╝██║██╔══╝  ██║███╗██║    ██╔══██╗██║   ██║   ██║   {Colors.RESET}{Colors.BRIGHT_RED}  
║   {Colors.BOLD}╚████╔╝ ██║███████╗╚███╔███╔╝    ██████╔╝╚██████╔╝   ██║   {Colors.RESET}{Colors.BRIGHT_RED}  
║    {Colors.BOLD}╚═══╝  ╚═╝╚══════╝ ╚══╝╚══╝     ╚═════╝  ╚═════╝    ╚═╝   {Colors.RESET}{Colors.BRIGHT_RED}  
║                                                          
║              {Colors.BOLD}{Colors.WHITE}TWITCH VIEW BOT{Colors.RESET}{Colors.BRIGHT_RED}                          
║                   {Colors.PINK}Coded by ReviveX{Colors.RESET}{Colors.BRIGHT_RED}                       
╚══════════════════════════════════════════════════════════╝{Colors.RESET}
"""

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.6261.94 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.6312.58 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_6_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.6261.94 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.6312.58 Safari/537.36",
]

class TwitchViewBot:
    
    def __init__(self):
        self.channel = None
        self.proxies = []
        self.viewers_active = 0
        self.segments_total = 0
        self.running = True
        self.max_viewers = 0
        self.viewer_sessions = {}
        
    def parse_proxy(self, line):
        line = line.strip()
        if not line or line.startswith('#'):
            return None
        
        if line.startswith(('http://', 'https://', 'socks4://', 'socks5://')):
            return line
        
        parts = line.split(':')
        
        if len(parts) == 4:
            host, port, user, password = parts
            return f"http://{user}:{password}@{host}:{port}"
        
        if '@' in line:
            return f"http://{line}"
        
        if len(parts) == 2:
            return f"http://{parts[0]}:{parts[1]}"
        
        return None
    
    def load_proxies(self):
        if not os.path.exists('proxies.txt'):
            print(f"{Colors.RED}[!]{Colors.RESET} proxies.txt not found!")
            return False
        
        try:
            with open('proxies.txt', 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    proxy = self.parse_proxy(line)
                    if proxy:
                        self.proxies.append(proxy)
            
            if not self.proxies:
                print(f"{Colors.RED}[!]{Colors.RESET} No valid proxies found")
                return False
            
            return True
        except Exception as e:
            print(f"{Colors.RED}[!]{Colors.RESET} Error loading proxies: {e}")
            return False
    
    def get_proxy(self, viewer_id):
        if not self.proxies:
            return None
        index = (viewer_id - 1) % len(self.proxies)
        return self.proxies[index]
    
    def generate_id(self, length=32):
        return ''.join(random.choices('abcdef0123456789', k=length))
    
    def generate_uuid(self):
        return ''.join(random.choices('0123456789abcdef', k=8)) + '-' + \
               ''.join(random.choices('0123456789abcdef', k=4)) + '-' + \
               ''.join(random.choices('0123456789abcdef', k=4)) + '-' + \
               ''.join(random.choices('0123456789abcdef', k=4)) + '-' + \
               ''.join(random.choices('0123456789abcdef', k=12))
    
    async def send_heartbeat(self, viewer_id, session, player_session, device_id):
        try:
            heartbeat_query = [{
                "operationName": "PlaybackHeartbeat",
                "variables": {
                    "playerSessionID": player_session
                },
                "extensions": {
                    "persistedQuery": {
                        "version": 1,
                        "sha256Hash": "a069645bf07c7f6d84e1669df07005a7f873e6acbdbf6e1c3a7c5c3efbbeb2ae"
                    }
                }
            }]
            
            await session.post(
                "https://gql.twitch.tv/gql",
                json=heartbeat_query,
                headers={
                    "Client-ID": "kimne78kx3ncx6brgo4mv6wki5h1ko",
                    "Device-ID": device_id
                }
            )
        except:
            pass
    
    async def keep_alive(self, viewer_id, session, stream_url, headers, proxy, player_session, device_id):
        last_segment = None
        segment_count = 0
        last_heartbeat = time.time()
        
        while self.running:
            try:
                async with session.get(
                    stream_url,
                    headers=headers,
                    proxy=proxy,
                    timeout=aiohttp.ClientTimeout(total=15)
                ) as r:
                    if r.status != 200:
                        await asyncio.sleep(3)
                        continue
                    
                    playlist_data = await r.text()
                    segments = [l.strip() for l in playlist_data.split('\n') 
                              if l.strip() and not l.startswith('#')]
                    
                    if not segments:
                        await asyncio.sleep(3)
                        continue
                    
                    latest = segments[-1]
                    
                    if latest != last_segment:
                        last_segment = latest
                        
                        if not latest.startswith('http'):
                            base = stream_url.rsplit('/', 1)[0]
                            latest = f"{base}/{latest}"
                        
                        try:
                            async with session.get(
                                latest,
                                headers=headers,
                                proxy=proxy,
                                timeout=aiohttp.ClientTimeout(total=15)
                            ) as seg_r:
                                if seg_r.status == 200:
                                    data = bytearray()
                                    async for chunk in seg_r.content.iter_chunked(8192):
                                        data.extend(chunk)
                                    
                                    if len(data) > 0:
                                        segment_count += 1
                                        self.segments_total += 1
                                        
                                        if segment_count % 20 == 0:
                                            print(f"{Colors.CYAN}[V{viewer_id}]{Colors.RESET} {segment_count} segs")
                        except:
                            pass
                    
                    if time.time() - last_heartbeat > 60:
                        await self.send_heartbeat(viewer_id, session, player_session, device_id)
                        last_heartbeat = time.time()
                    
                    await asyncio.sleep(random.uniform(4, 7))
                    
            except asyncio.CancelledError:
                break
            except:
                await asyncio.sleep(3)
    
    async def create_viewer(self, viewer_id):
        
        await asyncio.sleep(viewer_id * 0.1)
        
        device_id = self.generate_id(32)
        session_id = self.generate_id(16)
        player_session = self.generate_uuid()
        client_session = self.generate_uuid()
        
        user_agent = random.choice(USER_AGENTS)
        proxy = self.get_proxy(viewer_id)
        
        if not proxy:
            return
        
        viewer_active = False
        
        while self.running:
            try:
                connector = aiohttp.TCPConnector(ssl=False, limit=0, force_close=False)
                timeout = aiohttp.ClientTimeout(total=20, connect=10)
                
                async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
                    
                    token_headers = {
                        "Client-ID": "kimne78kx3ncx6brgo4mv6wki5h1ko",
                        "User-Agent": user_agent,
                        "Accept": "*/*",
                        "Accept-Language": "en-US,en;q=0.9",
                        "Origin": "https://www.twitch.tv",
                        "Referer": f"https://www.twitch.tv/{self.channel}",
                        "Device-ID": device_id,
                        "Client-Session-Id": client_session,
                        "X-Device-Id": device_id,
                        "X-Session-Id": session_id,
                    }
                    
                    token_query = [{
                        "operationName": "PlaybackAccessToken",
                        "variables": {
                            "isLive": True,
                            "login": self.channel,
                            "isVod": False,
                            "vodID": "",
                            "playerType": "site"
                        },
                        "extensions": {
                            "persistedQuery": {
                                "version": 1,
                                "sha256Hash": "0828119ded1c13477966434e15800ff57ddacf13ba1911c129dc2200705b0712"
                            }
                        }
                    }]
                    
                    token = None
                    sig = None
                    
                    for attempt in range(3):
                        try:
                            async with session.post(
                                "https://gql.twitch.tv/gql",
                                json=token_query,
                                headers=token_headers,
                                proxy=proxy
                            ) as r:
                                if r.status == 200:
                                    data = await r.json()
                                    if isinstance(data, list) and len(data) > 0:
                                        token_data = data[0]["data"]["streamPlaybackAccessToken"]
                                        token = token_data["value"]
                                        sig = token_data["signature"]
                                        break
                        except:
                            if attempt < 2:
                                await asyncio.sleep(2)
                    
                    if not token:
                        await asyncio.sleep(5)
                        continue
                    
                    usher_url = f"https://usher.ttvnw.net/api/channel/hls/{self.channel}.m3u8"
                    usher_params = {
                        "client_id": "kimne78kx3ncx6brgo4mv6wki5h1ko",
                        "token": token,
                        "sig": sig,
                        "allow_source": "true",
                        "allow_audio_only": "true",
                        "allow_spectre": "false",
                        "player": "twitchweb",
                        "player_backend": "mediaplayer",
                        "player_version": "1.28.0",
                        "playlist_include_framerate": "true",
                        "reassignments_supported": "true",
                        "cdm": "wv",
                        "p": random.randint(1000000, 9999999)
                    }
                    
                    stream_url = None
                    
                    try:
                        async with session.get(
                            usher_url,
                            params=usher_params,
                            headers={"User-Agent": user_agent},
                            proxy=proxy
                        ) as r:
                            if r.status == 200:
                                playlist = await r.text()
                                lines = playlist.split('\n')
                                
                                for line in lines:
                                    if line.startswith('https://') and '160p30' in line:
                                        stream_url = line.strip()
                                        break
                                
                                if not stream_url:
                                    for line in lines:
                                        if line.startswith('https://'):
                                            stream_url = line.strip()
                                            break
                    except:
                        await asyncio.sleep(5)
                        continue
                    
                    if not stream_url:
                        await asyncio.sleep(5)
                        continue
                    
                    if not viewer_active:
                        print(f"{Colors.GREEN}[V{viewer_id}]{Colors.RESET} Connected")
                        self.viewers_active += 1
                        viewer_active = True
                        if self.viewers_active > self.max_viewers:
                            self.max_viewers = self.viewers_active
                    
                    segment_headers = {
                        "User-Agent": user_agent,
                        "Accept": "*/*",
                        "Accept-Encoding": "gzip, deflate",
                        "Accept-Language": "en-US,en;q=0.9",
                        "Origin": "https://www.twitch.tv",
                        "Referer": f"https://www.twitch.tv/{self.channel}",
                        "Device-ID": device_id,
                        "X-Device-Id": device_id,
                        "X-Session-Id": session_id,
                        "Connection": "keep-alive",
                    }
                    
                    await self.keep_alive(
                        viewer_id, session, stream_url, 
                        segment_headers, proxy, player_session, device_id
                    )
                    
            except asyncio.CancelledError:
                break
            except:
                await asyncio.sleep(5)
        
        if viewer_active:
            self.viewers_active -= 1
    
    async def display_stats(self):
        start_time = time.time()
        
        while self.running:
            elapsed = int(time.time() - start_time)
            mins = elapsed // 60
            secs = elapsed % 60
            
            rate = self.segments_total / elapsed if elapsed > 0 else 0
            
            print(f"\r{Colors.BRIGHT_RED}[{mins:02d}:{secs:02d}]{Colors.RESET} "
                  f"Active: {Colors.WHITE}{self.viewers_active}/{self.max_viewers}{Colors.RESET} | "
                  f"Segments: {Colors.PINK}{self.segments_total}{Colors.RESET} | "
                  f"Rate: {Colors.CYAN}{rate:.1f}/s{Colors.RESET}",
                  end='', flush=True)
            
            await asyncio.sleep(2)
    
    async def run(self):
        os.system('cls' if os.name == 'nt' else 'clear')
        print(BANNER)
        
        if not self.load_proxies():
            return
        
        print(f"{Colors.BRIGHT_RED}┌─[{Colors.WHITE}Channel{Colors.BRIGHT_RED}]─{Colors.RESET}")
        self.channel = input(f"{Colors.BRIGHT_RED}└─▶{Colors.RESET} ").strip()
        
        if not self.channel:
            print(f"{Colors.RED}[!]{Colors.RESET} Channel required")
            return
        
        print(f"\n{Colors.BRIGHT_RED}┌─[{Colors.WHITE}Viewers{Colors.BRIGHT_RED}]─{Colors.RESET}")
        try:
            viewer_count = int(input(f"{Colors.BRIGHT_RED}└─▶{Colors.RESET} ").strip())
        except:
            viewer_count = 50
        
        print(f"\n{Colors.BRIGHT_RED}[STARTING]{Colors.RESET} Launching {Colors.BOLD}{viewer_count}{Colors.RESET} viewers")
        print(f"{Colors.PINK}[!]{Colors.RESET} Press Ctrl+C to stop\n")
        
        stats_task = asyncio.create_task(self.display_stats())
        
        viewer_tasks = []
        for i in range(viewer_count):
            task = asyncio.create_task(self.create_viewer(i + 1))
            viewer_tasks.append(task)
            if i % 5 == 0:
                await asyncio.sleep(0.1)
        
        print(f"{Colors.BRIGHT_RED}[RUNNING]{Colors.RESET} All viewers launched!\n")
        
        try:
            await asyncio.gather(*viewer_tasks)
        except KeyboardInterrupt:
            pass
        finally:
            self.running = False
            stats_task.cancel()
            
            for task in viewer_tasks:
                task.cancel()
            
            await asyncio.gather(*viewer_tasks, return_exceptions=True)
            
            print(f"\n\n{Colors.BRIGHT_RED}{'═' * 50}{Colors.RESET}")
            print(f"{Colors.BOLD}{Colors.WHITE}                  RESULTS{Colors.RESET}")
            print(f"{Colors.BRIGHT_RED}{'═' * 50}{Colors.RESET}")
            print(f"{Colors.WHITE}Peak Viewers:{Colors.RESET}     {self.max_viewers}")
            print(f"{Colors.PINK}Total Segments:{Colors.RESET}   {self.segments_total}")
            print(f"{Colors.BRIGHT_RED}{'═' * 50}{Colors.RESET}")
            print(f"\n{Colors.PINK}[INFO]{Colors.RESET} Coded by {Colors.BOLD}ReviveX{Colors.RESET}")

    async def run_with_viewers(self, viewer_count):
        stats_task = asyncio.create_task(self.display_stats())
        
        viewer_tasks = []
        for i in range(viewer_count):
            task = asyncio.create_task(self.create_viewer(i + 1))
            viewer_tasks.append(task)
            if i % 5 == 0:
                await asyncio.sleep(0.1)
        
        print(f"{Colors.BRIGHT_RED}[RUNNING]{Colors.RESET} All viewers launched!\n")
        
        try:
            await asyncio.gather(*viewer_tasks)
        except KeyboardInterrupt:
            pass
        finally:
            self.running = False
            stats_task.cancel()
            
            for task in viewer_tasks:
                task.cancel()
            
            await asyncio.gather(*viewer_tasks, return_exceptions=True)
            
            print(f"\n\n{Colors.BRIGHT_RED}{'═' * 50}{Colors.RESET}")
            print(f"{Colors.BOLD}{Colors.WHITE}                  RESULTS{Colors.RESET}")
            print(f"{Colors.BRIGHT_RED}{'═' * 50}{Colors.RESET}")
            print(f"{Colors.WHITE}Peak Viewers:{Colors.RESET}     {self.max_viewers}")
            print(f"{Colors.PINK}Total Segments:{Colors.RESET}   {self.segments_total}")
            print(f"{Colors.BRIGHT_RED}{'═' * 50}{Colors.RESET}")
            print(f"\n{Colors.PINK}[INFO]{Colors.RESET} Coded by {Colors.BOLD}ReviveX{Colors.RESET}")

import sys

async def main():
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    # Check for command line arguments
    if len(sys.argv) > 1:
        # Non-interactive mode
        channel = sys.argv[1] if len(sys.argv) > 1 else ""
        viewer_count = int(sys.argv[2]) if len(sys.argv) > 2 else 50
        
        bot = TwitchViewBot()
        bot.channel = channel
        await bot.run_with_viewers(viewer_count)
    else:
        # Interactive mode
        bot = TwitchViewBot()
        await bot.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n{Colors.PINK}Exited{Colors.RESET}")
