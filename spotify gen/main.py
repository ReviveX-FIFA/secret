import random
import string
import time
import json
import os
import sys
import requests
from urllib.parse import urlencode
import ctypes
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import getpass

if os.name == 'nt':
    import ctypes
    kernel32 = ctypes.windll.kernel32
    kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    CYAN = '\033[96m'
    MAGENTA = '\033[95m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

class SpotifyCLI:
    def __init__(self):
        self.amount = 1
        self.threads = 1
        self.proxy_mode = False

    def clear_screen(self):
        os.system('cls' if os.name == 'nt' else 'clear')

    def print_banner(self):
        banner = """
╔═══════════════════════════════════════════════════════════════════════════════════════╗
║   _____             __  _ ____         ______                           __            ║
║  / ___/____  ____  / /_(_) __/_  __   / ____/__  ____  ___  _________ _/ /_____  _____║
║  \\__ \/ __ \/ __ \/ __/ / /_/ / / /  / / __/ _ \/ __ \/ _ \/ ___/ __ `/ __/ __ \/ ___/║
║ ___/ / /_/ / /_/ / /_/ / __/ /_/ /  / /_/ /  __/ / / /  __/ /  / /_/ / /_/ /_/ / /    ║
║/____/ .___/\____/\__/_/_/  \__, /   \____/\___/_/ /_/\___/_/   \__,_/\__/\____/_/     ║
║    /_/                    /____/                                                      ║
╚═══════════════════════════════════════════════════════════════════════════════════════╝
                            Made by Rivalsfunds
        
        """
        print(f"{Colors.GREEN}{banner}{Colors.RESET}")

    def get_input(self, prompt: str, default: str = "", is_password: bool = False) -> str:
        if default:
            full_prompt = f"{Colors.GREEN}{prompt} [{Colors.YELLOW}{default}{Colors.GREEN}]: {Colors.RESET}"
        else:
            full_prompt = f"{Colors.GREEN}{prompt}: {Colors.RESET}"

        if is_password:
            return getpass.getpass(full_prompt).strip() or default
        else:
            return input(full_prompt).strip() or default

    def get_yes_no(self, prompt: str, default: bool = False) -> bool:
        default_str = "Y/n" if default else "y/N"
        while True:
            response = self.get_input(f"{prompt} ({default_str})", "").lower()
            if not response:
                return default
            if response in ['y', 'yes', '1']:
                return True
            elif response in ['n', 'no', '0']:
                return False
            print(f"{Colors.RED}Please enter 'y' or 'n'{Colors.RESET}")

    def get_number(self, prompt: str, default: int = 1, min_val: int = 1) -> int:
        while True:
            try:
                response = self.get_input(f"{prompt}", str(default))
                value = int(response) if response else default
                if value >= min_val:
                    return value
                print(f"{Colors.RED}Please enter a number >= {min_val}{Colors.RESET}")
            except ValueError:
                print(f"{Colors.RED}Please enter a valid number{Colors.RESET}")

    def configure_settings(self):
        print(f"{Colors.YELLOW}{Colors.BOLD}Account Creation Settings{Colors.RESET}")
        self.amount = self.get_number("Amount of accounts to create", 1, 1)
        print()

        print(f"{Colors.YELLOW}{Colors.BOLD}Performance Settings{Colors.RESET}")
        self.threads = self.get_number("Number of threads", 1, 1)
        print()

        print(f"{Colors.YELLOW}{Colors.BOLD}Proxy Configuration{Colors.RESET}")
        self.proxy_mode = self.get_yes_no("Enable proxy mode", False)
        print()

    def show_summary(self):
        print(f"{Colors.CYAN}{'─' * 50}{Colors.RESET}")
        print(f"{Colors.CYAN}{'CONFIGURATION SUMMARY':^50}{Colors.RESET}")
        print(f"{Colors.CYAN}{'─' * 50}{Colors.RESET}\n")

        print(f"{Colors.GREEN}Amount to Create:{Colors.RESET} {Colors.YELLOW}{self.amount}{Colors.RESET}")
        print(f"{Colors.GREEN}Threads:{Colors.RESET} {Colors.YELLOW}{self.threads}{Colors.RESET}")
        print(f"{Colors.GREEN}Proxy Mode:{Colors.RESET} {Colors.YELLOW}{'Enabled' if self.proxy_mode else 'Disabled'}{Colors.RESET}")
        print()

    def confirm_start(self):
        if not self.get_yes_no("Proceed with these settings", True):
            if self.get_yes_no("Reconfigure settings", True):
                self.clear_screen()
                self.print_banner()
                self.configure_settings()
                self.show_summary()
                return self.confirm_start()
            else:
                print(f"{Colors.GREEN}Goodbye!{Colors.RESET}")
                sys.exit(0)
        return True

    def run(self):
        try:
            self.clear_screen()
            self.print_banner()
            self.configure_settings()
            self.confirm_start()

            return {
                'amount': self.amount,
                'threads': self.threads,
                'proxy_mode': self.proxy_mode
            }
        except KeyboardInterrupt:
            print(f"\n{Colors.RED}Operation cancelled by user.{Colors.RESET}")
            sys.exit(0)
        except Exception as e:
            print(f"\n{Colors.RED}An error occurred: {e}{Colors.RESET}")
            sys.exit(1)

