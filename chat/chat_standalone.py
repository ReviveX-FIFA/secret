#!/usr/bin/env python3
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

class ChatSpammer:
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
        self.target_count = 0
        self.auto_follow = True
        self.spam_mode = "regular"
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
        print(f"\n{Colors.CYAN}{'='*50}{Colors.RESET}")
        print(f"{Colors.CYAN}         TWITCH CHAT SPAMMER{Colors.RESET}")
        print(f"{Colors.CYAN}{'='*50}{Colors.RESET}")
        
        while True:
            try:
                channel = input(f"\n{Colors.YELLOW}Enter channel name: {Colors.RESET}").strip()
                if channel and not channel.startswith('[') and not channel.startswith('<') and not channel.startswith('DEBUG'):
                    self.channel_name = channel
                    print(f"{Colors.GREEN}[OK]{Colors.RESET} Target channel: #{channel}")
                    return channel
                else:
                    print(f"{Colors.RED}[ERROR]{Colors.RESET} Please enter a valid channel name")
            except KeyboardInterrupt:
                print(f"\n{Colors.YELLOW}[CANCELLED]{Colors.RESET} Exiting...")
                sys.exit(0)
            except Exception as e:
                print(f"{Colors.RED}[ERROR]{Colors.RESET} Input error: {e}")
                continue
    
    def get_spam_mode(self):
        print(f"\n{Colors.CYAN}Select spam mode:{Colors.RESET}")
        print(f"{Colors.YELLOW}1.{Colors.RESET} Regular Spam")
        print(f"{Colors.YELLOW}2.{Colors.RESET} Emote-Only Spam")
        print(f"{Colors.YELLOW}3.{Colors.RESET} AI Spam (coming soon)")
        
        while True:
            try:
                choice = input(f"\n{Colors.YELLOW}Choice (1-3): {Colors.RESET}").strip()
                if choice == "1":
                    self.spam_mode = "regular"
                    self.use_emotes_only = False
                    print(f"{Colors.GREEN}[OK]{Colors.RESET} Regular spam mode selected")
                    break
                elif choice == "2":
                    self.spam_mode = "emote_only"
                    self.use_emotes_only = True
                    print(f"{Colors.GREEN}[OK]{Colors.RESET} Emote-only spam mode selected")
                    break
                elif choice == "3":
                    print(f"{Colors.YELLOW}[INFO]{Colors.RESET} AI spam coming soon - using regular mode")
                    self.spam_mode = "regular"
                    self.use_emotes_only = False
                    break
                else:
                    print(f"{Colors.RED}[ERROR]{Colors.RESET} Please enter 1, 2, or 3")
            except KeyboardInterrupt:
                print(f"\n{Colors.YELLOW}[CANCELLED]{Colors.RESET} Exiting...")
                sys.exit(0)
    
    def get_messages(self):
        if self.use_emotes_only:
            print(f"\n{Colors.GREEN}[INFO]{Colors.RESET} Emote-only mode - will spam random emotes")
            self.messages.append("emote_only_spam")
        else:
            print(f"\n{Colors.CYAN}Enter messages (one per line, empty line to finish):{Colors.RESET}")
            while True:
                try:
                    msg = input(f"{Colors.CYAN}> {Colors.RESET}").strip()
                    if not msg:
                        break
                    self.messages.append(msg)
                except KeyboardInterrupt:
                    print(f"\n{Colors.YELLOW}[CANCELLED]{Colors.RESET} Exiting...")
                    sys.exit(0)
    
    def get_target_count(self):
        while True:
            try:
                count = input(f"\n{Colors.YELLOW}Target count (0 = unlimited): {Colors.RESET}").strip()
                count = int(count)
                if count >= 0:
                    self.target_count = count
                    if count == 0:
                        print(f"{Colors.GREEN}[OK]{Colors.RESET} Will send continuously until stopped")
                    else:
                        print(f"{Colors.GREEN}[OK]{Colors.RESET} Will send exactly {count} messages")
                    return
                else:
                    print(f"{Colors.RED}[ERROR]{Colors.RESET} Please enter 0 or a positive number")
            except ValueError:
                print(f"{Colors.RED}[ERROR]{Colors.RESET} Please enter a valid number")
            except KeyboardInterrupt:
                print(f"\n{Colors.YELLOW}[CANCELLED]{Colors.RESET} Exiting...")
                sys.exit(0)
    
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
                            print(f"{Colors.GREEN}[OK]{Colors.RESET} Channel ID: {user_id}")
                            return user_id
            except:
                if p:
                    self.bad_proxies.add(p)
                await asyncio.sleep(1)
        return None

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
        if self.use_emotes_only:
            num_emotes = random.randint(3, 4)
            emotes = random.sample(GLOBAL_EMOTES, min(num_emotes, len(GLOBAL_EMOTES)))
            enhanced_msg = " ".join(emotes)
        else:
            enhanced_msg = msg
        
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
            async with session.post("https://gql.twitch.tv/gql", 
                                   headers=headers, json=payload, 
                                   proxy=p, timeout=5) as r:
                if r.status == 200:
                    data = await r.json()
                    if "errors" not in data:
                        return True
                    else:
                        err = data["errors"].get("message", "") if isinstance(data["errors"], dict) else data["errors"][0].get("message", "")
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
                    
                    if self.use_emotes_only:
                        num_emotes = random.randint(3, 4)
                        emotes = random.sample(GLOBAL_EMOTES, min(num_emotes, len(GLOBAL_EMOTES)))
                        actual_msg = " ".join(emotes)
                        print(f"{Colors.GREEN}[{self.counter}/{self.target_count if self.target_count > 0 else 'INF'}]{Colors.RESET} {actual_msg}")
                    else:
                        print(f"{Colors.GREEN}[{self.counter}/{self.target_count if self.target_count > 0 else 'INF'}]{Colors.RESET} {msg[:30]}...")
                    
                    if self.target_count > 0 and self.counter >= self.target_count:
                        print(f"\n{Colors.GREEN}[COMPLETE]{Colors.RESET} Target reached!")
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
        self.get_channel()
        self.get_spam_mode()
        self.get_messages()
        self.get_target_count()
        await self._execute_spam()
    
    async def run_non_interactive(self):
        # Skip all interactive setup, use pre-set values
        if not self.tokens:
            print(f"{Colors.RED}[ERROR]{Colors.RESET} No tokens found in tokens.txt")
            input(f"{Colors.YELLOW}Press Enter to exit...{Colors.RESET}")
            return
        
        await self._execute_spam()
    
    async def _execute_spam(self):
        print(f"\n{Colors.GREEN}[STARTING]{Colors.RESET} Initializing spam...")
        
        async with aiohttp.ClientSession() as s:
            self.channel_id = await self.get_id(s, self.channel_name)
            if not self.channel_id:
                print(f"{Colors.RED}[ERROR]{Colors.RESET} Could not get channel ID")
                input(f"{Colors.YELLOW}Press Enter to exit...{Colors.RESET}")
                return
            
            print(f"{Colors.GREEN}[RUNNING]{Colors.RESET} Spamming #{self.channel_name}")
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
                print(f"\n{Colors.YELLOW}[STOPPING]{Colors.RESET} Stopping spam...")
            finally:
                self.running = False
                for w in workers:
                    w.cancel()
                await asyncio.gather(*workers, return_exceptions=True)
                
                total = self.sent + self.failed
                rate = (self.sent / total * 100) if total > 0 else 0
                
                print(f"\n{Colors.CYAN}{'='*30} RESULTS {'='*30}{Colors.RESET}")
                print(f"{Colors.GREEN}Sent:{Colors.RESET}     {self.sent}")
                print(f"{Colors.RED}Failed:{Colors.RESET}   {self.failed}")
                print(f"{Colors.YELLOW}Rate:{Colors.RESET}     {rate:.1f}%")
                print(f"{Colors.CYAN}{'='*68}{Colors.RESET}")

