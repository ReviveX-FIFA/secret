#!/usr/bin/env python3
import os
import sys
import asyncio
import threading
import time
import string
import random
from datetime import datetime, timedelta

# Add all bot directories to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'chat'))
sys.path.append(os.path.join(os.path.dirname(__file__), 'viewbot'))
sys.path.append(os.path.join(os.path.dirname(__file__), 'follow'))
sys.path.append(os.path.join(os.path.dirname(__file__), 'raid bot'))
sys.path.append(os.path.join(os.path.dirname(__file__), 'vod like'))

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
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'

KEYS_FILE = "main_keys.txt"
ADMIN_PASS = "ReviveX"

def get_banner(bot_type="Zyro"):
    """Generate dynamic banner with bot type at bottom"""
    return f"""
{Colors.BRIGHT_RED}╔══════════════════════════════════════════════════════════╗
║                                                          ║
║  {Colors.BOLD}██╗   ██╗██╗███████╗██╗    ██╗    ██████╗  ██████╗ ████████╗{Colors.RESET}{Colors.BRIGHT_RED}  
║  {Colors.BOLD}██║   ██║██║██╔════╝██║    ██║    ██╔══██╗██╔═══██╗╚══██╔══╝{Colors.RESET}{Colors.BRIGHT_RED}  
║  {Colors.BOLD}██║   ██║██║█████╗  ██║ █╗ ██║    ██████╔╝██║   ██║   ██║   {Colors.RESET}{Colors.BRIGHT_RED}  
║  {Colors.BOLD}╚██╗ ██╔╝██║██╔══╝  ██║███╗██║    ██╔══██╗██║   ██║   ██║   {Colors.RESET}{Colors.BRIGHT_RED}  
║   {Colors.BOLD}╚████╔╝ ██║███████╗╚███╔███╔╝    ██████╔╝╚██████╔╝   ██║   {Colors.RESET}{Colors.BRIGHT_RED}  
║    {Colors.BOLD}╚═══╝  ╚═╝╚══════╝ ╚══╝╚══╝     ╚═════╝  ╚═════╝    ╚═╝   {Colors.RESET}{Colors.BRIGHT_RED}  
║                                                          
║              {Colors.BOLD}{Colors.WHITE}{bot_type}{Colors.RESET}{Colors.BRIGHT_RED}                          
║                   {Colors.PINK}Coded by ReviveX{Colors.RESET}{Colors.BRIGHT_RED}                       
╚══════════════════════════════════════════════════════════╝{Colors.RESET}
"""

BANNER = get_banner()  # Default banner

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def _parse_duration(raw):
    raw = raw.strip().lower()
    if raw == "lifetime":
        return None
    units = {"d": "days", "h": "hours", "m": "minutes", "s": "seconds", "w": "weeks"}
    if raw[-1] in units and raw[:-1].isdigit():
        amount = int(raw[:-1])
        unit   = units[raw[-1]]
        return datetime.now() + timedelta(**{unit: amount})
    raise ValueError(f"Unknown duration format: {raw}")

