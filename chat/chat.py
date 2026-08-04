import aiohttp
import asyncio
import json
import random
import sys
import re
import os
from datetime import datetime
import threading

# Global emotes that work in every chat (emote-only mode bypass)
GLOBAL_EMOTES = [
    "RedNoseDay26", "NowField", "WoWMidnight", "Yagoo", "SipTime", "EleGiggle",
    "FeverFighter", "WeDidThat", "PewPewPew", "JinxLUL", "FeelsVi", "AmbessaLove",
    "EkkoChest", "CaitThinking", "Cinheimer", "BratChat", "BigSad", "GRASSLORD",
    "TWITH", "SUBtember", "AnotherRecord", "GoatEmotey", "GoldPLZ", "TwitchConHYPE",
    "PopNemo", "DinoDance", "NewRecord", "SUBprise", "ImTyping", "Shush", "MyAvatar",
    "PizzaTime", "LaundryBasket", "ModLove", "Jebasted", "TransgenderPride",
    "PansexualPride", "NonbinaryPride", "LesbianPride", "IntersexPride",
    "GenderFluidPride", "GayPride", "BisexualPride", "AsexualPride", "PogChamp",
    "GlitchNRG", "GlitchLit", "StinkyGlitch", "GlitchCat", "FootGoal", "FootYellow",
    "FootBall", "BlackLivesMatter", "ExtraLife", "VirtualHug", "BOP", "SingsNote",
    "SingsMic", "TwitchSings", "SoonerLater", "HolidayTree", "HolidaySanta",
    "HolidayPresent", "HolidayLog", "HolidayCookie", "PixelBob", "FBPenalty",
    "FBChallenge", "FBCatch", "FBBlock", "FBSpiral", "FBPass", "FBRun", "MaxLOL",
    "TwitchRPG", "PinkMercy", "MercyWing2", "MercyWing1", "PartyHat", "EarthDay",
    "TombRaid", "PopCorn", "FBtouchdown", "TPFufun", "TwitchVotes", "DarkMode",
    "HSWP", "HSCheers", "PowerUpL", "PowerUpR", "LUL", "EntropyWins",
    "TPcrunchyroll", "TwitchUnity", "Squid4", "Squid3", "Squid2", "Squid1",
    "CrreamAwk", "CarlSmile", "TwitchLit", "TehePelo", "TearGlove", "SabaPing",
    "PunOko", "KonCha", "Kappu", "InuyoFace", "BigPhish", "BegWan", "ThankEgg",
    "MorphinTime", "TheIlluminati", "TBAngel", "MVGame", "NinjaGrumpy", "PartyTime",
    "RlyTho", "UWot", "YouDontSay", "KAPOW", "ItsBoshyTime", "CoolStoryBob",
    "TriHard", "SuperVinlin", "FreakinStinkin", "Poooound", "CurseLit", "BatChest",
    "BrainSlug", "PrimeMe", "StrawBeary", "RaccAttack", "UncleNox", "WTRuck",
    "TooSpicy", "Jebaited", "DogFace", "BlargNaut", "TakeNRG", "GivePLZ",
    "imGlitch", "pastaThat", "copyThis", "UnSane", "DatSheffy", "TheTarFu",
    "PicoMause", "TinyFace", "DxCat", "RuleFive", "VoteNay", "VoteYea", "PJSugar",
    "DoritosChip", "OpieOP", "FutureMan", "ChefFrank", "StinkyCheese", "NomNom",
    "SmoocherZ", "cmonBruh", "KappaWealth", "MikeHogu", "VoHiYo", "KomodoHype",
    "SeriousSloth", "OSFrog", "OhMyDog", "KappaClaus", "KappaRoss", "MingLee",
    "SeemsGood", "twitchRaid", "bleedPurple", "duDudu", "riPepperonis", "NotLikeThis",
    "DendiFace", "CoolCat", "KappaPride", "ShadyLulu", "ArgieB8", "CorgiDerp",
    "PraiseIt", "TTours", "mcaT", "NotATK", "HeyGuys", "Mau5", "PRChase", "WutFace",
    "BuddhaBar", "PermaSmug", "panicBasket", "BabyRage", "HassaanChop", "TheThing",
    "RitzMitz", "YouWHY", "PipeHype", "BrokeBack", "ANELE", "PanicVis",
    "GrammarKing", "PeoplesChamp", "SoBayed", "BigBrother", "Keepo", "Kippa",
    "RalpherZ", "TF2John", "ThunBeast", "WholeWheat", "DAESuppy", "FailFish",
    "HotPokket", "4Head", "ResidentSleeper", "FUNgineer", "PMSTwin", "ShazBotstix",
    "AsianGlow", "DBstyle", "BloodTrail", "OneHand", "FrankerZ", "SMOrc",
    "ArsonNoSexy", "PunchTrees", "SSSsss", "Kreygasm", "KevinTurtle", "PJSalt",
    "SwiftRage", "DansGame", "GingerPower", "BCWarrior", "MrDestructoid",
    "JonCarnage", "Kappa", "RedCoat", "TheRinger", "StoneLightning", "OptimizePrime",
    "JKanStyle", "R)", ";P", ":P", ";)", ":/", "<3", ":O", "B)", "O_o", ":|", ">", ":D", ":(", ":)"
]