ARTIST_ID = "31webi2eljizsc7t45tpqr7btsoa"

SIGNUP_URL = "https://spclient.wg.spotify.com/signup/public/v1/account"
ACCOUNTS_BASE = "https://accounts.spotify.com"

created_count = 0
failed_count = 0
start_time = time.time()
stats_lock = threading.Lock()

def update_title():
    elapsed = time.time() - start_time
    aps = created_count / elapsed if elapsed > 0 else 0
    title = f"SpotifyGen | Created: {created_count} | Failed: {failed_count} | APS: {aps:.2f}"
    ctypes.windll.kernel32.SetConsoleTitleW(title)

def log_success(msg):
    print(f"{Colors.GREEN}{Colors.BOLD}[+]{Colors.RESET} {Colors.GREEN}{msg}{Colors.RESET}")

def log_error(msg):
    print(f"{Colors.RED}{Colors.BOLD}[x]{Colors.RESET} {Colors.RED}{msg}{Colors.RESET}")

def log_proxy_error(msg):
    print(f"{Colors.YELLOW}{Colors.BOLD}[-]{Colors.RESET} {Colors.YELLOW}{msg}{Colors.RESET}")

FIRST_NAMES = [
    "james", "mary", "john", "patricia", "robert", "jennifer", "michael", "linda", 
    "william", "elizabeth", "david", "barbara", "richard", "susan", "joseph", "jessica",
    "thomas", "sarah", "charles", "karen", "daniel", "nancy", "matthew", "lisa",
    "anthony", "betty", "mark", "helen", "donald", "sandra", "steven", "donna",
    "paul", "carol", "andrew", "ruth", "joshua", "sharon", "kenneth", "michelle",
    "kevin", "laura", "brian", "emily", "george", "kimberly", "edward", "deborah",
    "ronald", "dorothy", "timothy", "amy", "jason", "angela", "jeffrey", "ashley",
    "ryan", "brenda", "jacob", "emma", "gary", "olivia", "nicholas", "ava",
    "eric", "sophia", "jonathan", "isabella", "stephen", "mia", "larry", "charlotte",
    "justin", "amelia", "scott", "evelyn", "brandon", "abigail", "benjamin", "harper",
    "samuel", "emily", "frank", "elizabeth", "gregory", "avery", "raymond", "sofia",
    "alexander", "camila", "patrick", "aria", "jack", "scarlett", "dennis", "victoria",
    "jerry", "madison", "tyler", "luna", "aaron", "grace", "jose", "chloe",
    "adam", "penelope", "nathan", "layla", "henry", "riley", "douglas", "zoe",
    "zachary", "nora", "peter", "lily", "kyle", "eleanor", "ethan", "hannah",
    "walter", "lillian", "noah", "addison", "jeremy", "aubrey", "christian", "ellie",
    "keith", "stella", "roger", "natalie", "terry", "zoey", "gerald", "leah",
    "harold", "hazel", "sean", "violet", "austin", "aurora", "carl", "savannah",
    "arthur", "audrey", "lawrence", "brooklyn", "dylan", "bella", "jesse", "claire",
    "jordan", "skylar", "bryan", "lucy", "billy", "paisley", "bruce", "everly",
    "ralph", "anna", "roy", "caroline", "eugene", "nova", "wayne", "genesis",
    "louis", "emilia", "russell", "kennedy", "alan", "kinsley", "juan", "allie",
    "gabriel", "maya", "philip", "sarah", "logan", "madelyn", "randy", "adeline",
    "harry", "alex", "isaac", "sydney", "julian", "julia", "mason", "piper",
    "evan", "ruby", "elijah", "serenity", "luke", "ivy", "jayden", "josie",
    "leo", "delilah", "lincoln", "emery", "ryan", "bailey", "caleb", "liliana",
    "owen", "valentina", "oliver", "willow", "gavin", "naomi", "wyatt", "aaliyah"
]