async def main():
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    bot = ChatSpammer()
    
    # Check for command line arguments (like follow bot)
    if len(sys.argv) >= 2:
        # Non-interactive mode - auto-fill from Discord modal
        bot.channel_name = sys.argv[1]
        bot.target_count = int(sys.argv[3]) if len(sys.argv) > 3 and sys.argv[3].isdigit() else 100
        bot.messages = [sys.argv[2]] if len(sys.argv) > 2 else ["yo"]
        bot.use_emotes_only = sys.argv[4].lower() == "true" if len(sys.argv) > 4 else False
        
        print(f"\n{Colors.GREEN}[AUTO-MODE]{Colors.RESET} Using Discord modal inputs:")
        print(f"Channel: #{bot.channel_name}")
        print(f"Message: {bot.messages[0]}")
        print(f"Amount: {bot.target_count}")
        print(f"Emote Only: {bot.use_emotes_only}")
        
        # Skip interactive setup and go directly to execution
        await bot.run_non_interactive()
    else:
        # Interactive mode
        await bot.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}[EXIT]{Colors.RESET} Program terminated by user")
    except Exception as e:
        print(f"{Colors.RED}[FATAL ERROR]{Colors.RESET} {e}")
    finally:
        input(f"{Colors.YELLOW}Press Enter to exit...{Colors.RESET}")