threads = {200}

class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    RESET = '\033[0m'

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

BANNER = f"""
{Colors.CYAN}╔══════════════════════════════════════════════════════════╗
║{Colors.WHITE}{Colors.BOLD}           ReviveX TWITCH ChatSpam{Colors.RESET}{Colors.CYAN}                  ║
╚══════════════════════════════════════════════════════════╝{Colors.RESET}
"""

class Spammer:
    def __init__(self, concurrent=50):
        self.tokens = self.load_tokens()
        self.proxies = self.load_proxies()
        self.messages = []
        self.concurrent = concurrent
        self.sent = 0
        self.failed = 0
        self.channel_id = None
        self.channel_name = None
        self.running = True
        self.bad_proxies = set()
        self.bad_tokens = set()
        self.counter = 0
        self.last_activity = datetime.now()
        self.target_count = 0  # 0 = unlimited
        self.auto_follow = True  # Auto-follow to bypass follow-only mode
        self.spam_mode = "regular"  # regular, emote_only, ai
        self.use_emotes_only = False
        
    def load_tokens(self):
        try:
            with open("tokens.txt") as f:
                return [line.strip().replace("oauth:", "").strip() for line in f if line.strip()]
        except:
            return []
    
    def parse_proxy(self, p):
        p = p.strip()
        if not p:
            return None
        
        parts = p.split(':')
        if len(parts) == 4:
            host = parts[0]
            port = parts[1]
            user = parts[2]
            password = parts[3]
            return f"http://{user}:{password}@{host}:{port}"
        
        if p.startswith(('http://', 'https://')):
            return p
        
        if '@' in p:
            return f"http://{p}"
        
        if re.match(r'\d+\.\d+\.\d+\.\d+:\d+', p):
            return f"http://{p}"
        
        return None
    
    def load_proxies(self):
        try:
            with open("proxies.txt") as f:
                return [self.parse_proxy(p) for p in f if self.parse_proxy(p)]
        except:
            return []
    
    def get_channel(self):
        print(f"\n{Colors.CYAN}Enter channel name:")
        while True:
            try:
                # Clear any pending input and show fresh prompt
                print(f"\r{Colors.CYAN}Channel: {Colors.RESET}", end="", flush=True)
                channel = input().strip()
                if channel and not channel.startswith('[') and not channel.startswith('<'):  # Filter out log messages
                    self.channel_name = channel
                    print(f"\n{Colors.GREEN}[INFO]{Colors.RESET} Target channel: #{channel}")
                    return channel
                else:
                    print(f"\n{Colors.RED}[ERROR]{Colors.RESET} Please enter a valid channel name (not a log message)")
            except KeyboardInterrupt:
                print(f"\n{Colors.YELLOW}[CANCELLED]{Colors.RESET} Channel input cancelled")
                raise
            except Exception as e:
                print(f"\n{Colors.RED}[ERROR]{Colors.RESET} Input error: {e}")
                continue
    
    def get_spam_mode(self):
        print(f"\n{Colors.CYAN}┌─[{Colors.WHITE}Spam Mode{Colors.CYAN}]─{Colors.RESET}")
        print(f"{Colors.CYAN}│{Colors.RESET}  {Colors.YELLOW}1. Regular Spam - Standard message spam{Colors.RESET}")
        print(f"{Colors.CYAN}│{Colors.RESET}  {Colors.YELLOW}2. Emote-Only Spam - Bypass emote-only mode{Colors.RESET}")
        print(f"{Colors.CYAN}│{Colors.RESET}  {Colors.YELLOW}3. AI Spam - Smart AI-generated messages (coming soon){Colors.RESET}")
        
        while True:
            choice = input(f"{Colors.CYAN}└─▶{Colors.RESET} Enter choice (1-3): ").strip()
            if choice == "1":
                self.spam_mode = "regular"
                self.use_emotes_only = False
                print(f"{Colors.GREEN}[INFO]{Colors.RESET} Regular spam mode selected")
                break
            elif choice == "2":
                self.spam_mode = "emote_only"
                self.use_emotes_only = True
                print(f"{Colors.GREEN}[INFO]{Colors.RESET} Emote-only spam mode selected")
                print(f"{Colors.YELLOW}[INFO]{Colors.RESET} Global emotes will be automatically added")
                break
            elif choice == "3":
                self.spam_mode = "ai"
                self.use_emotes_only = False
                print(f"{Colors.YELLOW}[INFO]{Colors.RESET} AI spam mode coming soon - using regular mode")
                self.spam_mode = "regular"
                self.use_emotes_only = False
                break
            else:
                print(f"{Colors.RED}[ERROR]{Colors.RESET} Please enter 1, 2, or 3")
    
    def enhance_message(self, msg):
        """Generate emote-only spam messages"""
        if not self.use_emotes_only:
            return msg
            
        # Generate 3-4 random global emotes for emote-only spam
        num_emotes = random.randint(3, 4)
        emotes = random.sample(GLOBAL_EMOTES, min(num_emotes, len(GLOBAL_EMOTES)))
        
        # Return only emotes, no user message
        return " ".join(emotes)
    
    def get_messages(self):
        if self.use_emotes_only:
            print(f"\n{Colors.CYAN}┌─[{Colors.WHITE}Messages{Colors.CYAN}]─{Colors.RESET}")
            print(f"{Colors.CYAN}│{Colors.RESET}  {Colors.GREEN}Emote-only mode - will spam 3-4 random emotes per message{Colors.RESET}")
            print(f"{Colors.CYAN}└─▶{Colors.RESET} {Colors.YELLOW}No message input needed{Colors.RESET}")
            # Add dummy message so the list isn't empty
            self.messages.append("emote_only_spam")
        else:
            print(f"\n{Colors.CYAN}┌─[{Colors.WHITE}Messages{Colors.CYAN}]─{Colors.RESET}")
            print(f"{Colors.CYAN}│{Colors.RESET}  {Colors.YELLOW}(one per line, empty line to finish){Colors.RESET}")
            
            while True:
                msg = input(f"{Colors.CYAN}├─▶{Colors.RESET} ").strip()
                if not msg:
                    break
                self.messages.append(msg)
    
    def get_target_count(self):
        print(f"\n{Colors.CYAN}┌─[{Colors.WHITE}Target Count{Colors.CYAN}]─{Colors.RESET}")
        print(f"{Colors.CYAN}│{Colors.RESET}  {Colors.YELLOW}(0 = unlimited, send until stopped){Colors.RESET}")
        while True:
            try:
                count = input(f"{Colors.CYAN}└─▶{Colors.RESET} ").strip()
                count = int(count)
                if count >= 0:
                    self.target_count = count
                    if count == 0:
                        print(f"{Colors.GREEN}[INFO]{Colors.RESET} Will send continuously until stopped")
                    else:
                        print(f"{Colors.GREEN}[INFO]{Colors.RESET} Will send exactly {count} messages")
                    return
                else:
                    print(f"{Colors.RED}[ERROR]{Colors.RESET} Please enter 0 or a positive number")
            except ValueError:
                print(f"{Colors.RED}[ERROR]{Colors.RESET} Please enter a valid number")
        
    def get_proxy(self):
        if not self.proxies:
            return None
        good = [p for p in self.proxies if p not in self.bad_proxies]
        if not good:
            self.bad_proxies.clear()
            good = self.proxies
        return random.choice(good)

    async def get_id(self, session, username):
        data = json.dumps([{
            "operationName": "GetIDFromLogin",
            "variables": {"login": username},
            "extensions": {
                "persistedQuery": {
                    "version": 1,
                    "sha256Hash": "94e82a7b1e3c21e186daa73ee2afc4b8f23bade1fbbff6fe8ac133f50a2f58ca"
                }
            }
        }])
        
        for _ in range(3):
            try:
                p = self.get_proxy()
                async with session.post("https://gql.twitch.tv/gql", 
                                       headers={"Client-Id": "kimne78kx3ncx6brgo4mv6wki5h1ko", 
                                               "Content-Type": "application/json"},
                                       data=data, proxy=p, timeout=10) as r:
                    if r.status == 200:
                        j = await r.json()
                        if j and j[0].get("data", {}).get("user"):
                            user_id = j[0]["data"]["user"]["id"]
                            print(f"{Colors.GREEN}[ID]{Colors.RESET} Channel ID: {user_id}")
                            return user_id
            except:
                if p:
                    self.bad_proxies.add(p)
                await asyncio.sleep(1)
        return None

    async def check_follow(self, session, token):
        """Check if token follows the channel"""
        p = self.get_proxy()
        headers = {
            "Authorization": f"OAuth {token}",
            "Client-Id": "kimne78kx3ncx6brgo4mv6wki5h1ko"
        }
        
        # Use a simpler follow check method
        data = json.dumps([{
            "operationName": "ChannelFollows",
            "variables": {
                "channelLogin": self.channel_name,
                "limit": 1
            },
            "extensions": {
                "persistedQuery": {
                    "version": 1,
                    "sha256Hash": "3b8b765ed18fa4c89b4369e2c0db9a0d8f1a3b8b8b8b8b8b8b8b8b8b8b8b"
                }
            }
        }])
        
        try:
            async with session.post("https://gql.twitch.tv/gql", 
                                   headers=headers, data=data, 
                                   proxy=p, timeout=5) as r:
                if r.status == 200:
                    result = await r.json()
                    # For now, assume we need to follow and skip the check
                    return False
        except:
            if p:
                self.bad_proxies.add(p)
        return False
    
    async def follow_channel(self, session, token):
        p = self.get_proxy()
        
        headers = {
            "Authorization": f"OAuth {token}",
            "Client-Id": "kimne78kx3ncx6brgo4mv6wki5h1ko",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Origin": "https://www.twitch.tv",
            "Referer": "https://www.twitch.tv/"
        }
        
        data = json.dumps([{
            "operationName": "FollowUserMutation",
            "variables": {
                "targetId": str(self.channel_id),
                "disableNotifications": False
            },
            "extensions": {
                "persistedQuery": {
                    "version": 1,
                    "sha256Hash": "cd112d9483ede85fa0da514a5657141c24396efbc7bac0ea3623e839206573b8"
                }
            }
        }])
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                async with session.post("https://gql.twitch.tv/gql", 
                                       data=data, headers=headers, 
                                       proxy=p, timeout=10) as r:
                    if r.status in (200, 204):
                        return True
            except aiohttp.ClientConnectorError:
                if p:
                    self.bad_proxies.add(p)
                # Try with different proxy
                p = self.get_proxy()
                await asyncio.sleep(1)
                continue
            except aiohttp.ClientError:
                if p:
                    self.bad_proxies.add(p)
                await asyncio.sleep(0.5)
                continue
            except Exception:
                if p:
                    self.bad_proxies.add(p)
                await asyncio.sleep(0.3)
                continue
                
            # Wait between retries
            if attempt < max_retries - 1:
                await asyncio.sleep(0.5)
                
        return False
    
    async def send(self, session, token, msg):
        p = self.get_proxy()
        if token in self.bad_tokens:
            return False
            
        headers = {
            "Authorization": f"OAuth {token}",
            "Client-Id": "kimne78kx3ncx6brgo4mv6wki5h1ko",
            "Content-Type": "application/json"
        }
        
        # Enhance message with emotes if emote-only mode is enabled
        enhanced_msg = self.enhance_message(msg)
        
        payload = {
            "operationName": "sendChatMessage",
            "variables": {
                "input": {
                    "channelID": self.channel_id,
                    "message": enhanced_msg,
                    "nonce": str(random.randint(1, 999999999))
                }
            },
            "extensions": {
                "persistedQuery": {
                    "version": 1,
                    "sha256Hash": "0435464292cf380ed4b3d905e4edcb73078362e82c06367a5b2181c76c822fa2"
                }
            }
        }
        
        try:
            # First, try to follow the channel
            if self.auto_follow:
                follow_success = await self.follow_channel(session, token)
                if follow_success:
                    print(f"{Colors.YELLOW}[FOLLOW]{Colors.RESET} Followed channel")
                
            # Small delay after following
            await asyncio.sleep(0.2)
                    
            # Now try to send the message
            async with session.post("https://gql.twitch.tv/gql", 
                                   headers=headers, json=payload, 
                                   proxy=p, timeout=5) as r:
                if r.status == 200:
                    data = await r.json()
                    if "errors" not in data:
                        return True
                    else:
                        err = data["errors"].get("message", "") if isinstance(data["errors"], dict) else data["errors"][0].get("message", "")
                        # Check for follow-only error
                        if "follow" in err.lower() or "subscriber" in err.lower() or "slow mode" in err.lower():
                            # Try to follow and retry once
                            if self.auto_follow and await self.follow_channel(session, token):
                                print(f"{Colors.YELLOW}[RETRY]{Colors.RESET} Following and retrying...")
                                # Retry the message after following
                                await asyncio.sleep(0.5)  # Small delay
                                async with session.post("https://gql.twitch.tv/gql", 
                                                       headers=headers, json=payload, 
                                                       proxy=p, timeout=5) as r2:
                                    if r2.status == 200:
                                        data2 = await r2.json()
                                        if "errors" not in data2:
                                            return True
                        if "invalid" in err or "expired" in err:
                            self.bad_tokens.add(token)
        except:
            if p:
                self.bad_proxies.add(p)
        return False

    async def worker(self, session, q, wid):
        fails = 0
        while self.running:
            try:
                token = await asyncio.wait_for(q.get(), 1.0)
                msg = random.choice(self.messages)
                
                ok = await self.send(session, token, msg)
                
                if ok:
                    self.sent += 1
                    self.counter += 1
                    self.last_activity = datetime.now()
                    fails = 0
                    
                    # Show the actual message being sent
                    if self.use_emotes_only:
                        # For emote-only mode, show the emotes that were actually sent
                        actual_msg = self.enhance_message(msg)
                        print(f"{Colors.GREEN}[{self.counter}/{self.target_count if self.target_count > 0 else '∞'}]{Colors.RESET} {actual_msg}")
                    else:
                        # For regular mode, show the user message
                        print(f"{Colors.GREEN}[{self.counter}/{self.target_count if self.target_count > 0 else '∞'}]{Colors.RESET} {msg[:20]}...")
                    
                    # Stop if target reached (and not unlimited)
                    if self.target_count > 0 and self.counter >= self.target_count:
                        print(f"\n{Colors.GREEN}[COMPLETE]{Colors.RESET} Target of {self.target_count} messages reached!")
                        self.running = False
                        break
                else:
                    self.failed += 1
                    fails += 1
                    print(f"{Colors.RED}x{Colors.RESET}", end="", flush=True)
                
                if fails > 10:
                    await asyncio.sleep(3)
                    fails = 0
                
                if token not in self.bad_tokens:
                    await q.put(token)
                    
            except asyncio.TimeoutError:
                if q.empty() and self.sent > 0:
                    for t in self.tokens:
                        if t not in self.bad_tokens:
                            await q.put(t)
            except asyncio.CancelledError:
                break
            except:
                pass

    async def run(self):
        print(f"\n{Colors.CYAN}{'='*60}{Colors.RESET}")
        print(f"{Colors.CYAN}           TWITCH CHAT BOT SETUP{Colors.RESET}")
        print(f"{Colors.CYAN}{'='*60}{Colors.RESET}")
        
        self.get_channel()
        self.get_spam_mode()
        self.get_messages()
        self.get_target_count()
        
        if not self.tokens:
            print(f"{Colors.RED}[ERROR]{Colors.RESET} No tokens")
            return
        
        print()
        
        async with aiohttp.ClientSession() as s:
            self.channel_id = await self.get_id(s, self.channel_name)
            if not self.channel_id:
                return
            
            if self.target_count == 0:
                print(f"{Colors.GREEN}[running]{Colors.RESET} Spamming #{self.channel_name} (unlimited)")
            else:
                print(f"{Colors.GREEN}[running]{Colors.RESET} Spamming #{self.channel_name} (target: {self.target_count})")
            print(f"{Colors.YELLOW}Press Ctrl+C to stop{Colors.RESET}\n")
            
            q = asyncio.Queue()
            for t in self.tokens:
                if t not in self.bad_tokens:
                    await q.put(t)
            
            workers = []
            for i in range(min(self.concurrent, len(self.tokens))):
                workers.append(asyncio.create_task(self.worker(s, q, i+1)))
            
            try:
                await asyncio.sleep(999999)
            except KeyboardInterrupt:
                print(f"\n\n{Colors.YELLOW}[STOP]{Colors.RESET} Stopping...")
            finally:
                self.running = False
                for w in workers:
                    w.cancel()
                await asyncio.gather(*workers, return_exceptions=True)
                
                total = self.sent + self.failed
                rate = (self.sent / total * 100) if total > 0 else 0
                
                print(f"\n{Colors.CYAN}═══════ RESULTS ═══════{Colors.RESET}")
                print(f"{Colors.GREEN}Sent:{Colors.RESET}     {self.sent}")
                print(f"{Colors.RED}Failed:{Colors.RESET}   {self.failed}")
                print(f"{Colors.YELLOW}Rate:{Colors.RESET}     {rate:.1f}%")
                print(f"{Colors.CYAN}═══════════════════════{Colors.RESET}")

async def main():
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    bot = Spammer()
    await bot.run()

if __name__ == "__main__":
    asyncio.run(main())