LAST_NAMES = [
    "smith", "johnson", "williams", "brown", "jones", "garcia", "miller", "davis",
    "rodriguez", "martinez", "hernandez", "lopez", "gonzalez", "wilson", "anderson", "thomas",
    "taylor", "moore", "jackson", "martin", "lee", "perez", "thompson", "white",
    "harris", "sanchez", "clark", "ramirez", "lewis", "robinson", "walker", "young",
    "allen", "king", "wright", "scott", "torres", "nguyen", "hill", "flores",
    "green", "adams", "nelson", "baker", "hall", "rivera", "campbell", "mitchell",
    "carter", "roberts", "gomez", "phillips", "evans", "turner", "diaz", "parker",
    "cruz", "edwards", "collins", "reyes", "stewart", "morris", "morales", "murphy",
    "cook", "rogers", "gutierrez", "ortiz", "morgan", "cooper", "peterson", "bailey",
    "reed", "kelly", "howard", "ramos", "kim", "cox", "ward", "richardson",
    "watson", "brooks", "chavez", "wood", "james", "bennett", "gray", "mendoza",
    "ruiz", "hughes", "price", "alvarez", "castillo", "sanders", "patel", "myers",
    "long", "ross", "foster", "jimenez", "powell", "jenkins", "perry", "russell",
    "sullivan", "bell", "coleman", "butler", "henderson", "barnes", "gonzales", "fisher",
    "vasquez", "simmons", "romero", "jordan", "patterson", "alexander", "hamilton", "graham",
    "reynolds", "griffin", "wallace", "moreno", "west", "cole", "hayes", "bryant",
    "herrera", "gibson", "ellis", "tran", "medina", "aguilar", "stevens", "murray",
    "ford", "castro", "marshall", "owens", "harrison", "fernandez", "mcdonald", "woods",
    "washington", "kennedy", "wells", "vargas", "henry", "chen", "freeman", "webb",
    "tucker", "guzman", "burns", "crawford", "olson", "simpson", "porter", "hunter",
    "gordon", "mendez", "silva", "shaw", "snyder", "mason", "dixon", "munoz",
    "hunt", "hicks", "holmes", "palmer", "wagner", "black", "dean", "gregory",
    "santiago", "duncan", "armstrong", "hudson", "carroll", "lane", "riley", "andrews",
    "alvarado", "ray", "delgado", "berry", "perkins", "hoffman", "johnston", "maldonado",
    "pena", "aguirre", "wheeler", "willis", "wilkins", "larson", "fowler", "douglas"
]

ADJECTIVES = ["lil", "big", "young", "old", "da", "tha", "lil", "raw", "dark", "light", "fast", "slow", "wild", "calm", "hard", "soft", "hot", "cold", "red", "blue", "green", "black", "white", "gold", "silver"]
NOUNS = ["rapper", "beats", "flows", "bars", "music", "sounds", "waves", "vibes", "tracks", "hits", "records", "albums", "songs", "tunes", "melodies", "rhythms", "notes", "lyrics", "verses", "hooks", "chorus", "bridge", "intro", "outro"]
STYLES = ["rivals", "legend", "king", "queen", "master", "god", "demon", "angel", "beast", "savage", "hero", "villain", "ghost", "shadow", "storm", "fire", "ice", "thunder", "lightning", "dragon", "wolf", "tiger", "lion", "bear", "snake", "eagle", "hawk", "shark"]

def generate_display_name(first, last):
    choice = random.randint(1, 4)

    if choice == 1:
        return f"{first.capitalize()} {last.capitalize()}"
    elif choice == 2:
        prefix = random.choice(ADJECTIVES + [first.lower()])
        suffix = random.choice(STYLES + NOUNS)
        return f"{prefix}{suffix}{random.randint(1, 999)}"
    elif choice == 3:
        adj = random.choice(ADJECTIVES).capitalize()
        style = random.choice(STYLES).capitalize()
        return f"{adj}{style}{random.randint(1, 99)}"
    else:
        word1 = random.choice(STYLES + NOUNS)
        word2 = random.choice(NOUNS + ["mode", "gang", "squad", "crew", "fam", "unit", "clan"])
        return f"{word1}{word2}{random.randint(1, 999)}"