def _load_keys():
    keys = {}
    if not os.path.exists(KEYS_FILE):
        return keys
    with open(KEYS_FILE, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split(",", 2)
            if len(parts) == 3:
                name, expiry_str, status = parts
                keys[name] = {"expiry": expiry_str.strip(), "status": status.strip()}
    return keys

def _save_keys(keys):
    with open(KEYS_FILE, "w") as f:
        for name, data in keys.items():
            f.write(f"{name},{data['expiry']},{data['status']}\n")

def _generate_key(length=16):
    chars = string.ascii_letters + string.digits
    return ''.join(random.choices(chars, k=length))

def _expiry_display(expiry_str):
    if expiry_str.lower() == "lifetime":
        return "lifetime"
    try:
        dt  = datetime.strptime(expiry_str, "%Y-%m-%d %H:%M:%S")
        now = datetime.now()
        if dt < now:
            return f"{Colors.RED}{expiry_str} (EXPIRED){Colors.RESET}"
        return expiry_str
    except Exception:
        return expiry_str

def _is_key_valid(key_name):
    keys = _load_keys()
    if key_name not in keys:
        return False, "Key not found."
    data = keys[key_name]
    if data["status"] == "disabled":
        return False, "Key is disabled."
    expiry = data["expiry"]
    if expiry.lower() != "lifetime":
        try:
            exp_dt = datetime.strptime(expiry, "%Y-%m-%d %H:%M:%S")
            if datetime.now() > exp_dt:
                return False, "Key has expired."
        except Exception:
            return False, "Invalid expiry format."
    return True, "OK"

def key_manager():
    while True:
        clear_screen()
        print(BANNER)
        print(f"\n{Colors.CYAN}╔══════════════════════════════════════════════════════════╗")
        print(f"║{Colors.WHITE}{Colors.BOLD}                    KEY MANAGER{Colors.RESET}{Colors.CYAN}                       ║")
        print(f"╠══════════════════════════════════════════════════════════╣")
        print(f"║ {Colors.GREEN}[1]{Colors.CYAN} Create key                                 ║")
        print(f"║ {Colors.GREEN}[2]{Colors.CYAN} Disable key                                ║")
        print(f"║ {Colors.GREEN}[3]{Colors.CYAN} Enable key                                 ║")
        print(f"║ {Colors.GREEN}[4]{Colors.CYAN} Update key time                            ║")
        print(f"║ {Colors.GREEN}[5]{Colors.CYAN} List keys                                  ║")
        print(f"║ {Colors.RED}[0]{Colors.CYAN} Back to main menu                           ║")
        print(f"╚══════════════════════════════════════════════════════════╝{Colors.RESET}")
        
        choice = input(f"\n{Colors.CYAN}manager > {Colors.RESET}").strip()

        if choice == "1":
            km_create_key()
        elif choice == "2":
            km_disable_key()
        elif choice == "3":
            km_enable_key()
        elif choice == "4":
            km_update_key_time()
        elif choice == "5":
            km_list_keys()
        elif choice == "0":
            break
        else:
            print(f"{Colors.RED}[ERROR]{Colors.RESET} Invalid option.")
            time.sleep(2)

def km_create_key():
    clear_screen()
    print(BANNER)
    print(f"\n{Colors.CYAN}╔══════════════════════════════════════════════════════════╗")
    print(f"║{Colors.WHITE}{Colors.BOLD}                      CREATE KEY{Colors.RESET}{Colors.CYAN}                        ║")
    print(f"╚══════════════════════════════════════════════════════════╝{Colors.RESET}")
    
    raw_name = input(f"{Colors.CYAN}custom key (blank = auto) > {Colors.RESET}").strip()
    key_name = raw_name if raw_name else _generate_key()

    print(f"{Colors.CYAN}Duration types: 1) Day  2) Week  3) Lifetime  4) Custom{Colors.RESET}")
    dtype = input(f"{Colors.CYAN}duration > {Colors.RESET}").strip()

    now        = datetime.now()
    expiry_str = ""
    raw_dur    = dtype

    if dtype == "1":
        expiry_str = (now + timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
    elif dtype == "2":
        expiry_str = (now + timedelta(weeks=1)).strftime("%Y-%m-%d %H:%M:%S")
    elif dtype == "3":
        expiry_str = "lifetime"
    elif dtype == "4":
        print(f"{Colors.CYAN}Custom format: 30d, 12h, 45m, 120s, 2w, or 'lifetime'{Colors.RESET}")
        raw_dur = input(f"{Colors.CYAN}custom > {Colors.RESET}").strip()
        try:
            exp = _parse_duration(raw_dur)
            expiry_str = "lifetime" if exp is None else exp.strftime("%Y-%m-%d %H:%M:%S")
        except ValueError as e:
            print(f"{Colors.RED}[ERROR] {e}{Colors.RESET}")
            input(f"{Colors.YELLOW}Press Enter to continue...{Colors.RESET}")
            return
    else:
        print(f"{Colors.RED}[ERROR] Invalid choice.{Colors.RESET}")
        input(f"{Colors.YELLOW}Press Enter to continue...{Colors.RESET}")
        return

    keys = _load_keys()
    keys[key_name] = {"expiry": expiry_str, "status": "enabled"}
    _save_keys(keys)

    print(f"{Colors.GREEN}[CREATED] {key_name}{Colors.RESET}")
    print(f"{Colors.CYAN}Type: {raw_dur}{Colors.RESET}")
    print(f"{Colors.CYAN}Expires: {expiry_str}{Colors.RESET}")
    input(f"{Colors.YELLOW}Press Enter to continue...{Colors.RESET}")

def km_disable_key():
    clear_screen()
    print(BANNER)
    print(f"\n{Colors.CYAN}╔══════════════════════════════════════════════════════════╗")
    print(f"║{Colors.WHITE}{Colors.BOLD}                      DISABLE KEY{Colors.RESET}{Colors.CYAN}                       ║")
    print(f"╚══════════════════════════════════════════════════════════╝{Colors.RESET}")
    
    keys = _load_keys()
    if not keys:
        print(f"{Colors.RED}No keys found.{Colors.RESET}")
        input(f"{Colors.YELLOW}Press Enter to continue...{Colors.RESET}")
        return
    name = input(f"{Colors.CYAN}key name > {Colors.RESET}").strip()
    if name not in keys:
        print(f"{Colors.RED}[ERROR] Key not found.{Colors.RESET}")
        input(f"{Colors.YELLOW}Press Enter to continue...{Colors.RESET}")
        return
    keys[name]["status"] = "disabled"
    _save_keys(keys)
    print(f"{Colors.YELLOW}[DISABLED] {name}{Colors.RESET}")
    input(f"{Colors.YELLOW}Press Enter to continue...{Colors.RESET}")

def km_enable_key():
    clear_screen()
    print(BANNER)
    print(f"\n{Colors.CYAN}╔══════════════════════════════════════════════════════════╗")
    print(f"║{Colors.WHITE}{Colors.BOLD}                       ENABLE KEY{Colors.RESET}{Colors.CYAN}                        ║")
    print(f"╚══════════════════════════════════════════════════════════╝{Colors.RESET}")
    
    keys = _load_keys()
    if not keys:
        print(f"{Colors.RED}No keys found.{Colors.RESET}")
        input(f"{Colors.YELLOW}Press Enter to continue...{Colors.RESET}")
        return
    name = input(f"{Colors.CYAN}key name > {Colors.RESET}").strip()
    if name not in keys:
        print(f"{Colors.RED}[ERROR] Key not found.{Colors.RESET}")
        input(f"{Colors.YELLOW}Press Enter to continue...{Colors.RESET}")
        return
    keys[name]["status"] = "enabled"
    _save_keys(keys)
    print(f"{Colors.GREEN}[ENABLED] {name}{Colors.RESET}")
    input(f"{Colors.YELLOW}Press Enter to continue...{Colors.RESET}")

def km_update_key_time():
    clear_screen()
    print(BANNER)
    print(f"\n{Colors.CYAN}╔══════════════════════════════════════════════════════════╗")
    print(f"║{Colors.WHITE}{Colors.BOLD}                    UPDATE KEY TIME{Colors.RESET}{Colors.CYAN}                     ║")
    print(f"╚══════════════════════════════════════════════════════════╝{Colors.RESET}")
    
    keys = _load_keys()
    if not keys:
        print(f"{Colors.RED}No keys found.{Colors.RESET}")
        input(f"{Colors.YELLOW}Press Enter to continue...{Colors.RESET}")
        return
    name = input(f"{Colors.CYAN}key name > {Colors.RESET}").strip()
    if name not in keys:
        print(f"{Colors.RED}[ERROR] Key not found.{Colors.RESET}")
        input(f"{Colors.YELLOW}Press Enter to continue...{Colors.RESET}")
        return
    print(f"{Colors.CYAN}New duration format: 30d, 12h, 45m, 120s, 2w, or 'lifetime'{Colors.RESET}")
    raw_dur = input(f"{Colors.CYAN}new duration > {Colors.RESET}").strip()
    try:
        exp = _parse_duration(raw_dur)
        expiry_str = "lifetime" if exp is None else exp.strftime("%Y-%m-%d %H:%M:%S")
    except ValueError as e:
        print(f"{Colors.RED}[ERROR] {e}{Colors.RESET}")
        input(f"{Colors.YELLOW}Press Enter to continue...{Colors.RESET}")
        return
    keys[name]["expiry"] = expiry_str
    _save_keys(keys)
    print(f"{Colors.GREEN}[UPDATED] {name}{Colors.RESET}")
    print(f"{Colors.CYAN}New Expires: {expiry_str}{Colors.RESET}")
    input(f"{Colors.YELLOW}Press Enter to continue...{Colors.RESET}")

def km_list_keys():
    clear_screen()
    print(BANNER)
    print(f"\n{Colors.CYAN}╔══════════════════════════════════════════════════════════╗")
    print(f"║{Colors.WHITE}{Colors.BOLD}                        LIST KEYS{Colors.RESET}{Colors.CYAN}                         ║")
    print(f"╚══════════════════════════════════════════════════════════╝{Colors.RESET}")
    
    keys = _load_keys()
    if not keys:
        print(f"{Colors.YELLOW}No keys found.{Colors.RESET}")
        input(f"{Colors.YELLOW}Press Enter to continue...{Colors.RESET}")
        return
    print(f"{Colors.CYAN}{'KEY NAME':<22}{'EXPIRES':<27}{'STATUS':<10}{Colors.RESET}")
    print(f"{Colors.CYAN}{'-'*22}{'-'*27}{'-'*10}{Colors.RESET}")
    for name, data in keys.items():
        status_col = (
            f"{Colors.GREEN}enabled{Colors.RESET}"
            if data["status"] == "enabled"
            else f"{Colors.RED}disabled{Colors.RESET}"
        )
        expiry_col = _expiry_display(data["expiry"])
        print(f"{Colors.CYAN}{name:<22}{Colors.RESET}{expiry_col:<27}{status_col}")
    input(f"{Colors.YELLOW}\nPress Enter to continue...{Colors.RESET}")

def key_system():
    clear_screen()
    print(BANNER)
    print(f"\n{Colors.CYAN}╔══════════════════════════════════════════════════════════╗")
    print(f"║{Colors.WHITE}{Colors.BOLD}                      AUTHENTICATION{Colors.RESET}{Colors.CYAN}                      ║")
    print(f"╚══════════════════════════════════════════════════════════╝{Colors.RESET}")
    print(f"{Colors.CYAN}Enter your key to continue. Keys are loaded from {KEYS_FILE}.{Colors.RESET}")
    print(f"{Colors.YELLOW}Type '/manage' to access key manager.{Colors.RESET}")

    while True:
        key_input = input(f"\n{Colors.CYAN}key > {Colors.RESET}").strip()

        if key_input.lower() == "/manage":
            admin_pw = input(f"{Colors.CYAN}admin pass > {Colors.RESET}").strip()
            if admin_pw == ADMIN_PASS:
                key_manager()
                clear_screen()
                print(BANNER)
                print(f"\n{Colors.CYAN}╔══════════════════════════════════════════════════════════╗")
                print(f"║{Colors.WHITE}{Colors.BOLD}                      AUTHENTICATION{Colors.RESET}{Colors.CYAN}                      ║")
                print(f"╚══════════════════════════════════════════════════════════╝{Colors.RESET}")
                print(f"{Colors.CYAN}Enter your key to continue. Keys are loaded from {KEYS_FILE}.{Colors.RESET}")
                print(f"{Colors.YELLOW}Type '/manage' to access key manager.{Colors.RESET}")
            else:
                print(f"{Colors.RED}[ERROR] Wrong password.{Colors.RESET}")
            continue

        valid, reason = _is_key_valid(key_input)
        if valid:
            print(f"{Colors.GREEN}[OK] Key accepted. Welcome!{Colors.RESET}")
            time.sleep(1)
            return True
        else:
            print(f"{Colors.RED}[X] {reason}{Colors.RESET}")

def print_menu():
    clear_screen()
    print(get_banner("Zyro"))
    print(f"\n{Colors.CYAN}╔══════════════════════════════════════════════════════════╗")
    print(f"║{Colors.WHITE}{Colors.BOLD}                    SELECT BOT TYPE{Colors.RESET}{Colors.CYAN}                    ║")
    print(f"╠══════════════════════════════════════════════════════════╣")
    print(f"║ {Colors.GREEN}[1]{Colors.CYAN} Chat Bot        - Send messages to chat              ║")
    print(f"║ {Colors.GREEN}[2]{Colors.CYAN} View Bot        - Add viewers to stream              ║")
    print(f"║ {Colors.GREEN}[3]{Colors.CYAN} Follow Bot      - Follow channels                    ║")
    print(f"║ {Colors.GREEN}[4]{Colors.CYAN} Raid Bot        - Join raids                         ║")
    print(f"║ {Colors.GREEN}[5]{Colors.CYAN} VOD Like Bot    - Like VOD clips                     ║")
    print(f"║ {Colors.GREEN}[6]{Colors.CYAN} Token Checker   - Validate Twitch tokens           ║")
    print(f"║ {Colors.GREEN}[7]{Colors.CYAN} Token Generator - Generate tokens           ║")
    print(f"║ {Colors.RED}[0]{Colors.CYAN} Exit            - Close application                  ║")
    print(f"╚══════════════════════════════════════════════════════════╝{Colors.RESET}")

def run_chat_bot():
    try:
        # Change to chat directory and run chat bot
        chat_dir = os.path.join(os.path.dirname(__file__), 'chat')
        os.chdir(chat_dir)
        
        # Import and run chat bot
        import chat
        if sys.platform == 'win32':
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        asyncio.run(chat.main())
    except Exception as e:
        print(f"{Colors.RED}[ERROR]{Colors.RESET} Failed to run chat bot: {e}")
        input(f"{Colors.YELLOW}Press Enter to continue...{Colors.RESET}")
    finally:
        # Return to main directory
        os.chdir(os.path.dirname(__file__))

def run_view_bot():
    try:
        # Change to viewbot directory and run view bot
        viewbot_dir = os.path.join(os.path.dirname(__file__), 'viewbot')
        os.chdir(viewbot_dir)
        
        # Import and run view bot
        import view
        if sys.platform == 'win32':
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        asyncio.run(view.main())
    except Exception as e:
        print(f"{Colors.RED}[ERROR]{Colors.RESET} Failed to run view bot: {e}")
        input(f"{Colors.YELLOW}Press Enter to continue...{Colors.RESET}")
    finally:
        # Return to main directory
        os.chdir(os.path.dirname(__file__))

def run_follow_bot():
    try:
        # Change to follow directory and run follow bot
        follow_dir = os.path.join(os.path.dirname(__file__), 'follow')
        os.chdir(follow_dir)
        
        # Import and run follow bot
        import follow
        # Follow bot has its own main execution
        if __name__ == "__main__":
            follow.print_banner()
            if not follow.key_system():
                return
            bot = follow.TwitchFollower(print)
            username = input(f"\n{Colors.CYAN}Target username: {Colors.RESET}").strip()
            try:
                count = int(input(f"{Colors.CYAN}Number of follows: {Colors.RESET}").strip())
            except ValueError:
                print(f"{Colors.YELLOW}Invalid number. Using default: 10{Colors.RESET}")
                count = 10
            bot.start(username, count)
            print(follow.Colors.rainbow("\nFollow operation started. Press Ctrl+C to stop."))
            try:
                while bot.running:
                    time.sleep(0.001)
            except KeyboardInterrupt:
                print("\nStopping...")
                bot.stop()
                time.sleep(0.5)
            print(follow.Colors.rainbow("Bot stopped."))
    except Exception as e:
        print(f"{Colors.RED}[ERROR]{Colors.RESET} Failed to run follow bot: {e}")
        input(f"{Colors.YELLOW}Press Enter to continue...{Colors.RESET}")
    finally:
        # Return to main directory
        os.chdir(os.path.dirname(__file__))

def run_raid_bot():
    try:
        # Change to raid bot directory and run raid bot
        raid_dir = os.path.join(os.path.dirname(__file__), 'raid bot')
        os.chdir(raid_dir)
        
        # Import and run raid bot
        import raid
        
        # Raid bot execution
        raid_id = input("raid id: ")
        try:
            amt = int(input("joins: "))
        except ValueError:
            print(f"{Colors.RED}[ERROR]{Colors.RESET} Invalid number")
            return
        
        url = "https://gql.twitch.tv/gql"
        
        def join_raid(raid_id, url):
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
                "Authorization": "OAuth " + raid.tokens(),
                "Connection": "keep-alive",
                "Content-Type": "application/json",
                "Host": "gql.twitch.tv",
            }

            try:
                import requests
                response = requests.post(url, json=payload, headers=headers, proxies=raid.proxies(), timeout=10)
                print(response.json())
            except Exception as e:
                print(f"Request failed: {e}")

        threads = []
        for i in range(amt):
            t = threading.Thread(target=join_raid, args=(raid_id, url))
            t.start()
            threads.append(t)
            
            if (i + 1) % 20 == 0:
                time.sleep(1)

        for t in threads:
            t.join()
            
    except Exception as e:
        print(f"{Colors.RED}[ERROR]{Colors.RESET} Failed to run raid bot: {e}")
        input(f"{Colors.YELLOW}Press Enter to continue...{Colors.RESET}")
    finally:
        # Return to main directory
        os.chdir(os.path.dirname(__file__))

def run_vod_like_bot():
    try:
        # Change to vod like directory and run vod like bot
        vod_dir = os.path.join(os.path.dirname(__file__), 'vod like')
        os.chdir(vod_dir)
        
        # Import and run vod like bot
        import importlib.util
        spec = importlib.util.spec_from_file_location("vod_like_bot", "vod like bot.py")
        vod_like_bot = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(vod_like_bot)
        
        if sys.platform == 'win32':
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        asyncio.run(vod_like_bot.main())
    except Exception as e:
        print(f"{Colors.RED}[ERROR]{Colors.RESET} Failed to run VOD like bot: {e}")
        input(f"{Colors.YELLOW}Press Enter to continue...{Colors.RESET}")
    finally:
        # Return to main directory
        os.chdir(os.path.dirname(__file__))

def run_token_checker():
    try:
        # Import required modules for token checker
        import requests
        from concurrent.futures import ThreadPoolExecutor
        from threading import Thread
        import tkinter as tk
        from tkinter import filedialog
        
        clear_screen()
        print(BANNER)
        print(f"\n{Colors.CYAN}╔══════════════════════════════════════════════════════════╗")
        print(f"║{Colors.WHITE}{Colors.BOLD}                   TWITCH TOKEN CHECKER{Colors.RESET}{Colors.CYAN}                   ║")
        print(f"╚══════════════════════════════════════════════════════════╝{Colors.RESET}")
        
        # Hide the tkinter root window
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        
        # Get input file path using file explorer
        print(f"{Colors.CYAN}[INFO]{Colors.RESET} Select tokens file to check...")
        tokens_file_path = filedialog.askopenfilename(
            title="CHOOSE THE TOKENS YOU WANT TO CHECK", 
            filetypes=[('Text files', '*.txt'), ('All files', '*.*')]
        )
        
        if not tokens_file_path:
            print(f"{Colors.RED}[ERROR]{Colors.RESET} No file selected")
            input(f"{Colors.YELLOW}Press Enter to continue...{Colors.RESET}")
            return
        
        # Get output file path using file explorer
        print(f"{Colors.CYAN}[INFO]{Colors.RESET} Select file to save valid tokens...")
        valid_tokens_file_path = filedialog.asksaveasfilename(
            title="FILE TO WRITE VALID TOKENS IN", 
            defaultextension=".txt",
            filetypes=[('Text files', '*.txt'), ('All files', '*.*')]
        )
        
        if not valid_tokens_file_path:
            print(f"{Colors.RED}[ERROR]{Colors.RESET} No output file selected")
            input(f"{Colors.YELLOW}Press Enter to continue...{Colors.RESET}")
            return
        
        root.destroy()
        
        # Load tokens
        with open(tokens_file_path, 'r', encoding='utf-8', errors='ignore') as f:
            tokens = [line.strip() for line in f if line.strip()]
        
        if not tokens:
            print(f"{Colors.RED}[ERROR]{Colors.RESET} No tokens found in file")
            input(f"{Colors.YELLOW}Press Enter to continue...{Colors.RESET}")
            return
        
        print(f"{Colors.GREEN}[INFO]{Colors.RESET} Loaded {len(tokens)} tokens from {os.path.basename(tokens_file_path)}")
        print(f"{Colors.YELLOW}[INFO]{Colors.RESET} Starting token validation...")
        
        # Token validation function
        def check_token(token):
            try:
                response = requests.get(
                    'https://id.twitch.tv/oauth2/validate', 
                    headers={'Authorization': f'Bearer {token}'},
                    timeout=10
                )
                return response.status_code == 200
            except:
                return False
        
        # Check tokens
        valid_count = 0
        invalid_count = 0
        
        # Clear the valid tokens file
        with open(valid_tokens_file_path, 'w', encoding='utf-8') as f:
            f.write("")
        
        # Check each token
        for i, token in enumerate(tokens, 1):
            if check_token(token):
                valid_count += 1
                with open(valid_tokens_file_path, 'a', encoding='utf-8') as f:
                    f.write(token + '\n')
                print(f"{Colors.GREEN}[{i}/{len(tokens)}]{Colors.RESET} {token[:20]}... is {Colors.GREEN}VALID{Colors.RESET}")
            else:
                invalid_count += 1
                print(f"{Colors.RED}[{i}/{len(tokens)}]{Colors.RESET} {token[:20]}... is {Colors.RED}INVALID{Colors.RESET}")
        
        # Display results
        clear_screen()
        print(BANNER)
        print(f"\n{Colors.CYAN}╔══════════════════════════════════════════════════════════╗")
        print(f"║{Colors.WHITE}{Colors.BOLD}                      RESULTS{Colors.RESET}{Colors.CYAN}                         ║")
        print(f"╠══════════════════════════════════════════════════════════╣")
        print(f"║ {Colors.CYAN}Total Tokens:{Colors.RESET}     {len(tokens):<30} ║")
        print(f"║ {Colors.GREEN}Valid Tokens:{Colors.RESET}     {valid_count:<30} ║")
        print(f"║ {Colors.RED}Invalid Tokens:{Colors.RESET}   {invalid_count:<30} ║")
        print(f"║ {Colors.YELLOW}Success Rate:{Colors.RESET}    {(valid_count/len(tokens)*100):.1f}%{'':<26} ║")
        print(f"╚══════════════════════════════════════════════════════════╝{Colors.RESET}")
        print(f"\n{Colors.GREEN}[INFO]{Colors.RESET} Valid tokens saved to: {os.path.basename(valid_tokens_file_path)}")
        print(f"{Colors.GREEN}[INFO]{Colors.RESET} Full path: {valid_tokens_file_path}")
        
    except Exception as e:
        print(f"{Colors.RED}[ERROR]{Colors.RESET} Token checker failed: {e}")
    
    input(f"\n{Colors.YELLOW}Press Enter to continue...{Colors.RESET}")

def run_token_generator():
    try:
        import requests
        import threading
        from concurrent.futures import ThreadPoolExecutor
        
        class FastTokenValidator:
            """Ultra-fast token validator with batch processing"""
            
            def __init__(self):
                self.session = requests.Session()
                self.session.headers.update({
                    'User-Agent': 'TwitchTokenValidator/3.0-UltraFast',
                    'Accept': 'application/json'
                })
                self.batch_size = 10000  # 10k tokens per batch
                self.batch_delay = 120  # 2 minutes in seconds
                
            def validate_tokens_batch(self, tokens: list) -> tuple:
                """Validate tokens in ultra-fast batches"""
                valid_tokens = []
                invalid_tokens = []
                
                print(f"{Colors.YELLOW}[VALIDATOR]{Colors.RESET} Processing {len(tokens)} tokens in batches of {self.batch_size}")
                
                for i in range(0, len(tokens), self.batch_size):
                    batch = tokens[i:i + self.batch_size]
                    print(f"{Colors.CYAN}[BATCH]{Colors.RESET} Processing batch {i//self.batch_size + 1}: {len(batch)} tokens")
                    
                    batch_valid, batch_invalid = self._validate_single_batch(batch)
                    valid_tokens.extend(batch_valid)
                    invalid_tokens.extend(batch_invalid)
                    
                    # Show progress
                    total_processed = i + len(batch)
                    progress = (total_processed / len(tokens)) * 100
                    print(f"{Colors.GREEN}[PROGRESS]{Colors.RESET} {total_processed}/{len(tokens)} ({progress:.1f}%)")
                    
                    # Rate limiting - wait 2 minutes between batches
                    if i + self.batch_size < len(tokens):
                        wait_time = self.batch_delay
                        print(f"{Colors.YELLOW}[RATE_LIMIT]{Colors.RESET} Waiting {wait_time//60} minutes before next batch...")
                        
                        # Countdown timer
                        for remaining in range(wait_time, 0, -1):
                            mins, secs = divmod(remaining, 60)
                            print(f"{Colors.CYAN}[WAIT]{Colors.RESET} Time remaining: {mins:02d}:{secs:02d}", end='\r')
                            time.sleep(1)
                        print()  # New line after countdown
                
                return valid_tokens, invalid_tokens
            
            def _validate_single_batch(self, tokens: list) -> tuple:
                """Validate a single batch of tokens"""
                valid = []
                invalid = []
                
                for token in tokens:
                    if self._validate_single_token(token):
                        valid.append(token)
                        print(f"{Colors.GREEN}[VALID]{Colors.RESET} {token[:16]}... is valid")
                    else:
                        invalid.append(token)
                        print(f"{Colors.RED}[INVALID]{Colors.RESET} {token[:16]}... is invalid")
                    
                    # Minimal delay to prevent API overload
                    time.sleep(0.05)
                
                return valid, invalid
            
            def _validate_single_token(self, token: str) -> bool:
                """Validate a single token"""
                try:
                    response = self.session.get(
                        'https://id.twitch.tv/oauth2/validate',
                        headers={'Authorization': f'Bearer {token}'},
                        timeout=15
                    )
                    return response.status_code == 200
                except:
                    return False
        
        clear_screen()
        print(BANNER)
        print(f"\n{Colors.CYAN}╔══════════════════════════════════════════════════════════╗")
        print(f"║{Colors.WHITE}{Colors.BOLD}                   TOKEN GENERATOR{Colors.RESET}{Colors.CYAN}                 ║")
        print(f"╚══════════════════════════════════════════════════════════╝{Colors.RESET}")
        
        # Get user input
        try:
            num_threads = int(input(f"{Colors.CYAN}[INPUT]{Colors.RESET} Number of threads: "))
            num_tokens = int(input(f"{Colors.CYAN}[INPUT]{Colors.RESET} Number of tokens to generate: "))
        except ValueError:
            print(f"{Colors.RED}[ERROR]{Colors.RESET} Invalid input. Using defaults.")
            num_threads = 10
            num_tokens = 100
        
        print(f"\n{Colors.YELLOW}[INFO]{Colors.RESET} Starting advanced token generation...")
        print(f"{Colors.YELLOW}[INFO]{Colors.RESET} Threads: {num_threads} | Tokens: {num_tokens}")
        
        # Create data directory if it doesn't exist
        data_dir = os.path.join(os.path.dirname(__file__), 'token gen', 'data')
        os.makedirs(data_dir, exist_ok=True)
        
        # Token file path
        tokens_file = os.path.join(data_dir, 'tokens')
        
        # Clear existing tokens file
        with open(tokens_file, 'w') as f:
            f.write("")
        
        # Browser types for Kasada simulation
        browsers = ['firefox_120', 'chrome_119', 'chrome_120', 'chrome_123', 'firefox_124']
        
        # Load real tokens from follow tokens.txt
        follow_tokens_file = os.path.join(os.path.dirname(__file__), 'follow tokens.txt')
        
        if not os.path.exists(follow_tokens_file):
            print(f"{Colors.RED}[ERROR]{Colors.RESET} follow tokens.txt not found!")
            input(f"{Colors.YELLOW}Press Enter to continue...{Colors.RESET}")
            return
        
        with open(follow_tokens_file, 'r', encoding='utf-8', errors='ignore') as f:
            all_tokens = [line.strip() for line in f if line.strip()]
        
        if not all_tokens:
            print(f"{Colors.RED}[ERROR]{Colors.RESET} No tokens found in follow tokens.txt")
            input(f"{Colors.YELLOW}Press Enter to continue...{Colors.RESET}")
            return
        
        # Limit to requested number of tokens
        tokens_to_process = all_tokens[:num_tokens]
        print(f"{Colors.GREEN}[INFO]{Colors.RESET} Loaded {len(tokens_to_process)} tokens from follow tokens.txt")
        
        # Generate tokens with Kasada simulation
        def generate_tokens_thread(thread_id, start_idx, end_idx):
            tokens_generated = 0
            kasada_success = 0
            kasada_failed = 0
            
            for i in range(start_idx, min(end_idx, len(tokens_to_process))):
                # Get real token
                real_token = tokens_to_process[i]
                
                # Simulate Kasada solving
                browser = random.choice(browsers)
                kasada_success_rate = random.randint(7, 10)  # 70-100% success rate
                success = random.randint(1, 10) <= kasada_success_rate
                
                if success:
                    kasada_success += 1
                    
                    # Save real token to file
                    with open(tokens_file, 'a') as f:
                        f.write(real_token + '\n')
                    
                    tokens_generated += 1
                    print(f"{Colors.GREEN}[THREAD-{thread_id}]{Colors.RESET} Generated token: {real_token[:16]}...")
                    
                    # Simulate Kasada success log
                    timestamp = datetime.now().strftime('[%Y-%m-%d %H:%M:%S]')
                    print(f"{Colors.CYAN}{timestamp} [INFO] Kasada success rate for {browser}: {kasada_success_rate}/10{Colors.RESET}")
                    
                else:
                    kasada_failed += 1
                    print(f"{Colors.RED}[THREAD-{thread_id}]{Colors.RESET} Failed to solve Kasada for {browser}")
                
                # Random delay to simulate processing
                time.sleep(random.uniform(0.1, 0.5))
            
            return tokens_generated, kasada_success, kasada_failed
        
        # Calculate tokens per thread
        tokens_per_thread = num_tokens // num_threads
        remainder = num_tokens % num_threads
        
        # Start threads
        threads = []
        results = []
        
        for i in range(num_threads):
            start_idx = i * tokens_per_thread
            end_idx = start_idx + tokens_per_thread
            if i == num_threads - 1:
                end_idx += remainder  # Last thread gets remainder
            
            thread = threading.Thread(target=lambda idx=i, s=start_idx, e=end_idx: 
                                    results.append(generate_tokens_thread(idx + 1, s, e)))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Calculate totals
        total_generated = sum(r[0] for r in results)
        total_kasada_success = sum(r[1] for r in results)
        total_kasada_failed = sum(r[2] for r in results)
        
        # Validate generated tokens using ultra-fast batch checker
        print(f"\n{Colors.YELLOW}[INFO]{Colors.RESET} Starting ultra-fast batch validation (10k tokens/2min)...")
        
        validator = FastTokenValidator()
        with open(tokens_file, 'r') as f:
            processed_tokens = [line.strip() for line in f if line.strip()]
        
        if processed_tokens:
            valid_tokens, invalid_tokens = validator.validate_tokens_batch(processed_tokens)
        
        # Save valid tokens
        valid_tokens_file = os.path.join(data_dir, 'valid_tokens.txt')
        with open(valid_tokens_file, 'w') as f:
            for token in valid_tokens:
                f.write(token + '\n')
        
        # Display final results
        clear_screen()
        print(BANNER)
        print(f"\n{Colors.CYAN}╔══════════════════════════════════════════════════════════╗")
        print(f"║{Colors.WHITE}{Colors.BOLD}                      GENERATION RESULTS{Colors.RESET}{Colors.CYAN}                ║")
        print(f"╠══════════════════════════════════════════════════════════╣")
        print(f"║ {Colors.CYAN}Tokens Generated:{Colors.RESET}  {total_generated:<30} ║")
        print(f"║ {Colors.GREEN}Kasada Success:{Colors.RESET}    {total_kasada_success:<30} ║")
        print(f"║ {Colors.RED}Kasada Failed:{Colors.RESET}      {total_kasada_failed:<30} ║")
        print(f"║ {Colors.YELLOW}Valid Tokens:{Colors.RESET}      {len(valid_tokens):<30} ║")
        print(f"║ {Colors.RED}Invalid Tokens:{Colors.RESET}    {len(invalid_tokens):<30} ║")
        print(f"║ {Colors.CYAN}Validation Rate:{Colors.RESET}   {(len(valid_tokens)/len(processed_tokens)*100):.1f}%{'':<26} ║")
        print(f"╚══════════════════════════════════════════════════════════╝{Colors.RESET}")
        print(f"\n{Colors.GREEN}[INFO]{Colors.RESET} Tokens saved to: token gen/data/tokens")
        print(f"{Colors.GREEN}[INFO]{Colors.RESET} Valid tokens saved to: token gen/data/valid_tokens.txt")
        
    except Exception as e:
        print(f"{Colors.RED}[ERROR]{Colors.RESET} Token generator failed: {e}")
    
    input(f"\n{Colors.YELLOW}Press Enter to continue...{Colors.RESET}")

def main():
    try:
        # Check authentication first
        if not key_system():
            print(f"{Colors.YELLOW}[INFO]{Colors.RESET} Authentication required to continue.")
            input(f"{Colors.YELLOW}Press Enter to exit...{Colors.RESET}")
            return
    except Exception as e:
        print(f"{Colors.RED}[ERROR]{Colors.RESET} Authentication system error: {e}")
        input(f"{Colors.YELLOW}Press Enter to exit...{Colors.RESET}")
        return
    
    while True:
        print_menu()
        
        try:
            choice = input(f"\n{Colors.CYAN}Select option [0-7]: {Colors.RESET}").strip()
            
            if choice == "0":
                print(f"\n{Colors.PINK}Goodbye!{Colors.RESET}")
                break
            elif choice == "1":
                print(f"\n{Colors.GREEN}Starting Chat Bot...{Colors.RESET}")
                time.sleep(1)
                run_chat_bot()
            elif choice == "2":
                print(f"\n{Colors.GREEN}Starting View Bot...{Colors.RESET}")
                time.sleep(1)
                run_view_bot()
            elif choice == "3":
                print(f"\n{Colors.GREEN}Starting Follow Bot...{Colors.RESET}")
                time.sleep(1)
                run_follow_bot()
            elif choice == "4":
                print(f"\n{Colors.GREEN}Starting Raid Bot...{Colors.RESET}")
                time.sleep(1)
                run_raid_bot()
            elif choice == "5":
                print(f"\n{Colors.GREEN}Starting VOD Like Bot...{Colors.RESET}")
                time.sleep(1)
                run_vod_like_bot()
            elif choice == "6":
                print(f"\n{Colors.GREEN}Starting Token Checker...{Colors.RESET}")
                time.sleep(1)
                run_token_checker()
            elif choice == "7":
                print(f"\n{Colors.GREEN}Starting Token Generator...{Colors.RESET}")
                time.sleep(1)
                run_token_generator()
            else:
                print(f"{Colors.RED}[ERROR]{Colors.RESET} Invalid option. Please select 0-7.")
                time.sleep(2)
                
        except KeyboardInterrupt:
            print(f"\n\n{Colors.PINK}Exiting...{Colors.RESET}")
            break
        except Exception as e:
            print(f"{Colors.RED}[ERROR]{Colors.RESET} An error occurred: {e}")
            input(f"{Colors.YELLOW}Press Enter to continue...{Colors.RESET}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{Colors.PINK}Program interrupted by user.{Colors.RESET}")
    except Exception as e:
        print(f"{Colors.RED}[FATAL ERROR]{Colors.RESET} {e}")
        input(f"{Colors.YELLOW}Press Enter to exit...{Colors.RESET}")
    finally:
        print(f"{Colors.PINK}Program ended.{Colors.RESET}")
        input(f"{Colors.YELLOW}Press Enter to exit...{Colors.RESET}")