def generate_account():
    first = random.choice(FIRST_NAMES)
    last = random.choice(LAST_NAMES)
    nums = ''.join(random.choices(string.digits, k=random.randint(2, 4)))

    email_formats = [
        f"{first}.{last}{nums}@gmail.com",
        f"{first}{last}{nums}@gmail.com",
        f"{first}_{last}{nums}@gmail.com",
        f"{first}{nums}.{last}@gmail.com",
        f"{first[0]}{last}{nums}@gmail.com",
        f"{first}{last[0]}{nums}@gmail.com",
        f"{first}{nums}{last}@gmail.com",
    ]
    email = random.choice(email_formats)

    password = (
        ''.join(random.choices(string.ascii_lowercase, k=6))
        + ''.join(random.choices(string.digits, k=3))
        + '!'
        + ''.join(random.choices(string.ascii_uppercase, k=3))
    )
    display_name = generate_display_name(first, last)
    month = random.randint(1, 12)
    day = random.randint(1, 28)
    year = random.randint(1990, 2000)
    return {
        "email": email,
        "password": password,
        "display_name": display_name,
        "month": month,
        "day": day,
        "year": year
    }

def load_proxies():
    paths = [os.path.join(os.path.dirname(__file__), "data", "proxies.txt"),
             os.path.join(os.path.dirname(__file__), "proxies.txt")]
    for path in paths:
        if os.path.exists(path):
            with open(path, "r") as f:
                proxies = [l.strip() for l in f if l.strip()]
            if proxies:
                display_path = "data\\proxies.txt" if "data" in path else "proxies.txt"
                log_success(f"Loaded {len(proxies)} proxies from {display_path}")
                return proxies
    log_error("No proxies.txt found, running without proxy")
    return []

def parse_proxy(proxy_str):
    if '@' in proxy_str:
        auth, server = proxy_str.split('@', 1)
        if ':' in auth and ':' in server:
            user, password = auth.split(':', 1)
            host, port = server.split(':', 1)
            return {
                "http": f"http://{user}:{password}@{host}:{port}",
                "https": f"http://{user}:{password}@{host}:{port}"
            }
    parts = proxy_str.split(":")
    if len(parts) == 4:
        return {
            "http": f"http://{parts[2]}:{parts[3]}@{parts[0]}:{parts[1]}",
            "https": f"http://{parts[2]}:{parts[3]}@{parts[0]}:{parts[1]}"
        }
    elif len(parts) == 2:
        return {
            "http": f"http://{parts[0]}:{parts[1]}",
            "https": f"http://{parts[0]}:{parts[1]}"
        }
    return None

def save_account(account):
    path = os.path.join(os.path.dirname(__file__), "data", "spotifyaccounts.txt")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a") as f:
        f.write(f"{account['email']}:{account['password']}\n")

def get_headers(referer=None):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36",
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Origin": "https://www.spotify.com",
        "Referer": referer or "https://www.spotify.com/ca-en/signup",
        "sec-ch-ua": '"Chromium";v="146", "Not-A.Brand";v="24", "Google Chrome";v="146"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-site",
        "Connection": "keep-alive",
        "Host": "spclient.wg.spotify.com"
    }
    return headers

def create_account_v1(session, account, proxies=None):
    data = {
        "displayname": account["display_name"],
        "creation_point": "https://login.app.spotify.com?utm_source=spotify&utm_medium=desktop-win32&utm_campaign=organic",
        "birth_month": str(account["month"]),
        "email": account["email"],
        "password": account["password"],
        "creation_flow": "desktop",
        "platform": "desktop",
        "birth_year": str(account["year"]),
        "iagree": "1",
        "key": "4c7a36d5260abca4af282779720cf631",
        "birth_day": str(account["day"]),
        "gender": "male",
        "password_repeat": account["password"],
        "referrer": ""
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36",
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Origin": "https://www.spotify.com",
        "Referer": "https://www.spotify.com/ca-en/signup",
        "Content-Type": "application/x-www-form-urlencoded",
        "Connection": "keep-alive"
    }

    try:
        r = session.post(SIGNUP_URL, headers=headers, data=data, proxies=proxies, timeout=30)

        if '{"status":1,' in r.text or '"status": 1' in r.text:
            return True, r.text

        if '"status":320' in r.text or 'proxy service' in r.text.lower():
            return False, "proxy_error"

        return False, r.text
    except Exception:
        return False, "proxy_error"

def process_account(idx, proxy_str=None, all_proxies=None):
    account = generate_account()

    proxy_candidates = []
    if proxy_str:
        proxy_candidates.append(proxy_str)
    if all_proxies:
        extras = [p for p in random.sample(all_proxies, min(5, len(all_proxies))) if p != proxy_str]
        proxy_candidates.extend(extras[:3])
    if not proxy_candidates:
        proxy_candidates = [None]

    for pi, pstr in enumerate(proxy_candidates):
        proxies = parse_proxy(pstr) if pstr else None
        session = requests.Session()
        try:
            success, result = create_account_v1(session, account, proxies)
            if success:
                save_account(account)
                
                return True
            if result == "proxy_error":
                if pi < len(proxy_candidates) - 1:
                    continue
                log_proxy_error("Proxy error")
                return False
            if pi < len(proxy_candidates) - 1:
                continue
            log_error("Account creation failed")
            return False
        except Exception:
            if pi < len(proxy_candidates) - 1:
                continue
            log_proxy_error("Proxy error")
            return False
        finally:
            session.close()
    return False

def worker_task(args):
    idx, proxy_str, all_proxies = args
    return process_account(idx, proxy_str, all_proxies)

def run_generation(amount, threads, use_proxies):
    global created_count, failed_count, start_time

    proxies = load_proxies() if use_proxies else []
    if use_proxies and not proxies:
        log_proxy_error("No proxies found, running proxyless")

    created_count = 0
    failed_count = 0
    start_time = time.time()
    next_account_idx = 1

    print(f"\n{Colors.CYAN}Starting with {threads} thread(s)...{Colors.RESET}\n")

    if threads == 1:
        while created_count < amount:
            proxy_str = random.choice(proxies) if proxies else None
            ok = process_account(next_account_idx, proxy_str, all_proxies=proxies)
            next_account_idx += 1
            with stats_lock:
                if ok:
                    created_count += 1
                    log_success(f"Account created ({created_count}/{amount})")
                else:
                    failed_count += 1
                    log_error("Account creation failed (email already registered)")
                update_title()

            if not use_proxies:
                time.sleep(5)
    else:
        with ThreadPoolExecutor(max_workers=threads) as executor:
            pending_futures = {}
            account_counter = 1

            for _ in range(min(threads * 2, amount)):
                proxy_str = random.choice(proxies) if proxies else None
                future = executor.submit(worker_task, (account_counter, proxy_str, proxies))
                pending_futures[future] = account_counter
                account_counter += 1

            while pending_futures and created_count < amount:
                done_futures = []
                for future in list(pending_futures.keys()):
                    if future.done():
                        done_futures.append(future)

                if not done_futures:
                    time.sleep(0.01)
                    continue

                for future in done_futures:
                    account_idx = pending_futures.pop(future)
                    try:
                        ok = future.result()
                        with stats_lock:
                            if ok:
                                created_count += 1
                                log_success(f"Account created ({created_count}/{amount})")
                            else:
                                failed_count += 1
                                log_error("Account creation failed (email already registered)")
                            update_title()

                        if created_count + len(pending_futures) < amount:
                            proxy_str = random.choice(proxies) if proxies else None
                            new_future = executor.submit(worker_task, (account_counter, proxy_str, proxies))
                            pending_futures[new_future] = account_counter
                            account_counter += 1
                    except Exception:
                        with stats_lock:
                            failed_count += 1
                            log_error("Account creation failed (email already registered)")
                            update_title()

                        if created_count + len(pending_futures) < amount:
                            proxy_str = random.choice(proxies) if proxies else None
                            new_future = executor.submit(worker_task, (account_counter, proxy_str, proxies))
                            pending_futures[new_future] = account_counter
                            account_counter += 1

    print(f"\n{Colors.GREEN}{'='*50}{Colors.RESET}")
    print(f"{Colors.GREEN}Done! Created: {created_count} | Failed: {failed_count}{Colors.RESET}")
    print(f"{Colors.GREEN}Saved to: data/spotifyaccounts.txt{Colors.RESET}")
    print(f"{Colors.GREEN}{'='*50}{Colors.RESET}\n")

def main():
    cli = SpotifyCLI()
    config = cli.run()

    amount = config['amount']
    threads = config['threads']
    use_proxies = config['proxy_mode']

    run_generation(amount, threads, use_proxies)

if __name__ == "__main__":
    main()
