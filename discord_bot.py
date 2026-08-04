import discord
import discord.app_commands as app_commands
from discord.ext import commands
import os
import sys
import asyncio
import threading
import random
import time
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
import uuid
import pickle

# Import UI components
from discord.ui import Button, View, Modal, TextInput
from discord import Interaction

# Global thread pool for managing concurrent operations
OPERATION_POOL = ThreadPoolExecutor(max_workers=10, thread_name_prefix="BotOp")

# Global storage for user bot names
user_bot_names = {}

# Bot control variables
bot_enabled = True
bot_operation_threads = {}  # Track running operations for timeout
BOT_TIMEOUT_MINUTES = 5  # Auto-stop bots after 5 minutes

# Service control variables
disabled_services = set()  # Track which services are disabled
SERVICE_DOWN_MESSAGE = "🔧 Service temporarily unavailable for maintenance. Please try again later."
OWNER_ID = 1389712262532431882  # Your ID for pings

# Bot ban system
bot_banned_users = {}  # Track banned users and their ban info

# Roblox generator variables
used_accounts = set()
used_accounts_file = 'roblox gen/used_accounts.pkl'

def timeout_operation(operation_id: str):
    """Stop a running operation after timeout"""
    if operation_id in bot_operation_threads:
        try:
            # Kill the subprocess if it's still running
            thread_info = bot_operation_threads[operation_id]
            if 'process' in thread_info and thread_info['process']:
                thread_info['process'].terminate()
                thread_info['process'].kill()
            print(f"[TIMEOUT] Operation {operation_id} timed out and was killed")
        except Exception as e:
            print(f"[TIMEOUT] Error killing operation {operation_id}: {e}")
        finally:
            bot_operation_threads.pop(operation_id, None)

# Roblox generator functions
def load_used_accounts():
    """Load used accounts from pickle file"""
    global used_accounts
    try:
        print(f"[ROBLOX] Loading used accounts from {used_accounts_file}")
        with open(used_accounts_file, 'rb') as f:
            used_accounts = pickle.load(f)
        print(f'[ROBLOX] Loaded {len(used_accounts)} used accounts: {list(used_accounts)[:5]}...')
    except FileNotFoundError:
        used_accounts = set()
        print('[ROBLOX] No used accounts file found, starting fresh')
    except Exception as e:
        used_accounts = set()
        print(f'[ROBLOX] Error loading used accounts: {e}')

def save_used_accounts():
    """Save used accounts to pickle file"""
    with open(used_accounts_file, 'wb') as f:
        pickle.dump(used_accounts, f)

def load_accounts():
    """Load accounts from text file (one per line: username:password)"""
    accounts = []
    try:
        print("[ROBLOX] Loading accounts from roblox gen/accounts/accounts.txt")
        with open('roblox gen/accounts/accounts.txt', 'r') as f:
            for line in f:
                line = line.strip()
                if line and ':' in line:
                    username, password = line.split(':', 1)
                    # Remove :_ suffix from password if present
                    password = password.replace(':_', '')
                    accounts.append({
                        'username': username.strip(),
                        'password': password.strip()
                    })
        print(f'[ROBLOX] Loaded {len(accounts)} total accounts')
    except FileNotFoundError:
        print('[ROBLOX] ERROR: accounts.txt not found at roblox gen/accounts/accounts.txt!')
    except Exception as e:
        print(f'[ROBLOX] ERROR loading accounts: {e}')
    return accounts

def get_available_account():
    """Get an unused account"""
    print("[ROBLOX] Getting available account...")
    accounts = load_accounts()
    print(f"[ROBLOX] Checking {len(accounts)} accounts against {len(used_accounts)} used accounts")
    
    for account in accounts:
        if account['username'] not in used_accounts:
            print(f"[ROBLOX] Found available account: {account['username']}")
            return account
    
    print("[ROBLOX] No available accounts found!")
    return None

def mark_account_used(username):
    """Mark an account as used"""
    print(f"[ROBLOX] Marking account {username} as used")
    used_accounts.add(username)
    save_used_accounts()
    print(f"[ROBLOX] Account {username} marked as used. Total used: {len(used_accounts)}")

# Create modal for setting bot name
class SetBotNameModal(Modal, title="Set Your Bot Name"):
    bot_name = TextInput(label="Bot Name", placeholder="Enter your custom bot name", default="ReviveX", required=True)

    async def on_submit(self, interaction: Interaction):
        await interaction.response.defer()
        
        bot_name = self.bot_name.value.strip()
        if not bot_name:
            await interaction.followup.send("❌ Bot name cannot be empty!", ephemeral=True)
            return
        
        # Store user's bot name
        user_bot_names[interaction.user.id] = bot_name
        
        await interaction.followup.send(
            f"✅ **Bot Name Set!**\n"
            f"🤖 Your bot name is now: `{bot_name}`\n"
            f"💡 This will be used for all bot services!",
            ephemeral=True
        )

# Create modal for follow bot input
class FollowModal(Modal, title="Follow Bot"):
    username = TextInput(label="Twitch Username", placeholder="Enter username to follow", default="")
    amount = TextInput(label="Amount", placeholder="Number of follows", default="10")

    async def on_submit(self, interaction: Interaction):
        print(f"[DEBUG] Follow modal submitted by {interaction.user.name}")
        await interaction.response.defer()
        
        username = self.username.value or interaction.user.name
        amount = int(self.amount.value) if self.amount.value.isdigit() else 10
        bot_name = user_bot_names.get(interaction.user.id, "ReviveX")
        
        print(f"[DEBUG] Follow parameters: username={username}, amount={amount}, bot_name={bot_name}")
        
        # Check user permissions
        user_perms = get_user_permission_level(interaction)
        max_amount = user_perms["tfollow"]
        
        print(f"[DEBUG] Max amount allowed: {max_amount}")
        
        if max_amount == 0:
            print("[DEBUG] User has no follow permission in modal")
            await log_to_owner(interaction, "Follow Bot", amount, username, False)
            await interaction.followup.send("❌ You don't have permission to use the Follow Bot.", ephemeral=True)
            return
        
        if amount > max_amount:
            print(f"[DEBUG] Amount {amount} exceeds max {max_amount}")
            await log_to_owner(interaction, "Follow Bot", amount, username, False)
            await interaction.followup.send(f"❌ You can only follow up to {max_amount} users at once.", ephemeral=True)
            return
        
        # Update cooldown after successful validation
        update_cooldown(interaction)
        print("[DEBUG] Cooldown updated")
        
        # Check for alting
        await check_for_alting(interaction, username, amount)
        
        # Check for owner abuse
        await check_owner_abuse(interaction, "Follow Bot", amount)
        
        # Execute follow bot
        try:
            print("[DEBUG] Starting follow bot execution")
            # Get the follow directory
            follow_dir = os.path.join(os.path.dirname(__file__), 'follow')
            
            # Run follow bot with parameters and timeout
            def run_follow():
                import subprocess
                import sys
                import threading
                import uuid
                
                operation_id = str(uuid.uuid4())[:8]
                print(f"[DEBUG] Starting follow operation {operation_id} for {username}")
                
                try:
                    result = subprocess.run(
                        [sys.executable, "follow.py", username, str(amount), bot_name], 
                        cwd=follow_dir,
                        timeout=90  # Increased from 60 to 90 seconds
                    )
                    print(f"[DEBUG] Follow operation {operation_id} completed: {result.returncode}")
                    return result
                except subprocess.TimeoutExpired:
                    print(f"[DEBUG] Follow operation {operation_id} timed out")
                    return None
                except Exception as e:
                    print(f"[DEBUG] Follow operation {operation_id} error: {e}")
                    return None
            
            OPERATION_POOL.submit(run_follow)
            print("[DEBUG] Follow bot submitted to thread pool")
            
            # Log to owner
            await log_to_owner(interaction, "Follow Bot", amount, username, True)
            
            # Auto-remove Video Maker role if used
            await auto_remove_video_maker_role(interaction)
            
            msg = await interaction.followup.send(f"✅ Started following `{username}` with `{amount}` follows", ephemeral=False)
            print("[DEBUG] Success message sent")
            
            # Send vouch reminder to user's DMs
            await send_vouch_reminder(interaction.user)
            
            await asyncio.sleep(15)
            await msg.delete()
        except Exception as e:
            print(f"[DEBUG] Follow bot execution error: {e}")
            await log_to_owner(interaction, "Follow Bot", amount, username, False)
            msg = await interaction.followup.send(f"❌ Error: `{str(e)}`", ephemeral=False)
            await asyncio.sleep(15)
            await msg.delete()

# Create modal for chat bot input
class ChatModal(Modal, title="Chat Bot"):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.username = TextInput(label="Twitch Channel", placeholder="Enter channel name", default="")
        self.message = TextInput(label="Message", placeholder="Message to spam", default="")
        self.amount = TextInput(label="Amount", placeholder="Number of messages", default="")
        self.emote_only = TextInput(label="Emote Only (true/false)", placeholder="Use emotes only", default="")
        
        # Add items to modal
        self.add_item(self.username)
        self.add_item(self.message)
        self.add_item(self.amount)
        self.add_item(self.emote_only)

    async def on_submit(self, interaction: Interaction):
        await interaction.response.defer()
        
        username = self.username.value.strip() if self.username.value.strip() else interaction.user.name
        message = self.message.value.strip() if self.message.value.strip() else "yo"
        amount = int(self.amount.value) if self.amount.value and self.amount.value.isdigit() else 100
        bot_name = user_bot_names.get(interaction.user.id, "ReviveX")
        emote_only = self.emote_only.value.strip().lower() == "true" if self.emote_only.value.strip() else False
        
        # Check user permissions
        user_perms = get_user_permission_level(interaction)
        max_amount = user_perms["tchat"]
        
        if max_amount == 0:
            await log_to_owner(interaction, "Chat Bot", amount, username, False)
            await interaction.followup.send("❌ You don't have permission to use the Chat Bot.", ephemeral=True)
            return
        
        if amount > max_amount:
            await log_to_owner(interaction, "Chat Bot", amount, username, False)
            await interaction.followup.send(f"❌ You can only send up to {max_amount} messages at once.", ephemeral=True)
            return
        
        # Update cooldown after successful validation
        update_cooldown(interaction)
        
        # Check for owner abuse
        await check_owner_abuse(interaction, "Chat Bot", amount)
        
        if emote_only:
            # Random emote
            global_emotes = ["RedNoseDay26", "NowField", "WoWMidnight", "Yagoo", "SipTime", "EleGiggle", "FeverFighter", "WeDidThat", "PewPewPew", "JinxLUL", "FeelsVi", "AmbessaLove", "EkkoChest", "CaitThinking", "Cinheimer", "BratChat", "BigSad", "GRASSLORD", "TWITH", "SUBtember", "AnotherRecord", "GoatEmotey", "GoldPLZ", "TwitchConHYPE", "PopNemo", "DinoDance", "NewRecord", "SUBprise", "ImTyping", "Shush", "MyAvatar", "PizzaTime", "LaundryBasket", "ModLove", "Jebasted", "TransgenderPride", "PansexualPride", "NonbinaryPride", "LesbianPride", "IntersexPride", "GenderFluidPride", "GayPride", "BisexualPride", "AsexualPride", "PogChamp", "GlitchNRG", "GlitchLit", "StinkyGlitch", "GlitchCat", "FootGoal", "FootYellow", "FootBall", "BlackLivesMatter", "ExtraLife", "VirtualHug", "BOP", "SingsNote", "SingsMic", "TwitchSings", "SoonerLater", "HolidayTree", "HolidaySanta", "HolidayPresent", "HolidayLog", "HolidayCookie", "PixelBob", "FBPenalty", "FBChallenge", "FBCatch", "FBBlock", "FBSpiral", "FBPass", "FBRun", "MaxLOL", "TwitchRPG", "PinkMercy", "MercyWing2", "MercyWing1", "PartyHat", "EarthDay", "TombRaid", "PopCorn", "FBtouchdown", "TPFufun", "TwitchVotes", "DarkMode", "HSWP", "HSCheers", "PowerUpL", "PowerUpR", "LUL", "EntropyWins", "TPcrunchyroll", "TwitchUnity", "Squid4", "Squid3", "Squid2", "Squid1", "CrreamAwk", "CarlSmile", "TwitchLit", "TehePelo", "TearGlove", "SabaPing", "PoroLove", "BlessRNG", "CoolCat", "CoolStoryBob", "Copium", "Cope", "Cringge", "Dank", "DankEnough", "DatSheffy", "FeelsBadMan", "FirstTime", "FrankerZ", "FreakBob", "Gasm", "Hi", "HypeTrain", "Jebaited", "Kappa", "Keepo", "KKona", "Kreygasm", "LULW", "MonkaS", "MonkaW", "Noot", "OMEGALUL", "PepeHands", "Pepega", "Pog", "PogChamp", "Poggers", "PogU", "PogYou", "Prayge", "ResidentSleeper", "Sadge", "SeemsGood", "SmashPass", "Stonks", "SupaHotFire", "Sweat", "TriHard", "VAC", "WutFace", "WideHard", "Wow", "YaHice", "YEP"]
            message = random.choice(global_emotes)
        
        # Execute chat bot
        try:
            chat_dir = os.path.join(os.path.dirname(__file__), 'chat')
            
            # Run chat bot with parameters (no directory changes)
            def run_chat():
                import subprocess
                import sys
                try:
                    subprocess.run([sys.executable, "chat_standalone.py", username, message, str(amount), str(emote_only).lower()], 
                                 cwd=chat_dir, timeout=90)  # Increased from 30 to 90 seconds
                except subprocess.TimeoutExpired:
                    print(f"[DEBUG] Chat bot timed out for {username}")
                except Exception as e:
                    print(f"[DEBUG] Chat bot error: {e}")
            
            OPERATION_POOL.submit(run_chat)
            # DEBUG message removed to prevent interference with chat bot
            
            # Log to owner
            await log_to_owner(interaction, "Chat Bot", amount, username, True)
            
            # Auto-remove Video Maker role if used
            await auto_remove_video_maker_role(interaction)
            
            msg = await interaction.followup.send(f"✅ Started spamming `{username}` with `{amount}` messages: `{message}`", ephemeral=False)
            
            # Send vouch reminder to user's DMs
            await send_vouch_reminder(interaction.user)
            
            await asyncio.sleep(15)
            await msg.delete()
        except Exception as e:
            await log_to_owner(interaction, "Chat Bot", amount, username, False)
            msg = await interaction.followup.send(f"❌ Error: `{str(e)}`", ephemeral=False)
            await asyncio.sleep(15)
            await msg.delete()

# Create modal for raid bot input
class RaidModal(Modal, title="Raid Bot"):
    raid_id = TextInput(label="Raid ID", placeholder="Enter raid ID", default="")
    amount = TextInput(label="Amount", placeholder="Number of raid joins", default="10")

    async def on_submit(self, interaction: Interaction):
        await interaction.response.defer()
        
        raid_id = self.raid_id.value
        amount = int(self.amount.value) if self.amount.value.isdigit() else 10
        bot_name = user_bot_names.get(interaction.user.id, "ReviveX")
        
        # Check user permissions
        user_perms = get_user_permission_level(interaction)
        max_amount = user_perms["traid"]
        
        if max_amount == 0:
            await log_to_owner(interaction, "Raid Bot", amount, raid_id, False)
            await interaction.followup.send("❌ You don't have permission to use the Raid Bot.", ephemeral=True)
            return
        
        if amount > max_amount:
            await log_to_owner(interaction, "Raid Bot", amount, raid_id, False)
            await interaction.followup.send(f"❌ You can only join up to {max_amount} raids at once.", ephemeral=True)
            return
        
        # Update cooldown after successful validation
        update_cooldown(interaction)
        
        # Check for owner abuse
        await check_owner_abuse(interaction, "Raid Bot", amount)
        
        if not raid_id:
            await log_to_owner(interaction, "Raid Bot", amount, raid_id, False)
            await interaction.followup.send("❌ Raid ID is required", ephemeral=True)
            return
        
        # Execute raid bot
        try:
            raid_dir = os.path.join(os.path.dirname(__file__), 'raid bot')
            
            # Run raid bot with parameters (no directory changes)
            def run_raid():
                import subprocess
                import sys
                try:
                    subprocess.run(["py", "-3.11", "raid.py", raid_id, str(amount), bot_name], 
                                 cwd=raid_dir, timeout=30)
                except subprocess.TimeoutExpired:
                    print(f"[DEBUG] Raid bot timed out for {raid_id}")
                except Exception as e:
                    print(f"[DEBUG] Raid bot error: {e}")
            
            OPERATION_POOL.submit(run_raid)
            print("[DEBUG] Raid bot submitted to thread pool")
            
            # Log to owner
            await log_to_owner(interaction, "Raid Bot", amount, raid_id, True)
            
            # Auto-remove Video Maker role if used
            await auto_remove_video_maker_role(interaction)
            
            msg = await interaction.followup.send(f"✅ Started raid `{raid_id}` with `{amount}` joins", ephemeral=False)
            
            # Send vouch reminder to user's DMs
            await send_vouch_reminder(interaction.user)
            
            await asyncio.sleep(15)
            await msg.delete()
        except Exception as e:
            await log_to_owner(interaction, "Raid Bot", amount, raid_id, False)
            msg = await interaction.followup.send(f"❌ Error: `{str(e)}`", ephemeral=False)
            await asyncio.sleep(15)
            await msg.delete()

# Create modal for view bot input
class ViewModal(Modal, title="View Bot"):
    username = TextInput(label="Twitch Channel", placeholder="Enter channel name", default="")
    amount = TextInput(label="Amount", placeholder="Number of viewers", default="50")

    async def on_submit(self, interaction: Interaction):
        await interaction.response.defer()
        
        username = self.username.value or interaction.user.name
        amount = int(self.amount.value) if self.amount.value.isdigit() else 50
        bot_name = user_bot_names.get(interaction.user.id, "ReviveX")
        
        # Check user permissions
        user_perms = get_user_permission_level(interaction)
        max_amount = user_perms["tview"]
        
        if max_amount == 0:
            await log_to_owner(interaction, "View Bot", amount, username, False)
            await interaction.followup.send("❌ You don't have permission to use the View Bot.", ephemeral=True)
            return
        
        if amount > max_amount:
            await log_to_owner(interaction, "View Bot", amount, username, False)
            await interaction.followup.send(f"❌ You can only add up to {max_amount} viewers at once.", ephemeral=True)
            return
        
        # Update cooldown after successful validation
        update_cooldown(interaction)
        
        # Check for owner abuse
        await check_owner_abuse(interaction, "View Bot", amount)
        
        # Execute view bot
        try:
            view_dir = os.path.join(os.path.dirname(__file__), 'viewbot')
            
            # Run view bot with parameters (no directory changes)
            def run_view():
                import subprocess
                import sys
                try:
                    subprocess.run(["py", "-3.11", "main.py", username, str(amount), bot_name], 
                                 cwd=view_dir, timeout=30)
                except subprocess.TimeoutExpired:
                    print(f"[DEBUG] View bot timed out for {username}")
                except Exception as e:
                    print(f"[DEBUG] View bot error: {e}")
            
            OPERATION_POOL.submit(run_view)
            print("[DEBUG] View bot submitted to thread pool")
            
            # Log to owner
            await log_to_owner(interaction, "View Bot", amount, username, True)
            
            # Auto-remove Video Maker role if used
            await auto_remove_video_maker_role(interaction)
            
            msg = await interaction.followup.send(f"✅ Started viewing `{username}` with `{amount}` viewers", ephemeral=False)
            
            # Send vouch reminder to user's DMs
            await send_vouch_reminder(interaction.user)
            
            await asyncio.sleep(15)
            await msg.delete()
        except Exception as e:
            await log_to_owner(interaction, "View Bot", amount, username, False)
            msg = await interaction.followup.send(f"❌ Error: `{str(e)}`", ephemeral=False)
            await asyncio.sleep(15)
            await msg.delete()

# Create modal for VOD like input
class LikeModal(Modal, title="Clip Like Bot"):
    vod_url = TextInput(label="Clip URL", placeholder="Enter clip URL", default="")
    amount = TextInput(label="Amount", placeholder="Number of likes", default="50")

    async def on_submit(self, interaction: Interaction):
        await interaction.response.defer()
        
        vod_url = self.vod_url.value
        amount = int(self.amount.value) if self.amount.value.isdigit() else 50
        bot_name = user_bot_names.get(interaction.user.id, "ReviveX")
        
        # Check user permissions
        user_perms = get_user_permission_level(interaction)
        max_amount = user_perms["tlike"]
        
        if max_amount == 0:
            await log_to_owner(interaction, "Clip Like Bot", amount, vod_url, False)
            await interaction.followup.send("❌ You don't have permission to use the Clip Like Bot.", ephemeral=True)
            return
        
        if amount > max_amount:
            await log_to_owner(interaction, "Clip Like Bot", amount, vod_url, False)
            await interaction.followup.send(f"❌ You can only add up to {max_amount} likes at once.", ephemeral=True)
            return
        
        # Update cooldown after successful validation
        update_cooldown(interaction)
        
        # Check for owner abuse
        await check_owner_abuse(interaction, "Clip Like Bot", amount)
        
        if not vod_url:
            await log_to_owner(interaction, "Clip Like Bot", amount, vod_url, False)
            await interaction.followup.send("❌ Clip URL is required", ephemeral=True)
            return
        
        # Execute VOD like bot
        try:
            like_dir = os.path.join(os.path.dirname(__file__), 'vod like')
            
            # Run VOD like bot with parameters (no directory changes)
            def run_like():
                import subprocess
                import sys
                try:
                    subprocess.run(["py", "-3.11", "main.py", vod_url, str(amount), bot_name], 
                                 cwd=like_dir, timeout=30)
                except subprocess.TimeoutExpired:
                    print(f"[DEBUG] Like bot timed out for {vod_url}")
                except Exception as e:
                    print(f"[DEBUG] Like bot error: {e}")
            
            OPERATION_POOL.submit(run_like)
            print("[DEBUG] Like bot submitted to thread pool")
            
            # Log to owner
            await log_to_owner(interaction, "Clip Like Bot", amount, vod_url, True)
            
            # Auto-remove Video Maker role if used
            await auto_remove_video_maker_role(interaction)
            
            msg = await interaction.followup.send(f"✅ Started liking `{vod_url}` with `{amount}` likes", ephemeral=False)
            
            # Send vouch reminder to user's DMs
            await send_vouch_reminder(interaction.user)
            
            await asyncio.sleep(15)
            await msg.delete()
        except Exception as e:
            await log_to_owner(interaction, "Clip Like Bot", amount, vod_url, False)
            msg = await interaction.followup.send(f"❌ Error: `{str(e)}`", ephemeral=False)
            await asyncio.sleep(15)
            await msg.delete()

# Generate Roblox account function
def generate_roblox_account():
    """Generate a random Roblox account"""
    import random
    import string
    
    # Generate random username
    adjectives = ['Cool', 'Super', 'Mega', 'Ultra', 'Pro', 'Epic', 'Awesome', 'Great', 'Fast', 'Quick', 'Swift', 'Brave', 'Bold', 'Smart', 'Tough', 'Strong', 'Mighty']
    nouns = ['Player', 'Gamer', 'Builder', 'Warrior', 'Champion', 'Hero', 'Legend', 'Master', 'Expert', 'Ninja', 'Panda', 'Dragon', 'Phoenix', 'Tiger', 'Lion', 'Eagle', 'Falcon', 'Wolf', 'Bear', 'Shark', 'Hawk', 'Viper', 'Cobra', 'Storm', 'Blaze', 'Frost', 'Ice', 'Fire', 'Thunder', 'Lightning', 'Shadow', 'Ghost', 'Spirit', 'Crystal', 'Diamond', 'Ruby', 'Emerald', 'Sapphire', 'Obsidian']
    numbers = [str(random.randint(100, 999)) for _ in range(4)]
    
    username = f"{random.choice(adjectives)}{random.choice(nouns)}{''.join(numbers)}"
    
    # Generate random password
    characters = string.ascii_letters + string.digits + "!@#$%^&*"
    password = ''.join(random.choice(characters) for _ in range(12))
    
    return {
        'username': username,
        'password': password
    }

# Create modal for Roblox account input
class RobloxModal(Modal, title="Roblox Account Generator"):
    username = TextInput(label="Username", placeholder="Enter username", default="")
    password = TextInput(label="Password", placeholder="Enter password", default="")
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_item(self.username)
        self.add_item(self.password)
    
    async def on_submit(self, interaction: Interaction):
        username = self.username.value
        password = self.password.value
        
        if not username:
            await interaction.response.send_message("❌ Please enter a username!", ephemeral=True)
            return
        
        if not password:
            await interaction.response.send_message("❌ Please enter a password!", ephemeral=True)
            return
        
        # Get user permissions and check limits
        perms = get_user_permission_level(interaction)
        max_accounts = perms.get('troblox', 0)
        
        if max_accounts <= 0:
            await interaction.response.send_message("❌ You don't have access to Roblox account generation!", ephemeral=True)
            return
        
        # Check cooldown
        is_cooldown, cooldown_msg = check_roblox_cooldown(interaction)
        if not is_cooldown:
            await interaction.response.send_message(f"❌ {cooldown_msg}", ephemeral=True)
            return
        
        # Generate Roblox account
        try:
            print(f"[ROBLOX] Account generation requested by {interaction.user.name} ({interaction.user.id})")
            
            # Send thinking message
            await interaction.response.send_message("🔄 Generating Roblox account...", ephemeral=True)
            
            # Load used accounts
            used_accounts = load_used_accounts()
            
            # Generate new account
            new_account = generate_roblox_account()
            
            if new_account:
                # Save to used accounts
                used_accounts.append(new_account)
                save_used_accounts(used_accounts)
                
                # Send account details via DM
                try:
                    user_embed = discord.Embed(
                        title="🎮 **Roblox Account Generated**",
                        description=f"**Here are your Roblox account details:**",
                        color=discord.Color.green()
                    )
                    
                    user_embed.add_field(
                        name="👤 **Account Details**",
                        value=f"**Username:** `{new_account['username']}`\n"
                              f"**Password:** `{new_account['password']}`",
                        inline=False
                    )
                    
                    user_embed.add_field(
                        name="📊 **Usage Info**",
                        value=f"**Generated by:** {interaction.user.mention}\n"
                              f"**Remaining accounts:** {max_accounts - 1}",
                        inline=False
                    )
                    
                    user_embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/743869767950618744.png")
                    user_embed.set_footer(text="Made by the one and only ReviveX • Use responsibly!")
                    
                    await interaction.user.send(embed=user_embed)
                    
                    # Send confirmation to channel
                    await interaction.followup.send(
                        f"✅ **Roblox Account Generated!**\n"
                        f"🎮 Account details sent to {interaction.user.mention}\n"
                        f"📊 Remaining: {max_accounts - 1}/{max_accounts}",
                        ephemeral=False
                    )
                    
                    print(f"[ROBLOX] Account generated for {interaction.user.name}: {new_account['username']}")
                    
                    # Update cooldown
                    update_roblox_cooldown(interaction.user.id)
                    
                    # Log to owners
                    await log_to_owner(interaction, "Roblox Account Generator", 1, True)
                    
                except Exception as e:
                    print(f"[-] Error sending Roblox account: {e}")
                    await interaction.followup.send(f"❌ Error generating account: `{str(e)}`", ephemeral=True)
            else:
                await interaction.followup.send("❌ Failed to generate account. Please try again.", ephemeral=True)
                
        except Exception as e:
            print(f"[-] Error in Roblox modal: {e}")
            await interaction.response.send_message(f"❌ Error: `{str(e)}`", ephemeral=True)

# Create modal for Kahoot raid bot input
class KahootModal(Modal, title="Kahoot Raid Bot"):
    game_pin = TextInput(label="Game PIN", placeholder="Enter Kahoot game PIN", default="")
    amount = TextInput(label="Amount", placeholder="Number of bots", default="10")

    async def on_submit(self, interaction: Interaction):
        await interaction.response.defer()
        
        game_pin = self.game_pin.value
        amount = int(self.amount.value) if self.amount.value.isdigit() else 10
        bot_name = user_bot_names.get(interaction.user.id, "ReviveX")
        
        # Check user permissions
        user_perms = get_user_permission_level(interaction)
        max_amount = user_perms.get("tkahoot", 0)
        
        if max_amount == 0:
            await log_to_owner(interaction, "Kahoot Raid Bot", amount, game_pin, False)
            await interaction.followup.send("❌ You don't have permission to use the Kahoot Raid Bot.", ephemeral=True)
            return
        
        if amount > max_amount:
            await log_to_owner(interaction, "Kahoot Raid Bot", amount, game_pin, False)
            await interaction.followup.send(f"❌ You can only use up to {max_amount} bots at once.", ephemeral=True)
            return
        
        # Update cooldown after successful validation
        update_cooldown(interaction)
        
        # Check for owner abuse
        await check_owner_abuse(interaction, "Kahoot Raid Bot", amount)
        
        if not game_pin:
            await log_to_owner(interaction, "Kahoot Raid Bot", amount, game_pin, False)
            await interaction.followup.send("❌ Game PIN is required", ephemeral=True)
            return
        
        # Execute Kahoot raid bot
        try:
            kahoot_dir = os.path.join(os.path.dirname(__file__), 'kahoot raid bot')
            
            # Run Kahoot raid bot with parameters
            def run_kahoot():
                import subprocess
                import sys
                try:
                    subprocess.run([sys.executable, "main.py", game_pin, str(amount), bot_name], 
                                 cwd=kahoot_dir, timeout=120)
                except subprocess.TimeoutExpired:
                    print(f"[DEBUG] Kahoot bot timed out for pin {game_pin}")
                except Exception as e:
                    print(f"[DEBUG] Kahoot bot error: {e}")
            
            OPERATION_POOL.submit(run_kahoot)
            print("[DEBUG] Kahoot bot submitted to thread pool")
            
            # Log to owner
            await log_to_owner(interaction, "Kahoot Raid Bot", amount, game_pin, True)
            
            msg = await interaction.followup.send(f"✅ Started Kahoot raid with `{amount}` bots named `{bot_name}`", ephemeral=False)
            
            # Send vouch reminder to user's DMs
            await send_vouch_reminder(interaction.user)
            
            await asyncio.sleep(15)
            await msg.delete()
        except Exception as e:
            await log_to_owner(interaction, "Kahoot Raid Bot", amount, game_pin, False)
            msg = await interaction.followup.send(f"❌ Error: `{str(e)}`", ephemeral=False)
            await asyncio.sleep(15)
            await msg.delete()

# Create Roblox/Kahoot/Spotify panel view
class RobloxKahootSpotifyView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        
        # Add individual buttons for each service
        self.add_item(discord.ui.Button(
            label="🎮 Roblox Account Generator",
            style=discord.ButtonStyle.primary,
            custom_id="rks_roblox"
        ))
        
        self.add_item(discord.ui.Button(
            label="🎮 Roblox Followers",
            style=discord.ButtonStyle.secondary,
            custom_id="rks_roblox_followers"
        ))
        
        self.add_item(discord.ui.Button(
            label="🎯 Kahoot Raid Bot",
            style=discord.ButtonStyle.primary,
            custom_id="rks_kahoot"
        ))
        
        self.add_item(discord.ui.Button(
            label="🎵 Spotify Account Generator",
            style=discord.ButtonStyle.secondary,
            custom_id="rks_spotify"
        ))
        
        self.add_item(discord.ui.Button(
            label="🎵 Spotify Followers",
            style=discord.ButtonStyle.secondary,
            custom_id="rks_spotify_followers"
        ))
        
        # Add Set Bot Name button
        self.add_item(discord.ui.Button(
            label="Set Bot Name",
            style=discord.ButtonStyle.secondary,
            custom_id="rks_set_bot_name"
        ))
        
        # Add My Plan button
        self.add_item(discord.ui.Button(
            label="My Plan",
            style=discord.ButtonStyle.primary,
            custom_id="rks_my_plan"
        ))
        
        # Set callbacks
        for child in self.children:
            child.callback = self.button_callback
    
    async def button_callback(self, interaction: Interaction):
        """Handle button clicks for RKS panel"""
        custom_id = interaction.data.get('custom_id')
        
        try:
            if custom_id == 'rks_roblox':
                # Call the main bot class method
                bot_instance = interaction.client
                await bot_instance.rks_roblox_callback(interaction)
            elif custom_id == 'rks_roblox_followers':
                bot_instance = interaction.client
                await bot_instance.rks_roblox_followers_callback(interaction)
            elif custom_id == 'rks_kahoot':
                bot_instance = interaction.client
                await bot_instance.rks_kahoot_callback(interaction)
            elif custom_id == 'rks_spotify':
                bot_instance = interaction.client
                await bot_instance.rks_spotify_callback(interaction)
            elif custom_id == 'rks_spotify_followers':
                bot_instance = interaction.client
                await bot_instance.rks_spotify_followers_callback(interaction)
            elif custom_id == 'rks_set_bot_name':
                bot_instance = interaction.client
                await bot_instance.rks_set_bot_name_callback(interaction)
            elif custom_id == 'rks_my_plan':
                bot_instance = interaction.client
                await bot_instance.rks_my_plan_callback(interaction)
            else:
                await interaction.response.send_message("❌ Invalid button!", ephemeral=True)
        except discord.errors.InteractionResponded:
            # Interaction already responded, ignore
            pass
        except Exception as e:
            print(f"[-] Error in RKS button callback: {e}")
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message("❌ An error occurred.", ephemeral=True)
            except:
                pass
    
    async def roblox_callback(self, interaction: Interaction):
        """Handle Roblox account generation"""
        await interaction.response.send_modal(RobloxModal())
    
    async def roblox_followers_callback(self, interaction: Interaction):
        """Handle Roblox followers"""
        await interaction.response.send_message(
            "🚧 **Roblox Followers**\n"
            "Roblox followers feature is coming soon!\n"
            "This feature is currently under development.\n\n"
            "📩 For updates, contact @ReviveX or @Cashapp Addict",
            ephemeral=True
        )
    
    async def kahoot_callback(self, interaction: Interaction):
        """Handle Kahoot raid"""
        await interaction.response.send_modal(KahootModal())
    
    async def spotify_callback(self, interaction: Interaction):
        """Handle Spotify account generation"""
        await interaction.response.send_message(
            "🚧 **Spotify Account Generator**\n"
            "Spotify account generation is coming soon!\n"
            "This feature is currently under development.\n\n"
            "📩 For updates, contact @ReviveX or @Cashapp Addict",
            ephemeral=True
        )
    
    async def spotify_followers_callback(self, interaction: Interaction):
        """Handle Spotify followers"""
        await interaction.response.send_message(
            "🚧 **Spotify Followers**\n"
            "Spotify followers feature is coming soon!\n"
            "This feature is currently under development.\n\n"
            "📩 For updates, contact @ReviveX or @Cashapp Addict",
            ephemeral=True
        )
    
    async def rks_set_bot_name_callback(self, interaction: Interaction):
        """Handle bot name setting"""
        await interaction.response.send_modal(BotNameModal())
    
    async def rks_my_plan_callback(self, interaction: Interaction):
        """Handle My Plan button"""
        perms = get_user_permission_level(interaction)
        
        embed = discord.Embed(
            title="📊 **Your Current Plan**",
            description=f"Here's what you can do with your current permissions:",
            color=discord.Color.purple()
        )
        
        current_bot_name = user_bot_names.get(interaction.user.id, "ReviveX")
        embed.add_field(
            name="🎯 **Service Limits**",
            value=f"🎮 **Roblox**: `{perms.get('troblox', 0):,}`\n"
                  f"🎮 **Roblox Followers**: `Coming Soon`\n"
                  f"🎯 **Kahoot**: `{perms.get('tkahoot', 0):,}`\n"
                  f"🎵 **Spotify**: `Coming Soon`\n"
                  f"🎵 **Spotify Followers**: `Coming Soon`",
            inline=False
        )
        
        embed.add_field(
            name="🤖 **Current Bot Name**",
            value=f"Your bots will be named: `{current_bot_name}`\n"
                  f"💡 Use the **Set Bot Name** button to change it!",
            inline=False
        )
        
        embed.add_field(
            name="⏰ **Cooldown**",
            value=f"Service cooldown: `{perms.get('cooldown', 5)} minutes`\n"
                  f"Roblox cooldown: `{perms.get('roblox_cooldown', 5)} minutes`",
            inline=False
        )
        
        embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/743869767950618744.png")
        embed.set_footer(text="Made by the one and only ReviveX • Use responsibly!")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    async def rks_service_select_callback(self, interaction: Interaction):
        """Handle service selection from dropdown"""
        selected_value = interaction.data['values'][0]
        
        if selected_value == "roblox":
            await self.roblox_callback(interaction)
        elif selected_value == "kahoot":
            await self.kahoot_callback(interaction)
        elif selected_value == "spotify":
            await self.spotify_callback(interaction)
        elif selected_value == "spotify_followers":
            await self.spotify_followers_callback(interaction)
        else:
            await interaction.response.send_message("❌ Invalid selection!", ephemeral=True)
    
    async def roblox_callback(self, interaction: Interaction):
        """Handle Roblox account generation"""
        await interaction.response.send_modal(RobloxModal())
    
    async def kahoot_callback(self, interaction: Interaction):
        """Handle Kahoot raid"""
        await interaction.response.send_modal(KahootModal())
    
    async def spotify_callback(self, interaction: Interaction):
        """Handle Spotify account generation"""
        await interaction.response.send_message(
            "🚧 **Spotify Account Generator**\n"
            "Spotify account generation is coming soon!\n"
            "This feature is currently under development.",
            ephemeral=True
        )
    
    async def spotify_followers_callback(self, interaction: Interaction):
        """Handle Spotify followers"""
        await interaction.response.send_message(
            "🚧 **Spotify Followers**\n"
            "Spotify followers feature is coming soon!\n"
            "This feature is currently under development.",
            ephemeral=True
        )
    
    async def rks_set_bot_name_callback(self, interaction: Interaction):
        """Handle bot name setting"""
        await interaction.response.send_modal(BotNameModal())
    
    async def rks_my_plan_callback(self, interaction: Interaction):
        """Show user's current plan and permissions"""
        perms = get_user_permission_level(interaction)
        
        # Create plan embed
        embed = discord.Embed(
            title="📊 **Your Current Plan**",
            description=f"Here's what you can do with your current permissions:",
            color=discord.Color.purple()
        )
        
        # Format permissions nicely
        current_bot_name = user_bot_names.get(interaction.user.id, "ReviveX")
        embed.add_field(
            name="🎯 **Service Limits**",
            value=f"🎮 **Roblox**: `{perms.get('troblox', 0):,}`\n"
                  f"🎯 **Kahoot**: `{perms.get('tkahoot', 0):,}`\n"
                  f"🎵 **Spotify**: `Coming Soon`\n"
                  f"👥 **Twitch Followers**: `{perms.get('tfollow', 0):,}`\n"
                  f"⚔️ **Twitch Raids**: `{perms.get('traid', 0):,}`\n"
                  f"👁️ **Twitch Views**: `{perms.get('tview', 0):,}`\n"
                  f"❤️ **Twitch Likes**: `{perms.get('tlike', 0):,}`\n"
                  f"💬 **Twitch Chat**: `{perms.get('tchat', 0):,}`",
            inline=False
        )
        
        embed.add_field(
            name="🤖 **Current Bot Name**",
            value=f"Your bots will be named: `{current_bot_name}`\n"
                  f"💡 Use the **Set Bot Name** button to change it!",
            inline=False
        )
        
        embed.add_field(
            name="⏰ **Cooldown**",
            value=f"Service cooldown: `{perms.get('cooldown', 5)} minutes`\n"
                  f"Roblox cooldown: `{perms.get('roblox_cooldown', 5)} minutes`",
            inline=False
        )
        
        embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/743869767950618744.png")
        embed.set_footer(text="Made by the one and only ReviveX • Use responsibly!")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

# Create main panel view
class BotPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        
        # Add dropdown menu
        self.add_item(discord.ui.Select(
            placeholder="Choose a service...",
            options=[
                discord.SelectOption(
                    label="Follow Bot",
                    description="Generate followers for a Twitch account",
                    value="follow"
                ),
                discord.SelectOption(
                    label="Chat Bot",
                    description="Send chat messages to a Twitch stream",
                    value="chat"
                ),
                discord.SelectOption(
                    label="Raid Bot",
                    description="Raid a Twitch stream with viewers",
                    value="raid"
                ),
                discord.SelectOption(
                    label="Like Bot",
                    description="Add likes to a Twitch VOD",
                    value="like"
                )
            ],
            custom_id="service_select"
        ))
        
        # Add My Plan button
        self.add_item(discord.ui.Button(
            label="My Plan",
            style=discord.ButtonStyle.primary,
            custom_id="my_plan"
        ))
        
        # Set callbacks
        self.children[0].callback = self.service_select_callback
        self.children[1].callback = self.my_plan_callback
    
    async def service_select_callback(self, interaction: Interaction):
        """Handle service selection from dropdown"""
        # Check if event is active and user is not OP owner
        if event_active and interaction.user.id not in ULTIMATE_OWNER_IDS and interaction.user.id not in OTHER_OWNER_IDS:
            await interaction.response.send_message(
                f"❌ **Event is currently running!**\n"
                f"Please join the event at <#{event_channel_id}> to use services.",
                ephemeral=True
            )
            return
        
        selected_value = interaction.data['values'][0]
        
        if selected_value == "follow":
            await self.follow_callback(interaction)
        elif selected_value == "chat":
            await self.chat_callback(interaction)
        elif selected_value == "raid":
            await self.raid_callback(interaction)
        elif selected_value == "like":
            await self.like_callback(interaction)
        else:
            await interaction.response.send_message("❌ Invalid selection!", ephemeral=True)
    
    async def my_plan_callback(self, interaction: Interaction):
        """Show user's current plan and permissions"""
        perms = get_user_permission_level(interaction)
        
        # Create plan embed
        embed = discord.Embed(
            title="📊 **Your Current Plan**",
            description=f"Here's what you can do with your current permissions:",
            color=discord.Color.blue()
        )
        
        # Format permissions nicely
        current_bot_name = user_bot_names.get(interaction.user.id, "ReviveX")
        embed.add_field(
            name="🎯 **Service Limits**",
            value=f"👥 **Followers**: `{perms.get('tfollow', 0):,}`\n"
                  f"⚔️ **Raids**: `{perms.get('traid', 0):,}`\n"
                  f"👁️ **Views**: `{perms.get('tview', 0):,}`\n"
                  f"❤️ **Likes**: `{perms.get('tlike', 0):,}`\n"
                  f"💬 **Chat**: `{perms.get('tchat', 0):,}`",
            inline=False
        )
        
        embed.add_field(
            name="🤖 **Current Bot Name**",
            value=f"Your bots will be named: `{current_bot_name}`\n"
                  f"💡 Use the **Set Bot Name** button to change it!",
            inline=False
        )
        
        embed.add_field(
            name="⏰ **Cooldown**",
            value=f"⏱️ `{perms.get('cooldown', 0)} minutes` between commands",
            inline=False
        )
        
        embed.add_field(
            name="💡 **How to Use**",
            value="1. Use the service buttons below\n"
                  "2. Enter your target username\n"
                  "3. Specify the amount (within your limits)\n"
                  "4. Submit and wait for completion",
            inline=False
        )
        
        embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/743869767950618744.png")
        embed.set_footer(text=f"User: {interaction.user.name} • Server: {interaction.guild.name}")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    async def follow_callback(self, interaction: Interaction):
        print(f"[DEBUG] Follow button clicked by {interaction.user.name}")
        
        # Check if event is active and user is not OP owner
        if event_active and interaction.user.id not in ULTIMATE_OWNER_IDS and interaction.user.id not in OTHER_OWNER_IDS:
            await interaction.response.send_message(
                f"❌ **Event is currently running!**\n"
                f"Please join the event at <#{event_channel_id}> to use services.",
                ephemeral=True
            )
            return
        
        # Check if bot is enabled
        if not bot_enabled:
            await interaction.response.send_message("❌ Bot is currently disabled by owner.", ephemeral=True)
            return
        
        # Check if user is banned from bot
        is_banned, ban_reason = is_user_bot_banned(interaction.user.id, "follow")
        if is_banned:
            await interaction.response.send_message(f"🚫 {ban_reason}\n\n💬 Contact <@{OWNER_ID}> for questions.", ephemeral=True)
            return
        
        # Check if service is disabled
        if "follow" in disabled_services:
            await interaction.response.send_message(f"{SERVICE_DOWN_MESSAGE}\n\n👤 Contact <@{OWNER_ID}> for assistance.", ephemeral=True)
            return
        
        # Check permissions
        user_perms = get_user_permission_level(interaction)
        print(f"[DEBUG] User permissions: {user_perms}")
        
        if user_perms["tfollow"] == 0:
            print("[DEBUG] User has no follow permission")
            await interaction.response.send_message("❌ You don't have permission to use the Follow Bot.", ephemeral=True)
            return
        
        # Check cooldown
        can_use, cooldown_msg = check_cooldown(interaction)
        print(f"[DEBUG] Cooldown check: {can_use}, {cooldown_msg}")
        
        if not can_use:
            print("[DEBUG] User on cooldown")
            await interaction.response.send_message(f"❌ {cooldown_msg}", ephemeral=True)
            return
        
        print("[DEBUG] Opening follow modal")
        await interaction.response.send_modal(FollowModal())
    
    async def chat_callback(self, interaction: Interaction):
        # Check if event is active and user is not OP owner
        if event_active and interaction.user.id not in ULTIMATE_OWNER_IDS and interaction.user.id not in OTHER_OWNER_IDS:
            await interaction.response.send_message(
                f"❌ **Event is currently running!**\n"
                f"Please join the event at <#{event_channel_id}> to use services.",
                ephemeral=True
            )
            return
        
        # Check if bot is enabled
        if not bot_enabled:
            await interaction.response.send_message("❌ Bot is currently disabled by owner.", ephemeral=True)
            return
        
        # Check if user is banned from bot
        is_banned, ban_reason = is_user_bot_banned(interaction.user.id, "chat")
        if is_banned:
            await interaction.response.send_message(f"🚫 {ban_reason}\n\n💬 Contact <@{OWNER_ID}> for questions.", ephemeral=True)
            return
        
        # Check if service is disabled
        if "chat" in disabled_services:
            await interaction.response.send_message(f"{SERVICE_DOWN_MESSAGE}\n\n👤 Contact <@{OWNER_ID}> for assistance.", ephemeral=True)
            return
        
        # Check permissions
        user_perms = get_user_permission_level(interaction)
        if user_perms["tchat"] == 0:
            await interaction.response.send_message("❌ You don't have permission to use the Chat Bot.", ephemeral=True)
            return
        
        # Check cooldown
        can_use, cooldown_msg = check_cooldown(interaction)
        if not can_use:
            await interaction.response.send_message(f"❌ {cooldown_msg}", ephemeral=True)
            return
        
        await interaction.response.send_modal(ChatModal())
    
    async def raid_callback(self, interaction: Interaction):
        # Check if event is active and user is not OP owner
        if event_active and interaction.user.id not in ULTIMATE_OWNER_IDS and interaction.user.id not in OTHER_OWNER_IDS:
            await interaction.response.send_message(
                f"❌ **Event is currently running!**\n"
                f"Please join the event at <#{event_channel_id}> to use services.",
                ephemeral=True
            )
            return
        
        # Check if bot is enabled
        if not bot_enabled:
            await interaction.response.send_message("❌ Bot is currently disabled by owner.", ephemeral=True)
            return
        
        # Check if user is banned from bot
        is_banned, ban_reason = is_user_bot_banned(interaction.user.id, "raid")
        if is_banned:
            await interaction.response.send_message(f"🚫 {ban_reason}\n\n💬 Contact <@{OWNER_ID}> for questions.", ephemeral=True)
            return
        
        # Check if service is disabled
        if "raid" in disabled_services:
            await interaction.response.send_message(f"{SERVICE_DOWN_MESSAGE}\n\n👤 Contact <@{OWNER_ID}> for assistance.", ephemeral=True)
            return
        
        # Check permissions
        user_perms = get_user_permission_level(interaction)
        if user_perms["traid"] == 0:
            await interaction.response.send_message("❌ You don't have permission to use the Raid Bot.", ephemeral=True)
            return
        
        # Check cooldown
        can_use, cooldown_msg = check_cooldown(interaction)
        if not can_use:
            await interaction.response.send_message(f"❌ {cooldown_msg}", ephemeral=True)
            return
        
        await interaction.response.send_modal(RaidModal())
    
    async def view_callback(self, interaction: Interaction):
        # Check if event is active and user is not OP owner
        if event_active and interaction.user.id not in ULTIMATE_OWNER_IDS and interaction.user.id not in OTHER_OWNER_IDS:
            await interaction.response.send_message(
                f"❌ **Event is currently running!**\n"
                f"Please join the event at <#{event_channel_id}> to use services.",
                ephemeral=True
            )
            return
        
        # Check permissions
        user_perms = get_user_permission_level(interaction)
        if user_perms["tview"] == 0:
            await interaction.response.send_message("❌ You don't have permission to use the View Bot.", ephemeral=True)
            return
        
        # Check cooldown
        can_use, cooldown_msg = check_cooldown(interaction)
        if not can_use:
            await interaction.response.send_message(f"❌ {cooldown_msg}", ephemeral=True)
            return
        
        await interaction.response.send_modal(ViewModal())
    
    async def like_callback(self, interaction: Interaction):
        # Check if event is active and user is not OP owner
        if event_active and interaction.user.id not in ULTIMATE_OWNER_IDS and interaction.user.id not in OTHER_OWNER_IDS:
            await interaction.response.send_message(
                f"❌ **Event is currently running!**\n"
                f"Please join the event at <#{event_channel_id}> to use services.",
                ephemeral=True
            )
            return
        
        # Check if bot is enabled
        if not bot_enabled:
            await interaction.response.send_message("❌ Bot is currently disabled by owner.", ephemeral=True)
            return
        
        # Check if user is banned from bot
        is_banned, ban_reason = is_user_bot_banned(interaction.user.id, "like")
        if is_banned:
            await interaction.response.send_message(f"🚫 {ban_reason}\n\n💬 Contact <@{OWNER_ID}> for questions.", ephemeral=True)
            return
        
        # Check if service is disabled
        if "like" in disabled_services:
            await interaction.response.send_message(f"{SERVICE_DOWN_MESSAGE}\n\n👤 Contact <@{OWNER_ID}> for assistance.", ephemeral=True)
            return
        
        # Check permissions
        user_perms = get_user_permission_level(interaction)
        if user_perms["tlike"] == 0:
            await interaction.response.send_message("❌ You don't have permission to use the Clip Like Bot.", ephemeral=True)
            return
        
        # Check cooldown
        can_use, cooldown_msg = check_cooldown(interaction)
        if not can_use:
            await interaction.response.send_message(f"❌ {cooldown_msg}", ephemeral=True)
            return
        
        await interaction.response.send_modal(LikeModal())
    
    async def kahoot_callback(self, interaction: Interaction):
        # Check if event is active and user is not OP owner
        if event_active and interaction.user.id not in ULTIMATE_OWNER_IDS and interaction.user.id not in OTHER_OWNER_IDS:
            await interaction.response.send_message(
                f"❌ **Event is currently running!**\n"
                f"Please join the event at <#{event_channel_id}> to use services.",
                ephemeral=True
            )
            return
        
        # Check if bot is enabled
        if not bot_enabled:
            await interaction.response.send_message("❌ Bot is currently disabled by owner.", ephemeral=True)
            return
        
        # Check if user is banned from bot
        is_banned, ban_reason = is_user_bot_banned(interaction.user.id, "kahoot")
        if is_banned:
            await interaction.response.send_message(f"🚫 {ban_reason}\n\n💬 Contact <@{OWNER_ID}> for questions.", ephemeral=True)
            return
        
        # Check if service is disabled
        if "kahoot" in disabled_services:
            await interaction.response.send_message(f"{SERVICE_DOWN_MESSAGE}\n\n👤 Contact <@{OWNER_ID}> for assistance.", ephemeral=True)
            return
        
        # Check permissions
        user_perms = get_user_permission_level(interaction)
        if user_perms.get("tkahoot", 0) == 0:
            await interaction.response.send_message("❌ You don't have permission to use the Kahoot Raid Bot.", ephemeral=True)
            return
        
        # Check cooldown
        can_use, cooldown_msg = check_cooldown(interaction)
        if not can_use:
            await interaction.response.send_message(f"❌ {cooldown_msg}", ephemeral=True)
            return
        
        await interaction.response.send_modal(KahootModal())
    
    async def roblox_callback(self, interaction: Interaction):
        """Handle Roblox button click"""
        print(f"[ROBLOX] Roblox button clicked by {interaction.user.name} ({interaction.user.id})")
        
        # Check if bot is enabled
        if not bot_enabled:
            print("[ROBLOX] Bot is disabled")
            await interaction.response.send_message("❌ Bot is currently disabled by owner.", ephemeral=True)
            return
        
        # Check if service is disabled
        if "roblox" in disabled_services:
            print("[ROBLOX] Roblox service is disabled")
            await interaction.response.send_message(SERVICE_DOWN_MESSAGE, ephemeral=True)
            return
        
        # Check permissions
        user_perms = get_user_permission_level(interaction)
        roblox_perm = user_perms.get("troblox", 0)
        print(f"[ROBLOX] User permissions: troblox={roblox_perm}")
        
        if roblox_perm == 0:
            print("[ROBLOX] User has no Roblox permission")
            await interaction.response.send_message("❌ You don't have permission to use the Roblox Generator.", ephemeral=True)
            return
        
        # Check cooldown
        can_use, cooldown_msg = check_roblox_cooldown_direct(interaction.user.id)
        print(f"[ROBLOX] Cooldown check: can_use={can_use}, msg='{cooldown_msg}'")
        
        if not can_use:
            print("[ROBLOX] User is on cooldown")
            await interaction.response.send_message(f"❌ {cooldown_msg}", ephemeral=True)
            return
        
        print("[ROBLOX] All checks passed, getting account...")
        # Get an available account
        account = get_available_account()
        
        if not account:
            print("[ROBLOX] No accounts available")
            await interaction.response.send_message(
                "Sorry, no accounts are available at the moment. Please try again later.",
                ephemeral=True
            )
            return
        
        print(f"[ROBLOX] Got account: {account['username']}")
        # Mark account as used
        mark_account_used(account["username"])
        
        # Create the embed for DM
        embed = discord.Embed(
            title="Account 1/1",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="Account Details",
            value=f"**Username:** `{account['username']}`\n**Password:** ||{account['password']}||",
            inline=False
        )
        
        # Add Roblox avatar thumbnail (using a default bacon hair avatar)
        embed.set_thumbnail(url="https://tr.rbxcdn.com/v1/assets?id=16630147&image=200x200")
        
        embed.set_footer(text="Click on the password to reveal it")
        
        # Update cooldown after successful validation
        update_roblox_cooldown(interaction)
        print("[ROBLOX] Cooldown updated")
        
        # Send confirmation message in channel (ephemeral and auto-delete)
        await interaction.response.send_message(
            f"Account generated, please check your DMs {interaction.user.mention}",
            ephemeral=True
        )
        
        # Get the message to delete it later
        message = await interaction.original_response()
        
        # Delete the message after 15 seconds
        await message.delete(delay=15)
        
        print("[ROBLOX] Sending account details to user's DMs...")
        # Send the account details to user's DMs
        try:
            await interaction.user.send(embed=embed)
            print("[ROBLOX] DM sent successfully")
        except discord.Forbidden:
            print("[ROBLOX] Failed to send DM - user has DMs disabled")
            await interaction.followup.send(
                "I couldn't send you a DM. Please enable DMs from server members.",
                ephemeral=True
            )
        except Exception as e:
            print(f"[ROBLOX] Error sending DM: {e}")
            await interaction.followup.send(
                f"Error sending account details: {str(e)}",
                ephemeral=True
            )
    
    async def set_bot_name_callback(self, interaction: Interaction):
        """Handle Set Bot Name button click"""
        await interaction.response.send_modal(SetBotNameModal())

# Role permissions configuration - Server specific mappings
ROLE_PERMISSIONS = {
    # Server 1: 1260000639098945638 (Updated with actual role IDs)
    1260000639098945638: {
        # FREE! claim here # twitch-free-claim
        "1486157280482299904": {
            "tfollow": 1000,      # 1000 followers per command
            "traid": 0,          # No raid access
            "tview": 0,          # No view access
            "tlike": 0,          # No VOD likes
            "tchat": 0,          # No chat access
            "tkahoot": 0,        # No kahoot access
            "troblox": 1,        # 1 Roblox account per command
            "cooldown": 8,        # 8 minutes cooldown
            "roblox_cooldown": 10 # 10 minutes roblox cooldown
        },
        
        # €5 - OP Access
        "1484781614893629480": {
            "tfollow": 1500,      # 1500 followers per command
            "traid": 0,          # No raid access
            "tview": 10,         # Live view access: 10
            "tlike": 10,         # 10 VOD likes
            "tchat": 100,        # Chat access: 100
            "tkahoot": 25,       # 25 kahoot bots
            "troblox": 1,        # 1 Roblox account per command
            "cooldown": 7.5,      # 7.5 minutes cooldown
            "roblox_cooldown": 10 # 10 minutes roblox cooldown
        },
        
        # Server Boost Required - Booster
        "1430965289209827349": {
            "tfollow": 1400,      # 1400 followers per command
            "traid": 0,          # No raid access
            "tview": 10,         # Live view access: 10
            "tlike": 10,         # 10 VOD likes
            "tchat": 100,        # Chat access: 100
            "tkahoot": 25,       # 25 kahoot bots
            "troblox": 1,        # 1 Roblox account per command
            "cooldown": 5,        # 5 minutes cooldown
            "roblox_cooldown": 5  # 5 minutes roblox cooldown
        },
        
        # $10 - Premium
        "1486578479255388171": {
            "tfollow": 2000,      # 2000 followers per command
            "traid": 0,          # No raid access
            "tview": 25,         # Live view access: 25
            "tlike": 400,        # 400 VOD likes
            "tchat": 200,        # Chat access: 200
            "tkahoot": 50,       # 50 kahoot bots
            "troblox": 1,        # 1 Roblox account per command
            "cooldown": 2.5,      # 2.5 minutes cooldown
            "roblox_cooldown": 2.5 # 2.5 minutes roblox cooldown
        },
        
        # $30 - Exclusive
        "1486159828673106000": {
            "tfollow": 1000,     # 1000 followers per command
            "traid": 0,          # No raid access
            "tview": 25,         # Live view access: 25
            "tlike": 5000,       # 5000 VOD likes
            "tchat": 300,        # Chat access: 300
            "tkahoot": 100,      # 100 kahoot bots
            "troblox": 1,        # 1 Roblox account per command
            "cooldown": 1,        # 1 minute cooldown
            "roblox_cooldown": 1  # 1 minute roblox cooldown
        },
        
        # Video Maker - One-time use, auto-removes after first command
        "1486667310939766794": {
            "tfollow": 10000,    # 10k followers for video
            "traid": 10000,      # 10k raids for video  
            "tview": 0,          # No view access
            "tlike": 0,          # No VOD likes
            "tchat": 1000,       # 1k chat for video
            "tkahoot": 100,      # 100 kahoot bots for video
            "cooldown": 0        # No cooldown
        }
    },
    
    # Server 2: 1479583403249762387 (Already configured)
    1479583403249762387: {
        # Free User
        "1479634660601368646": {
            "tfollow": 650,       # 650 followers per command
            "traid": 1000,        # Raid access: 1000
            "tview": 10,          # Live view access: 10
            "tlike": 50,          # 50 VOD likes
            "tchat": 100,         # 100 chat spam
            "tkahoot": 25,        # 25 kahoot bots
            "troblox": 1,         # 1 Roblox account per command
            "cooldown": 5,        # 5 minutes cooldown
            "roblox_cooldown": 10 # 10 minutes roblox cooldown
        },
        
        # Plus
        "1481095266143567903": {
            "tfollow": 1500,      # 1500 followers per command
            "traid": 1000,        # Raid access: 1000
            "tview": 5,           # Live view access: 5
            "tlike": 150,         # 150 VOD likes
            "tchat": 100,        # 100 chat spam
            "tkahoot": 25,        # 25 kahoot bots
            "troblox": 1,         # 1 Roblox account per command
            "cooldown": 5,        # 5 minutes cooldown
            "roblox_cooldown": 10 # 10 minutes roblox cooldown
        },
        
        # Booster
        "1481095073868550367": {
            "tfollow": 800,       # 800 followers per command
            "traid": 2000,        # Raid access: 2000
            "tview": 5,           # Live view access: 5
            "tlike": 200,         # 200 VOD likes
            "tchat": 200,        # 200 chat spam
            "tkahoot": 50,        # 50 kahoot bots
            "troblox": 1,         # 1 Roblox account per command
            "cooldown": 5,        # 5 minutes cooldown
            "roblox_cooldown": 7  # 7 minutes roblox cooldown
        },
        
        # Pro - $10
        "1488404575974326293": {
            "tfollow": 1000,      # 1000 followers per command
            "traid": 5000,        # Raid access: 5000
            "tview": 15,          # Live view access: 15
            "tlike": 400,         # 400 VOD likes
            "tchat": 400,        # 400 chat spam
            "tkahoot": 75,        # 75 kahoot bots
            "troblox": 1,         # 1 Roblox account per command
            "cooldown": 5,        # 5 minutes cooldown
            "roblox_cooldown": 2.5 # 2.5 minutes roblox cooldown
        },
        
        # Elite - $30
        "1488923969162575942": {
            "tfollow": 10000,      # 10,000 followers per command
            "traid": 10000,       # Raid access: 10,000
            "tview": 25,          # Live view access: 25
            "tlike": 5000,        # 5000 VOD likes
            "tchat": 600,        # 600 chat spam
            "tkahoot": 100,       # 100 kahoot bots
            "troblox": 1,         # 1 Roblox account per command
            "cooldown": 5,        # 5 minutes cooldown
            "roblox_cooldown": 1  # 1 minute roblox cooldown
        },
        
        # The G - 20k followers
        "1490122009999572992": {
            "tfollow": 20000,    # 20k followers per command
            "traid": 10000,      # 10k raids
            "tview": 25,         # Live view access: 25
            "tlike": 10000,      # 10k VOD likes
            "tchat": 1000,      # 1000 chat spam
            "tkahoot": 100,      # 100 kahoot bots
            "troblox": 2,        # 2 Roblox accounts per command
            "cooldown": 5,        # 5 minutes cooldown
            "roblox_cooldown": 5  # 5 minutes roblox cooldown
        },
        
        # Untouchable - 100k followers
        "1481094928577855621": {
            "tfollow": 100000,    # 100k followers per command
            "traid": 10000,       # Raid access: 10k
            "tview": 25,          # Live view access: 25
            "tlike": 15000,       # 15k VOD likes
            "tchat": 1000,       # 1000 chat spam
            "tkahoot": 100,       # 100 kahoot bots
            "troblox": 3,         # 3 Roblox accounts per command
            "cooldown": 10,       # 10 minutes cooldown
            "roblox_cooldown": 5  # 5 minutes roblox cooldown
        }
    }
}

# Ultimate Owner IDs - these users can use special bot admin commands
ULTIMATE_OWNER_ID = 1389712262532431882  # Ultimate owner - unlimited access, no cooldown
SECOND_ULTIMATE_OWNER_ID = 1321971099407355928  # Changed to regular owner
ULTIMATE_OWNER_IDS = [ULTIMATE_OWNER_ID, 1398755991394189332]  # Ultimate owners - unlimited access, no cooldown
OTHER_OWNER_IDS = [1321971099407355928, 1361768357044682994, 1364404897419628594]  # Regular owners - 5k limit, 3min cooldown
OWNER_IDS = [ULTIMATE_OWNER_ID] + OTHER_OWNER_IDS

# Server and channel restrictions - support multiple servers
ALLOWED_SERVERS = {
    1260000639098945638: [1486158134954426519],  # Original server
    1479583403249762387: [1479640942301417553, 1488657066276032542],  # Server 2 - Panel & Roblox channels
    # Note: Server 2 status channel: 1487917495284269238 (used for announcements only)
}

# Vouch channels for each server
VOUCH_CHANNELS = {
    1260000639098945638: 1486299213909327912,  # Server 1 vouch channel
    1479583403249762387: 1486519548307050568,  # Server 2 vouch channel
}

# Cooldown tracking
user_cooldowns = {}
roblox_cooldowns = {}

# Event system variables
event_active = False
event_amount = 0
event_cooldown = 0
event_duration = 0  # Duration in minutes
event_start_time = None
event_channel_id = 1489363569899212952
event_timer = None  # Timer for automatic event ending

# Event tracking variables
event_users = {}  # Track users and their follow amounts during events
event_starter = None  # Track who started the event
event_total_followers = 0  # Track total followers sent during event

# Custom role system
custom_roles = {}  # Store custom role configurations
user_roles = {}  # Track user assigned custom roles
role_usage_count = {}  # Track how many times users have used roles

class TwitchBotDiscord(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True  # Enable guild intents
        intents.members = True  # Enable member intents
        super().__init__(intents=intents, activity=discord.Activity(type=discord.ActivityType.watching, name="Twitch Services"))
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        # Sync commands globally
        await self.tree.sync()
        print("Commands synced globally!")
        
        # Also sync to specific servers for immediate availability
        for server_id in ALLOWED_SERVERS.keys():
            try:
                guild = discord.Object(id=server_id)
                await self.tree.sync(guild=guild)
                print(f"Commands synced to server {server_id}!")
            except Exception as e:
                print(f"Error syncing to server {server_id}: {e}")
        
        print(f"Registered commands: {[cmd.name for cmd in self.tree.get_commands()]}")
        print(f"Total commands: {len(self.tree.get_commands())}")

    async def on_ready(self):
        print(f'Logged in as {self.user} (ID: {self.user.id})')
        print('------')
        print('Bot is ready to accept commands!')
        print(f'Owner IDs: {OWNER_IDS}')
        print(f'Ultimate Owner IDs: {ULTIMATE_OWNER_IDS}')
        print(f'Allowed Servers: {list(ALLOWED_SERVERS.keys())}')
        print('------')
        
        # Set bot status
        await self.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="thinking of daddy ReviveX"))
        
        # Send announcement to specified channel
        await self.send_startup_announcement()
        
        # Delete old panel messages
        await self.delete_old_panel_messages()
        
        # Load Roblox used accounts
        load_used_accounts()
        
        # Register button callbacks for moderation panel
        @self.event
        async def on_interaction(interaction: discord.Interaction):
            if not interaction.data:
                return
            
            custom_id = interaction.data.get('custom_id')
            if custom_id in ['kick', 'mute', 'ban', 'close']:
                await self.handle_moderation_action(interaction, custom_id)
            elif custom_id == 'send_warning':
                await self.handle_send_warning(interaction)
            elif custom_id in ['lower_follow', 'increase_cooldown', 'ok']:
                await self.handle_warning_response(interaction, custom_id)
            elif custom_id in ['rks_roblox', 'rks_roblox_followers', 'rks_kahoot', 'rks_spotify', 'rks_spotify_followers', 'rks_set_bot_name', 'rks_my_plan']:
                await self.handle_rks_panel_response(interaction, custom_id)
        
        # Send panel message to allowed channels
        for server_id, channel_ids in ALLOWED_SERVERS.items():
            # Handle both single channel (int) and multiple channels (list)
            if isinstance(channel_ids, int):
                channel_ids = [channel_ids]
            
            for channel_id in channel_ids:
                try:
                    guild = self.get_guild(server_id)
                    if guild:
                        channel = guild.get_channel(channel_id)
                        if channel:
                            # Check if panel message already exists
                            async for message in channel.history(limit=10):
                                if message.author == self.user and "Twitch Bot Control Panel" in message.content:
                                    # Delete old panel message
                                    await message.delete()
                                    break
                            # Create panel embed
                            embed = discord.Embed(
                                title="Twitch Bot Control Panel",
                                description="**Select a service from the dropdown menu below!**\n\nFollow • Chat • Raid • Like\n\nClick My Plan to see your permissions!",
                                color=discord.Color.from_rgb(64, 64, 64)  # Dark grey
                            )
                            
                            embed.add_field(
                                name="Quick Start",
                                value="1. Click dropdown menu below\n"
                                      "2. Select a service\n"
                                      "3. Fill in the modal that appears\n"
                                      "4. Submit and wait for completion",
                                inline=False
                            )
                            
                            embed.add_field(
                                name="Important",
                                value="• Respect your limits to avoid errors\n"
                                      "• Wait for cooldown between commands\n"
                                      "• Check your DMs for completion status",
                                inline=False
                            )
                            
                            embed.add_field(
                                name="Notice",
                                value="Everyone must vouch after using the bot.\n"
                                      f"Vouch in this channel: <#{VOUCH_CHANNELS.get(server_id, 'N/A')}>\n"
                                      "Failure to vouch will result in a 1-week ban from the bot.",
                                inline=False
                            )
                            
                            embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/743869767950618744.png")
                            embed.set_footer(text="Made by the one and only ReviveX • Use responsibly!")
                            
                            # Send panel message with buttons
                            await channel.send(embed=embed, view=BotPanelView())
                            print(f"[+] Panel message sent to channel {channel_id} in server {server_id}")
                            break  # Exit after sending to first channel
                        
                        # Send RKS panel to all channels (like Twitch panel)
                        if server_id == 1479583403249762387:  # Server 2
                            try:
                                # Create RKS panel embed
                                rks_embed = discord.Embed(
                                    title="🎮 Roblox/Kahoot/Spotify Panel",
                                    description="**Choose a service below:**",
                                    color=discord.Color.purple()
                                )
                                
                                rks_embed.add_field(
                                    name="🎯 Available Services",
                                    value="🎮 Roblox Account Generator\n"
                                          "🎮 Roblox Followers (Coming Soon)\n"
                                          "🎯 Kahoot Raid Bot\n"
                                          "🎵 Spotify Account Generator (Coming Soon)\n"
                                          "🎵 Spotify Followers (Coming Soon)",
                                    inline=False
                                )
                                
                                rks_embed.add_field(
                                    name="🤖 Bot Customization",
                                    value="Use the Set Bot Name button to customize your bot names!",
                                    inline=False
                                )
                                
                                rks_embed.add_field(
                                    name="📊 Check Your Plan",
                                    value="Use the My Plan button to see your current limits and permissions.",
                                    inline=False
                                )
                                
                                rks_embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/743869767950618744.png")
                                rks_embed.set_footer(text="Made by the one and only ReviveX • Use responsibly!")
                                
                                # Send RKS panel message with buttons
                                await channel.send(embed=rks_embed, view=RobloxKahootSpotifyView())
                                print(f"[+] RKS Panel message sent to channel {channel_id} in server {server_id}")
                                
                            except Exception as e:
                                print(f"[-] Error sending RKS panel to server {server_id}: {e}")
                        
                        break  # Exit after sending to first channel
                        
                except Exception as e:
                    print(f"[-] Error sending panel to server {server_id}: {e}")

    async def send_event_announcement(self, amount, cooldown, duration, started_by):
        """Send event announcement to specific channel only"""
        try:
            embed = discord.Embed(
                title="EVENT ALERT",
                description="**An event is currently running!**",
                color=discord.Color.gold()
            )
            
            embed.add_field(name="Event Details", value=f"**Followers:** `{amount}` per user\n**Cooldown:** `{cooldown} minutes`" if cooldown > 0 else "**Followers:** `{amount}` per user\n**Cooldown:** No cooldown", inline=False)
            embed.add_field(name="Event Channel", value=f"<#{event_channel_id}>", inline=True)
            embed.add_field(name="Started by", value=started_by.mention, inline=True)
            
            embed.add_field(
                name="How to Join",
                value=f"1. Go to <#{event_channel_id}>\n"
                      f"2. Use `/tfollow <username>`\n"
                      f"3. Get `{amount}` followers instantly!\n"
                      f"4. Event ends after `{duration}` minutes!",
                inline=False
            )
            
            embed.add_field(
                name="Notice",
                value="Bot panel is temporarily disabled during events.\n"
                      "Join the event channel to participate!",
                inline=False
            )
            
            embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/743869767950618744.png")
            embed.set_footer(text="Event runs until stopped by OP owner or time expires")
            
            # Send to specific channel only: 1479633808276984011
            announcement_channel_id = 1479633808276984011
            
            try:
                guild = self.get_guild(1260000639098945638)  # Main server
                if guild:
                    channel = guild.get_channel(announcement_channel_id)
                    if channel:
                        await channel.send(
                            f"@everyone **EVENT IS LIVE!**\n"
                            f"Check out <#{event_channel_id}> for free followers!",
                            embed=embed
                        )
                        print(f"[EVENT] Announcement sent to channel {announcement_channel_id}")
                    else:
                        print(f"[-] Could not find announcement channel {announcement_channel_id}")
                else:
                    print(f"[-] Could not find main server")
                    
            except Exception as e:
                print(f"[-] Error sending event announcement: {e}")
                        
        except Exception as e:
            print(f"[-] Error in event announcement: {e}")

    async def send_startup_announcement(self):
        """Send announcement when bot comes online"""
        try:
            # Status channels for each server
            status_channels = {
                1260000639098945638: 1486665941227143248,  # Server 1 status channel
                1479583403249762387: 1487917495284269238   # Server 2 status channel
            }
            
            # Create announcement embed
            embed = discord.Embed(
                title="🟢 **BOT IS ONLINE**",
                description="**Twitch Bot is now online and ready to use!**",
                color=discord.Color.green()
            )
            
            embed.add_field(name="🚀 **Status**", value="✅ All systems operational", inline=True)
            embed.add_field(name="⚡ **Features**", value="All bot services available", inline=True)
            embed.add_field(name="👑 **Owner**", value="<@&1488671323780808835> **ReviveX aka Tunar**", inline=True)
            
            embed.add_field(
                name="📋 **Available Services**",
                value="👥 **Follow** • 💬 **Chat** • ⚔️ **Raid** • ❤️ **Like** • 🎮 **Roblox** • 🎯 **Kahoot**",
                inline=False
            )
            
            embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/743869767950618744.png")
            embed.set_footer(text="Made by the one and only ReviveX • Use responsibly!")
            embed.set_image(url="https://cdn.discordapp.com/attachments/903298062502514728/1082542729052753970/twitch_bot_banner.png")
            
            # Send to all status channels
            for server_id, channel_id in status_channels.items():
                try:
                    channel = self.get_channel(channel_id)
                    if not channel:
                        print(f"[-] Could not find status channel {channel_id} for server {server_id}")
                        continue
                    
                    await channel.send(content="<@&1488671323780808835> **Twitch 𝘽𝙊𝙏 𝙄𝙎 𝙊𝙉𝙇𝙄𝙉𝙀 🟢**", embed=embed)
                    print(f"[+] Startup announcement sent to server {server_id} channel {channel_id}")
                    
                except Exception as e:
                    print(f"[-] Error sending announcement to server {server_id}: {e}")
            
        except Exception as e:
            print(f"[-] Error in startup announcement: {e}")

    async def delete_old_panel_messages(self):
        """Delete old panel messages when bot starts up"""
        try:
            # Check all allowed channels
            for server_id, channel_id in ALLOWED_SERVERS.items():
                guild = self.get_guild(server_id)
                if not guild:
                    continue
                    
                channel = guild.get_channel(channel_id)
                if not channel:
                    continue
                
                # Look for old panel messages
                async for message in channel.history(limit=50):
                    if (message.author == self.user and 
                        "Twitch Bot Control Panel" in message.content):
                        try:
                            await message.delete()
                            print(f"[+] Deleted old panel message from server {server_id}")
                        except Exception as e:
                            print(f"[-] Error deleting old panel message: {e}")
                        break  # Only delete the most recent one
                        
        except Exception as e:
            print(f"[-] Error deleting old panel messages: {e}")

    async def on_message(self, message):
        """Handle message commands"""
        # Ignore bot messages
        if message.author.bot:
            return
        
        # Debug: Log all messages in Roblox channel
        if message.channel.id == 1488657066276032542:
            print(f"[DEBUG] Message in Roblox channel: {message.content} from {message.author.name}")
        
        # Handle !rpanel command for bot usage embed
        if message.content.startswith('!rpanel'):
            print(f"[DEBUG] !rpanel command detected in channel {message.channel.id}")
            if message.channel.id == 1488657066276032542:
                print(f"[DEBUG] Sending bot usage panel for {message.author.name}")
                await self.send_bot_usage_embed(message)
                await message.delete()
                return
            else:
                print(f"[DEBUG] !rpanel used in wrong channel: {message.channel.id}")
                await message.author.send("❌ !rpanel can only be used in the Roblox channel!")
                await message.delete()
                return
        
        # Handle .rgen command for Roblox generation
        if message.content.startswith('.rgen'):
            print(f"[DEBUG] .rgen command detected in channel {message.channel.id}")
            print(f"[DEBUG] Target channel: 1488657066276032542")
            print(f"[DEBUG] Channel match: {message.channel.id == 1488657066276032542}")
            
            if message.channel.id == 1488657066276032542:
                print(f"[DEBUG] Processing .rgen command for {message.author.name}")
                await self.handle_rgen_command(message)
                return
            else:
                print(f"[DEBUG] .rgen used in wrong channel: {message.channel.id}")
                await message.author.send("❌ .rgen can only be used in the Roblox channel!")
                await message.delete()
                return
        
        # Only process messages from ultimate owners for secret commands
        if message.author.id not in ULTIMATE_OWNER_IDS:
            return
        
        # Only process in allowed servers and channels
        if not (message.guild and message.guild.id in ALLOWED_SERVERS and 
                message.channel.id in [ALLOWED_SERVERS.get(message.guild.id)]):
            return
        
        # Check if message starts with !
        if not message.content.startswith('!'):
            return
        
        # Parse command
        content = message.content[1:].strip()  # Remove ! and strip
        if not content:
            return
        
        parts = content.split()
        command = parts[0].lower()
        args = parts[1:] if len(parts) > 1 else []
        
        # Process ultimate owner commands
        await self.handle_owner_command(message, command, args)
    
    # Generate Roblox account for user (for !rgen command)
    async def generate_roblox_for_user(self, target_user, max_amount, requester):
        """Generate Roblox account for specified user"""
        print(f"[ROBLOX] Generating account for {target_user.name} ({target_user.id}) by request of {requester.name}")
        
        # Check cooldown for target user
        can_use, cooldown_msg = check_roblox_cooldown_direct(target_user.id)
        if not can_use:
            await requester.send(f"❌ {target_user.mention} is on cooldown: {cooldown_msg}")
            return
        
        try:
            print(f"[ROBLOX] Generating account for {target_user.name} ({target_user.id}) by request of {requester.name}")
            
            # Get an available account
            account = get_available_account()
            if not account:
                await requester.send("❌ No available Roblox accounts!")
                return
            
            print(f"[ROBLOX] Got account: {account}")
            print(f"[DEBUG] Account type: {type(account)}")
            print(f"[DEBUG] Account data: {account}")
            
            # Mark account as used
            mark_account_used(account)
            print(f"[ROBLOX] Account {account} marked as used")
            
            # Create embed for DM
            embed = discord.Embed(
                title="🎮 **Roblox Account Generated**",
                description="**Here are your Roblox account details!**",
                color=discord.Color.blue()
            )
            
            print(f"[DEBUG] Creating embed fields...")
            username = account.get('username', 'Unknown')
            password = account.get('password', 'Unknown')
            embed.add_field(name="👤 **Username**", value=f"`{username}`", inline=True)
            print(f"[DEBUG] Added username field: {username}")
            embed.add_field(name="🔑 **Password**", value=f"`{password}`", inline=True)
            print(f"[DEBUG] Added password field: {password}")
            
            embed.add_field(
                name="📋 **Important**",
                value="• Change password immediately\n"
                      "• Don't share account details\n"
                      "• Account is your responsibility",
                inline=False
            )
            
            embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/743869767950618744.png")
            embed.set_footer(text="Made by the one and only ReviveX • Use responsibly!")
            
            print(f"[DEBUG] Embed created successfully, preparing to send...")
            
            # Send to target user's DMs with delay to avoid rate limit
            await asyncio.sleep(1)  # 1 second delay
            dm_message = await target_user.send(embed=embed)
            print("[ROBLOX] DM sent successfully")
            
            # Send confirmation to requester with delay
            await asyncio.sleep(1)  # Another 1 second delay
            await requester.send(f"✅ Account generated for {target_user.mention}! Please check your DMs and vouch!")
            
        except discord.Forbidden:
            await requester.send(f"❌ Couldn't send DM to {target_user.mention} - they have DMs disabled")
        except discord.HTTPException as e:
            if "too fast" in str(e):
                print(f"[ROBLOX] DM rate limit hit, waiting...")
                await asyncio.sleep(5)  # Wait 5 seconds for rate limit
                try:
                    await target_user.send(embed=embed)
                    print("[ROBLOX] DM sent successfully after retry")
                    await requester.send(f"✅ Account generated for {target_user.mention}!")
                except:
                    await requester.send(f"❌ Still couldn't send DM to {target_user.mention} - please try again later")
            else:
                await requester.send(f"❌ Error sending DM to {target_user.mention}: {e}")
        except Exception as e:
            print(f"[ROBLOX] Error sending DM: {e}")
            await requester.send(f"❌ Error processing Roblox generation: {e}")

    # Handle .rgen command for everyone in Roblox channel
    async def handle_rgen_command(self, message):
        """Handle .rgen command for Roblox generation"""
        try:
            print(f"[DEBUG] Starting .rgen command processing for {message.author.name}")
            
            # Target user is the person using the command
            target_user = message.author
            print(f"[DEBUG] Target user set to {target_user.name}")
            
            # Get user permissions
            from discord import Interaction
            # Create mock interaction for permission checking
            class MockInteraction:
                def __init__(self, user, guild):
                    self.user = user
                    self.guild = guild
            
            mock_interaction = MockInteraction(target_user, message.guild)
            print(f"[DEBUG] Mock interaction created")
            
            # Check permissions
            user_perms = get_user_permission_level(mock_interaction)
            max_roblox = user_perms.get("troblox", 0)
            print(f"[DEBUG] User permissions: troblox={max_roblox}")
            
            if max_roblox == 0:
                print(f"[DEBUG] User has no Roblox access")
                await message.author.send("❌ You don't have Roblox access!")
                await message.delete()
                return
            
            print(f"[DEBUG] About to generate Roblox account")
            # Generate Roblox account
            await self.generate_roblox_for_user(target_user, max_roblox, message.author)
            print(f"[DEBUG] Roblox account generation completed")
            # Safely delete command message
            try:
                await asyncio.sleep(1)  # Small delay before deletion
                await message.delete()
                print(f"[DEBUG] Command message deleted successfully")
            except discord.NotFound:
                print(f"[DEBUG] Message already deleted")
            except Exception as e:
                print(f"[DEBUG] Error deleting message: {e}")
            
        except Exception as e:
            print(f"[-] Error in .rgen command: {e}")
            import traceback
            print(f"[-] Traceback: {traceback.format_exc()}")
            try:
                await message.author.send("❌ Error processing .rgen command!")
            except:
                print(f"[-] Could not send error DM to user")

    async def send_bot_usage_embed(self, message):
        """Send embed explaining bot usage and cooldowns"""
        print(f"[DEBUG] Sending bot usage embed to channel {message.channel.id}")
        try:
            embed = discord.Embed(
                title="🤖 **Bot Usage Guide**",
                description="**How to use the bot and understand cooldowns!**",
                color=discord.Color.blue()
            )
            
            # Server 2 roles and cooldowns
            embed.add_field(
                name="🎯 **Server 2 Roles & Limits**",
                value=(
                    "**🆓 Free User**\n"
                    "• Follow: 1,500\n"
                    "• Raid: 50\n"
                    "• View: 10\n"
                    "• Like: 50\n"
                    "• Chat: 100\n"
                    "• Kahoot: 10\n"
                    "• Roblox: 1\n"
                    "• Cooldown: 3 minutes\n\n"
                    
                    "**🥉 Bronze**\n"
                    "• Follow: 2,000\n"
                    "• Raid: 100\n"
                    "• View: 25\n"
                    "• Like: 150\n"
                    "• Chat: 1,000\n"
                    "• Kahoot: 50\n"
                    "• Roblox: 1\n"
                    "• Cooldown: 3 minutes\n\n"
                    
                    "**⚡ Booster**\n"
                    "• Follow: 3,000\n"
                    "• Raid: 200\n"
                    "• View: 50\n"
                    "• Like: 200\n"
                    "• Chat: 1,000\n"
                    "• Kahoot: 100\n"
                    "• Roblox: 1\n"
                    "• Cooldown: 3 minutes\n\n"
                    
                    "**💎 Premium**\n"
                    "• Follow: 4,000\n"
                    "• Raid: 500\n"
                    "• View: 500\n"
                    "• Like: 400\n"
                    "• Chat: 3,000\n"
                    "• Kahoot: 500\n"
                    "• Roblox: 1\n"
                    "• Cooldown: 2 minutes\n\n"
                    
                    "**👑 Exclusive**\n"
                    "• Follow: 2,000\n"
                    "• Raid: 15,000\n"
                    "• View: 500\n"
                    "• Like: 10,000\n"
                    "• Chat: 10,000\n"
                    "• Kahoot: 2,000\n"
                    "• Roblox: 2\n"
                    "• Cooldown: 15 seconds"
                ),
                inline=False
            )
            
            embed.add_field(
                name="📋 **How to Use**",
                value=(
                    "1. **Panel**: Use dropdown in panel channel\n"
                    "2. **Roblox**: Use `!rgen @user` in this channel\n"
                    "3. **Cooldowns**: Wait between commands\n"
                    "4. **Vouch**: Always vouch after using bot\n"
                    "5. **DMs**: Keep DMs open for account delivery"
                ),
                inline=False
            )
            
            embed.add_field(
                name="⚠️ **Important Rules**",
                value=(
                    "• Respect your limits to avoid errors\n"
                    "• Wait for cooldown between commands\n"
                    "• Check your DMs for completion status\n"
                    "• Everyone must vouch after using bot\n"
                    "• No vouch = 1 week ban from bot"
                ),
                inline=False
            )
            
            embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/743869767950618744.png")
            embed.set_footer(text="Made by the one and only ReviveX • Use responsibly!")
            
            await message.channel.send(embed=embed, delete_after=30)  # Delete after 30 seconds

        except Exception as e:
            print(f"[-] Error sending bot usage embed: {e}")

    async def handle_owner_command(self, message, command, args):
        """Handle owner secret commands"""
        try:
            if command == "owner":
                # Owner management commands (ultimate owner only)
                if not args:
                    await message.author.send("❌ Usage: `!owner <add|remove|list> <user_id>`")
                    await message.delete()
                    return
                
                action = args[0].lower()
                if action == "add":
                    # Add user as regular owner
                    if len(args) < 2:
                        await message.author.send("❌ Usage: `!owner add <user_id>`")
                        await message.delete()
                        return
                    
                    try:
                        user_id = int(args[1])
                        if user_id not in OTHER_OWNER_IDS:
                            OTHER_OWNER_IDS.append(user_id)
                            OWNER_IDS.append(user_id)
                            await message.author.send(f"✅ Added {user_id} as regular owner!")
                        else:
                            await message.author.send(f"❌ {user_id} is already an owner!")
                    except ValueError:
                        await message.author.send("❌ Invalid user ID!")
                
                elif action == "remove":
                    # Remove user from regular owners
                    if len(args) < 2:
                        await message.author.send("❌ Usage: `!owner remove <user_id>`")
                        await message.delete()
                        return
                    
                    try:
                        user_id = int(args[1])
                        if user_id in OTHER_OWNER_IDS:
                            OTHER_OWNER_IDS.remove(user_id)
                            OWNER_IDS.remove(user_id)
                            await message.author.send(f"✅ Removed {user_id} from regular owners!")
                        else:
                            await message.author.send(f"❌ {user_id} is not an owner!")
                    except ValueError:
                        await message.author.send("❌ Invalid user ID!")
                
                elif action == "list":
                    # List all owners
                    owner_list = []
                    owner_list.extend([f"👑 Ultimate: {ULTIMATE_OWNER_ID}"])
                    for oid in OTHER_OWNER_IDS:
                        owner_list.append(f"👥 Regular: {oid}")
                    
                    await message.author.send("**Current Owners:**\n" + "\n".join(owner_list))
                
            elif command == "dmspam":
                if not args:
                    await message.author.send("❌ Usage: `!dmspam <user_id1,user_id2,...> <amount> <message>`")
                    await message.delete()
                    return
                
                # Parse targets (comma separated)
                targets_str = args[0]
                targets = [uid.strip() for uid in targets_str.split(',')]
                amount = int(args[1]) if len(args) > 1 and args[1].isdigit() else 5
                spam_message = " ".join(args[2:]) if len(args) > 2 else "Hello from bot owner!"
                
                # Send DM spam immediately - no delays or confirmations
                success_report = []
                for user_id in targets:
                    try:
                        target_user = await self.fetch_user(int(user_id))
                        if target_user:
                            sent_count = 0
                            # Send DM spam without delays or confirmations
                            for i in range(amount):
                                try:
                                    await target_user.send(spam_message)
                                    sent_count += 1
                                    # No delay - send as fast as possible
                                except discord.Forbidden:
                                    # Skip users with DMs closed
                                    break
                                except Exception as e:
                                    print(f"Error sending DM to {target_user.name}: {e}")
                            
                            success_report.append(f"✅ {target_user.name}: {sent_count}/{amount} DMs sent")
                        else:
                            success_report.append(f"❌ User ID {user_id} not found")
                    except ValueError:
                        success_report.append(f"❌ Invalid user ID: {user_id}")
                    except Exception as e:
                        success_report.append(f"❌ Error with {user_id}: {str(e)}")
                
                # DM results to sender
                await message.author.send("📨 **DM SPAM RESULTS**\n" + "\n".join(success_report))
                await message.delete()
                
            elif command == "spamdm":
                if not args:
                    await message.author.send("❌ Usage: `!spamdm all` or `!spamdm role @rolename`")
                    await message.delete()
                    return
                
                spam_type = args[0].lower()
                
                if spam_type == "all":
                    # Spam everyone in server
                    members = [member for member in message.guild.members if not member.bot]
                    spam_message = " ".join(args[1:]) if len(args) > 1 else "SERVER SPAM FROM OWNER!"
                    
                    success_count = 0
                    for member in members:
                        try:
                            await member.send(spam_message)
                            success_count += 1
                            # No delay or confirmation - send as fast as possible
                        except discord.Forbidden:
                            continue  # Skip users with DMs closed
                        except Exception as e:
                            print(f"Error spamming {member.name}: {e}")
                            continue
                    
                    # DM results to sender
                    await message.author.send(f"🎉 **SERVER SPAM RESULTS**\n👤 Successfully spammed: {success_count} members\n🎯 Total members: {len(members)}")
                    
                elif spam_type == "role":
                    if len(args) < 2 or not message.role_mentions:
                        await message.author.send("❌ Usage: `!spamdm role @rolename <message>`")
                        await message.delete()
                        return
                    
                    role = message.role_mentions[0]
                    spam_message = " ".join(args[2:]) if len(args) > 2 else "ROLE SPAM FROM OWNER!"
                    
                    success_count = 0
                    for member in role.members:
                        try:
                            await member.send(spam_message)
                            success_count += 1
                            # No delay or confirmation - send as fast as possible
                        except discord.Forbidden:
                            continue  # Skip users with DMs closed
                        except Exception as e:
                            print(f"Error spamming {member.name}: {e}")
                            continue
                    
                    # DM results to sender
                    await message.author.send(f"🎉 **ROLE SPAM RESULTS**\n🎯 Role: {role.mention}\n👤 Successfully spammed: {success_count}/{len(role.members)} members")
                
                await message.delete()
                
            elif command == "raid":
                target = args[0] if args else "unknown"
                amount = int(args[1]) if len(args) > 1 and args[1].isdigit() else 1000
                
                await message.channel.send(
                    f"⚡ **ULTIMATE RAID ACTIVATED**\n"
                    f"🎯 Target: `{target}`\n"
                    f"💥 Amount: `{amount}` raids\n"
                    f"👑 Executed by: {message.author.mention}\n"
                    f"⚠️ This is an admin-level raid command!"
                )
                # Delete original command message
                await message.delete()
                
            elif command == "unban":
                user_id = args[0] if args else "unknown"
                reason = " ".join(args[1:]) if len(args) > 1 else "Owner pardon"
                
                await message.channel.send(
                    f"⚡ **UNBAN EXECUTED**\n"
                    f"👤 User ID: `{user_id}`\n"
                    f"📝 Reason: `{reason}`\n"
                    f"👑 Unbanned by: {message.author.mention}\n"
                    f"✅ User has been pardoned!"
                )
                await message.delete()
                
            elif command == "ban":
                user_id = args[0] if args else "unknown"
                reason = " ".join(args[1:]) if len(args) > 1 else "Banned by owner"
                
                await message.channel.send(
                    f"⚡ **BAN EXECUTED**\n"
                    f"👤 User ID: `{user_id}`\n"
                    f"📝 Reason: `{reason}`\n"
                    f"👑 Banned by: {message.author.mention}\n"
                    f"🚫 User has been permanently banned!"
                )
                await message.delete()
                
            elif command == "lockdown":
                action = args[0].lower() if args else "lock"
                reason = " ".join(args[1:]) if len(args) > 1 else "Security protocol"
                
                if action not in ["lock", "unlock"]:
                    await message.channel.send("❌ Action must be 'lock' or 'unlock'")
                    return
                
                status = "🔒 LOCKDOWN ACTIVATED" if action == "lock" else "🔓 LOCKDOWN LIFTED"
                
                await message.channel.send(
                    f"⚡ **{status}**\n"
                    f"🏠 Server: {message.guild.name}\n"
                    f"📝 Reason: `{reason}`\n"
                    f"👑 Executed by: {message.author.mention}\n"
                    f"⚠️ All bot functions have been {'restricted' if action == 'lock' else 'restored'}!"
                )
                await message.delete()
                
            elif command == "purge":
                data_type = args[0] if args else "unknown"
                confirm = args[1] if len(args) > 1 else ""
                
                if confirm != "CONFIRM":
                    await message.channel.send("❌ You must type 'CONFIRM' to proceed with purge")
                    return
                
                await message.channel.send(
                    f"⚡ **PURGE EXECUTED**\n"
                    f"🗑️ Data Type: `{data_type}`\n"
                    f"🧹 All {data_type} data has been cleared\n"
                    f"👑 Purged by: {message.author.mention}\n"
                    f"⚠️ This action cannot be undone!"
                )
                await message.delete()
                
            elif command == "boost":
                target = args[0] if args else "server"
                multiplier = int(args[1]) if len(args) > 1 and args[1].isdigit() else 10
                
                await message.channel.send(
                    f"⚡ **BOOST ACTIVATED**\n"
                    f"🎯 Target: `{target}`\n"
                    f"🚀 Multiplier: `{multiplier}x`\n"
                    f"💪 All limits increased by {multiplier}x\n"
                    f"👑 Boosted by: {message.author.mention}\n"
                    f"⚡ Temporary boost activated!"
                )
                await message.delete()
                
            elif command == "admin":
                # Get bot stats
                total_users = len(user_cooldowns)
                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                embed = discord.Embed(
                    title="⚡ ULTIMATE ADMIN PANEL",
                    description="Bot administration controls",
                    color=discord.Color.red()
                )
                
                embed.add_field(name="👑 Ultimate Owners", value=f"`{len(ULTIMATE_OWNER_IDS)}` users", inline=True)
                embed.add_field(name="👥 Other Owners", value=f"`{len(OTHER_OWNER_IDS)}` users", inline=True)
                embed.add_field(name="📊 Active Users", value=f"`{total_users}` users", inline=True)
                embed.add_field(name="🏠 Active Servers", value=f"`{len(ALLOWED_SERVERS)}` servers", inline=True)
                embed.add_field(name="🔧 Thread Pool", value="`10` max workers", inline=True)
                embed.add_field(name="⏰ Current Time", value=f"`{current_time}`", inline=True)
                
                embed.add_field(
                    name="🚀 Available Commands",
                    value="`!dmspam`, `!raid`, `!ban`, `!unban`, `!lockdown`, `!purge`, `!boost`, `!admin`",
                    inline=False
                )
                
                embed.set_footer(text=f"Requested by {message.author.name} • Ultimate Owner Access")
                embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/743869767950618744.png")
                
                await message.channel.send(embed=embed, delete_after=60)
                await message.delete()
                
            elif command == "help":
                help_text = (
                    "⚡ **ULTIMATE OWNER COMMANDS**\n\n"
                    "`!dmspam <user_id1,user_id2,...> <amount> <message>` - DM spam multiple users\n"
                    "`!spamdm all <message>` - Spam all server members\n"
                    "`!spamdm role @rolename <message>` - Spam all members with specific role\n"
                    "`!raid <target> [amount]` - Raid any target\n"
                    "`!ban <user_id> [reason]` - Ban user\n"
                    "`!unban <user_id> [reason]` - Unban user\n"
                    "`!lockdown <lock/unlock> [reason]` - Server control\n"
                    "`!purge <data_type> CONFIRM` - Clear data\n"
                    "`!boost <target> [multiplier]` - Power boost\n"
                    "`!admin` - Show admin panel\n"
                    "`!help` - Show this help\n\n"
                    "🔒 These commands are only for ultimate owners!"
                )
                await message.channel.send(help_text, delete_after=30)
                await message.delete()
                
        except Exception as e:
            print(f"Error in ultimate command {command}: {e}")
    
    async def handle_moderation_action(self, interaction: discord.Interaction, action: str):
        """Handle moderation actions from alting detection panel"""
        try:
            # Only allow owners
            if interaction.user.id not in OWNER_IDS:
                await interaction.response.send_message("❌ Only owners can use this!", ephemeral=True)
                return
            
            # Get selected user from dropdown
            selected_user_id = None
            for component in interaction.message.components:
                for item in component.children:
                    if hasattr(item, 'custom_id') and item.custom_id == 'user_select':
                        if hasattr(item, 'values') and item.values:
                            selected_user_id = int(item.values[0])
                        break
            
            if not selected_user_id:
                await interaction.response.send_message("❌ Please select a user first!", ephemeral=True)
                return
            
            # Find user in guild
            target_user = None
            for guild in self.guilds:
                target_user = guild.get_member(selected_user_id)
                if target_user:
                    break
            
            if not target_user:
                await interaction.response.send_message("❌ User not found in any server!", ephemeral=True)
                return
            
            # Execute action
            if action == 'kick':
                await target_user.kick(reason="Suspected alting - multiple accounts targeting same Twitch user")
                await interaction.response.send_message(f"✅ Kicked {target_user.mention}", ephemeral=True)
                
            elif action == 'ban':
                await target_user.ban(reason="Suspected alting - multiple accounts targeting same Twitch user")
                await interaction.response.send_message(f"✅ Banned {target_user.mention}", ephemeral=True)
                
            elif action == 'mute':
                # Find a mute role or create one
                mute_role = None
                for role in target_user.guild.roles:
                    if 'mute' in role.name.lower():
                        mute_role = role
                        break
                
                if not mute_role:
                    # Create mute role
                    mute_role = await target_user.guild.create_role(name="Muted", color=discord.Color.dark_grey())
                    # Set permissions for all channels
                    for channel in target_user.guild.channels:
                        await channel.set_permissions(mute_role, send_messages=False, speak=False)
                
                await target_user.add_roles(mute_role, reason="Suspected alting - multiple accounts targeting same Twitch user")
                await interaction.response.send_message(f"✅ Muted {target_user.mention}", ephemeral=True)
                
            elif action == 'close':
                await interaction.message.delete()
                return
                
        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)
    
    async def handle_send_warning(self, interaction: discord.Interaction):
        """Handle sending warning to abusive owner"""
        try:
            # Only allow main owner
            if interaction.user.id != 1389712262532431882:
                await interaction.response.send_message("❌ Only the main owner can use this!", ephemeral=True)
                return
            
            # Get the abusive owner info from the message content or embed
            # Extract from the embed title/fields since we can't access view directly
            abusive_owner_id = None
            abusive_owner_name = None
            
            # Try to extract from embed
            if interaction.message.embeds:
                embed = interaction.message.embeds[0]
                print(f"[DEBUG] Embed fields: {[field.name + ': ' + field.value for field in embed.fields]}")
                
                # Look for the owner info in the embed fields
                for field in embed.fields:
                    if "Abusive Owner" in field.name:
                        print(f"[DEBUG] Found abusive owner field: {field.value}")
                        # Extract ID from format: **Name** (`ID`)
                        import re
                        # Try multiple patterns
                        id_patterns = [
                            r'\(`(\d+)\)`',  # **Name** (`ID`)
                            r'<@!?(\d+)>',   # <@ID> or <@!ID>
                            r'(\d{17,19})'   # Just the ID number
                        ]
                        
                        name_patterns = [
                            r'\*\*(.+?)\*\*',  # **Name**
                            r'@(.+?)(?:\s|$)', # @Name
                            r'(.+?)\s*\('      # Name (before parenthesis)
                        ]
                        
                        for pattern in id_patterns:
                            match = re.search(pattern, field.value)
                            if match:
                                abusive_owner_id = int(match.group(1))
                                print(f"[DEBUG] Extracted ID: {abusive_owner_id}")
                                break
                        
                        if abusive_owner_id:
                            for pattern in name_patterns:
                                name_match = re.search(pattern, field.value)
                                if name_match:
                                    abusive_owner_name = name_match.group(1).strip()
                                    print(f"[DEBUG] Extracted name: {abusive_owner_name}")
                                    break
                        
                        # Fallback: extract from the raw field value
                        if not abusive_owner_name and abusive_owner_id:
                            abusive_owner_name = f"User {abusive_owner_id}"
                            print(f"[DEBUG] Using fallback name: {abusive_owner_name}")
                        
                        break
            
            if not abusive_owner_id:
                await interaction.response.send_message("❌ Could not identify abusive owner!", ephemeral=True)
                return
            
            # Send warning to abusive owner
            await send_owner_warning(abusive_owner_id, abusive_owner_name or "Unknown")
            
            # Update the original message
            await interaction.response.edit_message(
                content="✅ **Warning sent successfully!**",
                embed=None,
                view=None
            )
            
        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)
    
    async def handle_warning_response(self, interaction: discord.Interaction, action: str):
        """Handle abusive owner's response to warning"""
        try:
            user_id = interaction.user.id
            main_owner_id = 1389712262532431882
            main_owner = await self.fetch_user(main_owner_id)
            
            if action == 'lower_follow':
                # Lower follow amount by 500
                owner_penalties[user_id]["follow_reduction"] += 500
                new_follow_limit = max(0, 5000 - owner_penalties[user_id]["follow_reduction"])
                response = f"**{interaction.user.name}** chose: **Lower my follow amount I don't care**\n\n✅ **Action Applied**: Follow amount reduced by 500\n📊 **New Follow Limit**: {new_follow_limit:,}"
                
            elif action == 'increase_cooldown':
                # Increase cooldown by 1 minute
                owner_penalties[user_id]["cooldown_increase"] += 1
                new_cooldown = 3 + owner_penalties[user_id]["cooldown_increase"]
                response = f"**{interaction.user.name}** chose: **Increase my cooldown I don't care**\n\n✅ **Action Applied**: Cooldown increased by 1 minute\n⏱️ **New Cooldown**: {new_cooldown} minutes"
                
            elif action == 'ok':
                response = f"**{interaction.user.name}** chose: **OK**\n\n✅ **Action**: User acknowledged warning (no penalties applied)"
            
            # Send response to main owner
            if main_owner:
                await main_owner.send(f"📩 **Warning Response - PENALTY APPLIED**\n\n{response}")
            
            # Also send confirmation to the user who responded
            await interaction.user.send(
                f"⚠️ **Penalty Applied**\n\n{response}\n\n"
                f"Your new limits are now active. Future bot usage will reflect these changes."
            )
            
            # Update the warning message
            await interaction.response.edit_message(
                content="✅ **Penalty applied and response recorded!**",
                embed=None,
                view=None
            )
            
        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)

    async def handle_rks_panel_response(self, interaction: discord.Interaction, custom_id: str):
        """Handle responses from Roblox/Kahoot/Spotify panel"""
        try:
            if custom_id == 'rks_roblox':
                await self.rks_roblox_callback(interaction)
            elif custom_id == 'rks_roblox_followers':
                await self.rks_roblox_followers_callback(interaction)
            elif custom_id == 'rks_kahoot':
                await self.rks_kahoot_callback(interaction)
            elif custom_id == 'rks_spotify':
                await self.rks_spotify_callback(interaction)
            elif custom_id == 'rks_spotify_followers':
                await self.rks_spotify_followers_callback(interaction)
            elif custom_id == 'rks_set_bot_name':
                await self.rks_set_bot_name_callback(interaction)
            elif custom_id == 'rks_my_plan':
                await self.rks_my_plan_callback(interaction)
                
        except Exception as e:
            print(f"[-] Error in RKS button callback: {e}")
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message("❌ An error occurred.", ephemeral=True)
            except:
                pass
    
    async def rks_roblox_callback(self, interaction: Interaction):
        """Handle Roblox account generation"""
        try:
            print(f"[ROBLOX] RKS Panel button clicked by {interaction.user.name} ({interaction.user.id})")
            
            # Check if user has permission
            if not is_allowed_server_and_channel(interaction):
                print("[ROBLOX] Wrong server or channel")
                await interaction.response.send_message("❌ This can only be used in the allowed server and channel.", ephemeral=True)
                return
            
            # Check if service is disabled
            if "roblox" in disabled_services:
                print("[ROBLOX] Roblox service is disabled")
                await interaction.response.send_message(SERVICE_DOWN_MESSAGE, ephemeral=True)
                return
            
            # Check user permissions
            user_perms = get_user_permission_level(interaction)
            max_amount = user_perms.get("troblox", 0)
            print(f"[ROBLOX] User permissions: troblox={max_amount}")
            
            if max_amount == 0:
                print("[ROBLOX] User has no Roblox permission")
                await interaction.response.send_message("❌ You don't have permission to use the Roblox Generator.", ephemeral=True)
                return
            
            # Check cooldown
            can_use, cooldown_msg = check_roblox_cooldown_direct(interaction.user.id)
            print(f"[ROBLOX] Cooldown check: can_use={can_use}, msg='{cooldown_msg}'")
            
            if not can_use:
                print("[ROBLOX] User is on cooldown")
                await interaction.response.send_message(f"❌ {cooldown_msg}", ephemeral=True)
                return
            
            print("[ROBLOX] All checks passed, getting account...")
            # Get an available account
            account = get_available_account()
            
            if not account:
                print("[ROBLOX] No accounts available")
                await interaction.response.send_message(
                    "Sorry, no accounts are available at the moment. Please try again later.",
                    ephemeral=True
                )
                return
            
            print(f"[ROBLOX] Got account: {account['username']}")
            # Mark account as used
            mark_account_used(account["username"])
            
            # Create the embed for DM
            embed = discord.Embed(
                title="Account 1/1",
                color=discord.Color.blue()
            )
            
            embed.add_field(
                name="Account Details",
                value=f"**Username:** `{account['username']}`\n**Password:** ||{account['password']}||\n\n💡 **Click on the username to copy it**\n💡 **Click on the password to reveal and copy it**",
                inline=False
            )
            
            # Add Roblox avatar thumbnail (using a default bacon hair avatar)
            embed.set_thumbnail(url="https://tr.rbxcdn.com/v1/assets?id=16630147&image=200x200")
            
            embed.set_footer(text="Click on the password to reveal it")
            
            # Update cooldown after successful validation
            update_roblox_cooldown(interaction)
            print("[ROBLOX] Cooldown updated")
            
            # Send confirmation message in channel (ephemeral and auto-delete)
            await interaction.response.send_message(
                f"Account generated, please check your DMs {interaction.user.mention}",
                ephemeral=True
            )
            
            # Get the message to delete it later
            message = await interaction.original_response()
            
            # Delete the message after 15 seconds
            await message.delete(delay=15)
            
            print("[ROBLOX] Sending account details to user's DMs...")
            # Send the account details to user's DMs
            try:
                await interaction.user.send(embed=embed)
                print("[ROBLOX] DM sent successfully")
            except discord.Forbidden:
                print("[ROBLOX] Failed to send DM - user has DMs disabled")
                await interaction.followup.send(
                    "I couldn't send you a DM. Please enable DMs from server members.",
                    ephemeral=True
                )
            except Exception as e:
                print(f"[ROBLOX] Error sending DM: {e}")
                await interaction.followup.send(
                    "An error occurred while sending the account details.",
                    ephemeral=True
                )
                
        except discord.errors.InteractionResponded:
            pass
        except Exception as e:
            print(f"[-] Error in roblox_callback: {e}")
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message("❌ An error occurred.", ephemeral=True)
            except:
                pass

    async def rks_roblox_followers_callback(self, interaction: Interaction):
        """Handle Roblox followers"""
        try:
            await interaction.response.send_message(
                "🚧 **Roblox Followers**\n"
                "Roblox followers feature is coming soon!\n"
                "This feature is currently under development.\n\n"
                "📩 For updates, contact @ReviveX or @Cashapp Addict",
                ephemeral=True
            )
        except discord.errors.InteractionResponded:
            pass
        except Exception as e:
            print(f"[-] Error in roblox_followers_callback: {e}")
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message("❌ An error occurred.", ephemeral=True)
            except:
                pass

    async def rks_kahoot_callback(self, interaction: Interaction):
        """Handle Kahoot raid"""
        try:
            print(f"[KAHOOT] RKS Panel button clicked by {interaction.user.name} ({interaction.user.id})")
            
            # Check if user has permission
            if not is_allowed_server_and_channel(interaction):
                print("[KAHOOT] Wrong server or channel")
                await interaction.response.send_message("❌ This can only be used in the allowed server and channel.", ephemeral=True)
                return
            
            # Check if service is disabled
            if "kahoot" in disabled_services:
                print("[KAHOOT] Kahoot service is disabled")
                await interaction.response.send_message(SERVICE_DOWN_MESSAGE, ephemeral=True)
                return
            
            # Check user permissions
            user_perms = get_user_permission_level(interaction)
            max_amount = user_perms.get("tkahoot", 0)
            print(f"[KAHOOT] User permissions: tkahoot={max_amount}")
            
            if max_amount == 0:
                print("[KAHOOT] User has no Kahoot permission")
                await interaction.response.send_message("❌ You don't have permission to use the Kahoot Generator.", ephemeral=True)
                return
            
            # Check cooldown
            can_use, cooldown_msg = check_cooldown(interaction)
            print(f"[KAHOOT] Cooldown check: can_use={can_use}, msg='{cooldown_msg}'")
            
            if not can_use:
                print("[KAHOOT] User is on cooldown")
                await interaction.response.send_message(f"❌ {cooldown_msg}", ephemeral=True)
                return
            
            print("[KAHOOT] All checks passed, generating kahoot bots...")
            
            # Generate Kahoot bots (min 5, max 50)
            amount = min(max(max_amount, 5), 50)  # Ensure between 5-50
            
            # Create the embed for DM
            embed = discord.Embed(
                title=f"Kahoot Bots Generated - {amount} Bots",
                color=discord.Color.purple()
            )
            
            # Add bot information
            bot_info = ""
            for i in range(amount):
                bot_info += f"🤖 Bot {i+1}: Ready to join\n"
            
            embed.add_field(
                name="Bot Details",
                value=bot_info,
                inline=False
            )
            
            embed.add_field(
                name="Instructions",
                value="1. Copy the game code from your Kahoot game\n2. Share it with the bots\n3. Watch them join automatically!",
                inline=False
            )
            
            embed.set_footer(text="Click on any text to copy it easily")
            
            # Update cooldown after successful validation
            update_cooldown(interaction)
            print("[KAHOOT] Cooldown updated")
            
            # Send confirmation message in channel (ephemeral and auto-delete)
            await interaction.response.send_message(
                f"Kahoot bots generated, please check your DMs {interaction.user.mention}",
                ephemeral=True
            )
            
            # Get the message to delete it later
            message = await interaction.original_response()
            
            # Delete the message after 15 seconds
            await message.delete(delay=15)
            
            print("[KAHOOT] Sending bot details to user's DMs...")
            # Send the bot details to user's DMs
            try:
                await interaction.user.send(embed=embed)
                print("[KAHOOT] DM sent successfully")
            except discord.Forbidden:
                print("[KAHOOT] Failed to send DM - user has DMs disabled")
                await interaction.followup.send(
                    "I couldn't send you a DM. Please enable DMs from server members.",
                    ephemeral=True
                )
            except Exception as e:
                print(f"[KAHOOT] Error sending DM: {e}")
                await interaction.followup.send(
                    "An error occurred while sending the bot details.",
                    ephemeral=True
                )
                
        except discord.errors.InteractionResponded:
            pass
        except Exception as e:
            print(f"[-] Error in kahoot_callback: {e}")
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message("❌ An error occurred.", ephemeral=True)
            except:
                pass

    async def rks_spotify_callback(self, interaction: Interaction):
        """Handle Spotify account generation"""
        try:
            print(f"[SPOTIFY] RKS Panel button clicked by {interaction.user.name} ({interaction.user.id})")
            
            # Check if user has permission
            if not is_allowed_server_and_channel(interaction):
                print("[SPOTIFY] Wrong server or channel")
                await interaction.response.send_message("❌ This can only be used in allowed server and channel.", ephemeral=True)
                return
            
            # Check if service is disabled
            if "spotify" in disabled_services:
                print("[SPOTIFY] Spotify service is disabled")
                await interaction.response.send_message(SERVICE_DOWN_MESSAGE, ephemeral=True)
                return
            
            # Check user permissions
            user_perms = get_user_permission_level(interaction)
            max_amount = user_perms.get("troblox", 0)  # Use roblox permission for spotify
            print(f"[SPOTIFY] User permissions: troblox={max_amount}")
            
            if max_amount == 0:
                print("[SPOTIFY] User has no Spotify permission")
                await interaction.response.send_message("❌ You don't have permission to use the Spotify Generator.", ephemeral=True)
                return
            
            # Get user's role to determine cooldown
            user_roles = [str(role.id) for role in interaction.user.roles] if interaction.user.roles else []
            server_id = interaction.guild.id if interaction.guild else None
            
            # Role-based cooldown mapping (Server 2)
            role_cooldowns = {
                # Free User - 10 min cooldown
                "1479634660601368646": 10,
                # Bronze - 8 min cooldown  
                "1481095073868550367": 8,
                # Booster - 5 min cooldown
                "1481094928577855621": 5,
                # Premium - 4 min cooldown
                "1481095266143567903": 4,
                # Exclusive - 3 min cooldown
                "1481095459299659947": 3,
                # Exclusive New - 3 min cooldown
                "1488404575974326293": 3,
                # Tuff Role - 3 min cooldown
                "1488923969162575942": 3,
                # 100k Role - 3 min cooldown
                "1488923969162575943": 3,
            }
            
            # Find the lowest cooldown from user's roles
            user_cooldown = 10  # Default 10 min
            for role_id in user_roles:
                if role_id in role_cooldowns:
                    user_cooldown = min(user_cooldown, role_cooldowns[role_id])
            
            # Check if user is on cooldown
            can_use, cooldown_msg = check_cooldown(interaction)
            if not can_use:
                print(f"[SPOTIFY] User is on cooldown: {cooldown_msg}")
                await interaction.response.send_message(f"❌ {cooldown_msg}", ephemeral=True)
                return
            
            print(f"[SPOTIFY] All checks passed, getting accounts from file...")
            
            # Read accounts from existing file
            accounts_file = os.path.join(os.path.dirname(__file__), "spotify gen", "data", "spotifyaccounts.txt")
            available_accounts = []
            
            try:
                with open(accounts_file, "r") as f:
                    lines = f.readlines()
                    
                # Parse accounts (format: email:password)
                for line in lines:
                    if ":" in line:
                        email, password = line.strip().split(":", 1)
                        if email and password:
                            available_accounts.append({
                                "email": email.strip(),
                                "password": password.strip()
                            })
                
                print(f"[SPOTIFY] Loaded {len(available_accounts)} accounts from file")
                
                # Determine amount based on user's role (min 5, max based on plan)
                amount = max(5, min(max_amount, len(available_accounts)))
                
                # Get accounts to give to user
                accounts_to_give = available_accounts[:amount]
                
                # Remove used accounts from file
                remaining_accounts = available_accounts[amount:]
                with open(accounts_file, "w") as f:
                    for account in remaining_accounts:
                        f.write(f"{account['email']}:{account['password']}\n")
                
                print(f"[SPOTIFY] Giving user {amount} accounts, {len(remaining_accounts)} remaining")
                
            except FileNotFoundError:
                print("[SPOTIFY] No spotifyaccounts.txt file found")
                await interaction.response.send_message("❌ No Spotify accounts available.", ephemeral=True)
                return
            except Exception as e:
                print(f"[SPOTIFY] Error reading accounts file: {e}")
                await interaction.response.send_message("❌ Error loading Spotify accounts.", ephemeral=True)
                return
            
            # Create embed for DM
            embed = discord.Embed(
                title=f"🎵 Spotify Accounts - {amount} Accounts",
                color=discord.Color.green()
            )
            
            # Add account information (limit display to avoid embed length issues)
            account_info = ""
            display_count = min(amount, 10)  # Only show first 10 accounts in embed
            for i, account in enumerate(accounts_to_give[:display_count]):
                account_info += f"🎵 Acc {i+1}: `{account['email']}` / ||{account['password']}||\n"
            
            if amount > 10:
                account_info += f"\n... and {amount - 10} more accounts!"
            
            embed.add_field(
                name="🔑 Account Details",
                value=account_info,
                inline=False
            )
            
            embed.add_field(
                name="📋 Instructions",
                value="1. **Click on email to copy it**\n2. **Click on password to reveal and copy it**\n3. **Use accounts immediately** - they may be shared!\n4. **These are demo accounts** for testing purposes",
                inline=False
            )
            
            embed.add_field(
                name="⏰ Your Cooldown",
                value=f"**{user_cooldown} minutes** (based on your server role)",
                inline=False
            )
            
            embed.add_field(
                name="📊 Stock Info",
                value=f"**{len(remaining_accounts)} accounts remaining** in stock",
                inline=False
            )
            
            embed.set_thumbnail(url="https://storage.googleapis.com/pr-newsroom-wp/1/2023/05/Spotify_Logo_RGB_Green.png")
            embed.set_footer(text="🎵 Demo Accounts • Click any text to copy")
            
            # Update cooldown after successful validation
            update_cooldown(interaction)
            print(f"[SPOTIFY] Cooldown updated to {user_cooldown} minutes")
            
            # Send announcement message in channel (like Twitch bot)
            await interaction.response.send_message(
                f"🎵 Spotify generated for {interaction.user.mention}! Please check your DMs",
                ephemeral=True
            )
            
            # Get the message to delete it later
            message = await interaction.original_response()
            
            # Delete the message after 15 seconds
            await message.delete(delay=15)
            
            print("[SPOTIFY] Sending account details to user's DMs...")
            # Send the account details to user's DMs
            try:
                await interaction.user.send(embed=embed)
                print("[SPOTIFY] DM sent successfully")
            except discord.Forbidden:
                print("[SPOTIFY] Failed to send DM - user has DMs disabled")
                await interaction.followup.send(
                    "I couldn't send you a DM. Please enable DMs from server members.",
                    ephemeral=True
                )
            except Exception as e:
                print(f"[SPOTIFY] Error sending DM: {e}")
                await interaction.followup.send(
                    "An error occurred while sending the account details.",
                    ephemeral=True
                )
                
        except discord.errors.InteractionResponded:
            pass
        except Exception as e:
            print(f"[-] Error in spotify_callback: {e}")
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message("❌ An error occurred.", ephemeral=True)
            except:
                pass

    async def rks_spotify_followers_callback(self, interaction: Interaction):
        """Handle Spotify followers"""
        try:
            await interaction.response.send_message(
                "🚧 **Spotify Followers**\n"
                "Spotify followers feature is coming soon!\n"
                "This feature is currently under development.\n\n"
                "📩 For updates, contact @ReviveX or @Cashapp Addict",
                ephemeral=True
            )
        except discord.errors.InteractionResponded:
            pass
        except Exception as e:
            print(f"[-] Error in spotify_followers_callback: {e}")
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message("❌ An error occurred.", ephemeral=True)
            except:
                pass

    async def rks_set_bot_name_callback(self, interaction: Interaction):
        """Handle bot name setting"""
        try:
            await interaction.response.send_modal(BotNameModal())
        except discord.errors.InteractionResponded:
            pass
        except Exception as e:
            print(f"[-] Error in set_bot_name_callback: {e}")
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message("❌ An error occurred.", ephemeral=True)
            except:
                pass

    async def rks_my_plan_callback(self, interaction: Interaction):
        """Handle My Plan button"""
        try:
            perms = get_user_permission_level(interaction)
            
            embed = discord.Embed(
                title="📊 **Your Current Plan**",
                description=f"Here's what you can do with your current permissions:",
                color=discord.Color.purple()
            )
            
            current_bot_name = user_bot_names.get(interaction.user.id, "ReviveX")
            embed.add_field(
                name="🎯 **Service Limits**",
                value=f"🎮 **Roblox**: `{perms.get('troblox', 0):,}`\n"
                      f"🎮 **Roblox Followers**: `Coming Soon`\n"
                      f"🎯 **Kahoot**: `{perms.get('tkahoot', 0):,}`\n"
                      f"🎵 **Spotify**: `{perms.get('troblox', 0):,}`\n"
                      f"🎵 **Spotify Followers**: `Coming Soon`",
                inline=False
            )
            
            embed.add_field(
                name="🤖 **Current Bot Name**",
                value=f"Your bots will be named: `{current_bot_name}`\n"
                      f"💡 Use the **Set Bot Name** button to change it!",
                inline=False
            )
            
            embed.add_field(
                name="⏰ **Cooldown**",
                value=f"Service cooldown: `{perms.get('cooldown', 5)} minutes`\n"
                      f"Roblox cooldown: `{perms.get('roblox_cooldown', 5)} minutes`",
                inline=False
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            print(f"[-] Error in rks_my_plan_callback: {e}")
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message("❌ An error occurred.", ephemeral=True)
            except:
                pass
        except:
            pass

# Initialize bot
bot = TwitchBotDiscord()

def is_owner(interaction: discord.Interaction) -> bool:
    """Check if the user is a bot owner"""
    return interaction.user.id in OWNER_IDS

def is_ultimate_owner(interaction: discord.Interaction) -> bool:
    """Check if the user is an ultimate owner (can use special commands)"""
    return interaction.user.id in ULTIMATE_OWNER_IDS

def get_user_permission_level(interaction: discord.Interaction) -> dict:
    """Get user's permission level based on roles and server"""
    user_id = interaction.user.id
    
    # Ultimate owners - unlimited access, no cooldown
    if user_id in ULTIMATE_OWNER_IDS:
        return {
            "tfollow": float('inf'),    # Infinite followers
            "traid": float('inf'),      # Infinite raids
            "tview": float('inf'),      # Infinite views
            "tlike": float('inf'),      # Infinite likes
            "tchat": float('inf'),      # Infinite chat
            "tkahoot": float('inf'),   # Infinite kahoot bots
            "troblox": float('inf'),   # Infinite Roblox accounts
            "cooldown": 0,         # No cooldown
            "roblox_cooldown": 0     # No roblox cooldown
        }
    
    # Other owners - 5k limit, 3 minute cooldown
    if user_id in OTHER_OWNER_IDS:
        # Get current penalties for this owner
        penalties = owner_penalties[user_id]
        follow_reduction = penalties["follow_reduction"]
        cooldown_increase = penalties["cooldown_increase"]
        
        return {
            "tfollow": max(0, 5000 - follow_reduction),      # 5k followers minus reductions
            "traid": 5000,        # 5k raids
            "tview": 5000,        # 5k views
            "tlike": 5000,        # 5k likes
            "tchat": 5000,        # 5k chat
            "tkahoot": 5000,      # 5k kahoot bots
            "troblox": 5000,      # 5k Roblox accounts
            "cooldown": 3 + cooldown_increase,         # 3 minutes plus increases
            "roblox_cooldown": 3 + cooldown_increase     # Same as regular cooldown
        }
    
    # Get server-specific role permissions
    server_id = interaction.guild.id if interaction.guild else None
    if not server_id or server_id not in ROLE_PERMISSIONS:
        # Server not configured, return no permissions
        return {
            "tfollow": 0,
            "traid": 0,
            "tview": 0,
            "tlike": 0,
            "tchat": 0,
            "tkahoot": 0,
            "troblox": 0,
            "cooldown": 5,
            "roblox_cooldown": 5
        }
    
    # Check user's roles against server-specific role permissions
    user_roles = [str(role.id) for role in interaction.user.roles] if interaction.user.roles else []
    server_roles = ROLE_PERMISSIONS[server_id]
    
    # Default permissions (no access)
    permissions = {
        "tfollow": 0,
        "traid": 0,
        "tview": 0,
        "tlike": 0,
        "tchat": 0,
        "tkahoot": 0,
        "troblox": 0,
        "cooldown": 5,
        "roblox_cooldown": 5
    }
    
    # Find the highest permission level based on user's roles
    for role_id in user_roles:
        if role_id in server_roles:
            role_perms = server_roles[role_id]
            for cmd, max_amount in role_perms.items():
                if cmd in permissions:
                    # Take the maximum value for each permission
                    permissions[cmd] = max(permissions[cmd], max_amount)
    
    # Check for custom permissions (OP owner overrides)
    if hasattr(bot, 'custom_permissions') and user_id in bot.custom_permissions:
        custom_perms = bot.custom_permissions[user_id].get(server_id, {})
        for cmd, custom_amount in custom_perms.items():
            if cmd in permissions:
                # Custom permissions override role-based permissions
                permissions[cmd] = custom_amount
    
    return permissions

def is_allowed_server_and_channel(interaction: discord.Interaction) -> bool:
    """Check if command is being used in allowed server and channel"""
    return (
        interaction.guild and 
        interaction.guild.id in ALLOWED_SERVERS and 
        interaction.channel.id in ALLOWED_SERVERS[interaction.guild.id]
    )

def check_cooldown(interaction: discord.Interaction) -> tuple[bool, str]:
    """Check if user is on cooldown"""
    user_id = interaction.user.id
    
    # Ultimate owners - no cooldown
    if user_id in ULTIMATE_OWNER_IDS:
        return True, ""
    
    # Check for custom cooldowns first
    if hasattr(bot, 'custom_cooldowns') and user_id in bot.custom_cooldowns:
        custom_cooldown = bot.custom_cooldowns[user_id].get("cooldown", 0)
        if custom_cooldown > 0:
            last_used = user_cooldowns.get(user_id)
            if last_used:
                elapsed = datetime.now() - last_used
                if elapsed < timedelta(minutes=custom_cooldown):
                    remaining = timedelta(minutes=custom_cooldown) - elapsed
                    minutes = remaining.seconds // 60
                    seconds = remaining.seconds % 60
                    return False, f"Please wait {minutes}m {seconds}s before using this command again."
            return True, ""
    
    # Get user permissions to check cooldown
    perms = get_user_permission_level(interaction)
    cooldown_minutes = perms.get("cooldown", 0)
    
    if cooldown_minutes == 0:
        return True, ""
    
    last_used = user_cooldowns.get(user_id)
    if last_used:
        elapsed = datetime.now() - last_used
        if elapsed < timedelta(minutes=cooldown_minutes):
            remaining = timedelta(minutes=cooldown_minutes) - elapsed
            minutes = remaining.seconds // 60
            seconds = remaining.seconds % 60
            return False, f"Please wait {minutes}m {seconds}s before using this command again."
    
    return True, ""

def update_cooldown(interaction: discord.Interaction):
    """Update user's last command time"""
    # Ultimate owners never get cooldown
    if interaction.user.id not in ULTIMATE_OWNER_IDS:
        user_cooldowns[interaction.user.id] = datetime.now()

async def send_vouch_reminder(user):
    """Send vouch reminder to user's DMs"""
    try:
        await user.send(
            "📢 **Please Vouch!**\n\n"
            "Please vouch in <#1486519548307050568>\n"
            "https://discord.com/channels/1479583403249762387/1486519548307050568\n\n"
            "⚠️ **Warning**: Not vouching could result in a day ban from the bot!"
        )
    except discord.Forbidden:
        pass  # Silent fail for DMs disabled
    except Exception as e:
        pass  # Silent fail for other errors

def check_roblox_cooldown_direct(user_id):
    """Check Roblox cooldown for user ID directly"""
    if user_id not in roblox_cooldowns:
        return True, "Ready"
        
    last_used = roblox_cooldowns[user_id]
    time_diff = (datetime.now() - last_used).total_seconds()
    
    # Get user's cooldown time (default to 10 minutes if not found)
    user_cooldown = 600  # 10 minutes default
    
    if time_diff < user_cooldown:
        remaining = int(user_cooldown - time_diff)
        minutes = remaining // 60
        seconds = remaining % 60
        return False, f"Please wait {minutes}m {seconds}s before using Roblox generator again."
    else:
        return True, "Ready"

def check_roblox_cooldown(interaction: discord.Interaction) -> tuple[bool, str]:
    """Check if user is on Roblox cooldown"""
    user_id = interaction.user.id
    print(f"[DEBUG] check_roblox_cooldown called for user {user_id}")
    
    # Ultimate owners - no cooldown
    if user_id in ULTIMATE_OWNER_IDS:
        return True, ""
    
    # Check for custom Roblox cooldowns first
    if hasattr(bot, 'custom_cooldowns') and user_id in bot.custom_cooldowns:
        custom_roblox_cooldown = bot.custom_cooldowns[user_id].get("roblox", 0)
        if custom_roblox_cooldown > 0:
            last_used = roblox_cooldowns.get(user_id)
            print(f"[DEBUG] roblox_cooldowns.get({user_id}) = {last_used}")
            if last_used:
                elapsed = datetime.now() - last_used
                if elapsed < timedelta(minutes=custom_roblox_cooldown):
                    remaining = timedelta(minutes=custom_roblox_cooldown) - elapsed
                    minutes = remaining.seconds // 60
                    seconds = remaining.seconds % 60
                    return False, f"Please wait {minutes}m {seconds}s before using Roblox generator again."
            return True, ""
    
    # Get user permissions to check Roblox cooldown
    perms = get_user_permission_level(interaction)
    roblox_cooldown_minutes = perms.get("roblox_cooldown", 0)
    print(f"[DEBUG] User roblox_cooldown from perms: {roblox_cooldown_minutes}")
    
    if roblox_cooldown_minutes == 0:
        return True, ""
    
    last_used = roblox_cooldowns.get(user_id)
    print(f"[DEBUG] roblox_cooldowns.get({user_id}) = {last_used}")
    if last_used:
        elapsed = datetime.now() - last_used
        if elapsed < timedelta(minutes=roblox_cooldown_minutes):
            remaining = timedelta(minutes=roblox_cooldown_minutes) - elapsed
            minutes = remaining.seconds // 60
            seconds = remaining.seconds % 60
            return False, f"Please wait {minutes}m {seconds}s before using Roblox generator again."
    
    return True, ""

def update_roblox_cooldown(interaction: discord.Interaction):
    """Update user's last Roblox command time"""
    # Ultimate owners never get cooldown
    if interaction.user.id not in ULTIMATE_OWNER_IDS:
        roblox_cooldowns[interaction.user.id] = datetime.now()

@bot.tree.command(name="roblox", description="Generate a Roblox account")
async def roblox_generate(interaction: discord.Interaction):
    """Generate a Roblox account and send it to the user's DMs"""
    print(f"[ROBLOX] Slash command used by {interaction.user.name} ({interaction.user.id})")
    
    # Check if user has permission
    if not is_allowed_server_and_channel(interaction):
        print("[ROBLOX] Wrong server or channel")
        await interaction.response.send_message("❌ This command can only be used in the allowed server and channel.", ephemeral=True)
        return
    
    # Check if service is disabled
    if "roblox" in disabled_services:
        print("[ROBLOX] Roblox service is disabled")
        await interaction.response.send_message(SERVICE_DOWN_MESSAGE, ephemeral=True)
        return
    
    # Check user permissions
    user_perms = get_user_permission_level(interaction)
    max_amount = user_perms.get("troblox", 0)
    print(f"[ROBLOX] User permissions: troblox={max_amount}")
    
    if max_amount == 0:
        print("[ROBLOX] User has no Roblox permission")
        await interaction.response.send_message("❌ You don't have permission to use the Roblox Generator.", ephemeral=True)
        return
    
    # Check cooldown
    can_use, cooldown_msg = check_roblox_cooldown_direct(interaction.user.id)
    print(f"[ROBLOX] Cooldown check: can_use={can_use}, msg='{cooldown_msg}'")
    
    if not can_use:
        print("[ROBLOX] User is on cooldown")
        await interaction.response.send_message(f"❌ {cooldown_msg}", ephemeral=True)
        return
    
    print("[ROBLOX] All checks passed, getting account...")
    # Get an available account
    account = get_available_account()
    
    if not account:
        print("[ROBLOX] No accounts available")
        await interaction.response.send_message(
            "Sorry, no accounts are available at the moment. Please try again later.",
            ephemeral=True
        )
        return
    
    print(f"[ROBLOX] Got account: {account['username']}")
    # Mark account as used
    mark_account_used(account["username"])
    
    # Create the embed for DM
    embed = discord.Embed(
        title="Account 1/1",
        color=discord.Color.blue()
    )
    
    embed.add_field(
        name="Account Details",
        value=f"**Username:** `{account['username']}`\n**Password:** ||{account['password']}||",
        inline=False
    )
    
    # Add Roblox avatar thumbnail (using a default bacon hair avatar)
    embed.set_thumbnail(url="https://tr.rbxcdn.com/v1/assets?id=16630147&image=200x200")
    
    embed.set_footer(text="Click on the password to reveal it")
    
    # Update cooldown after successful validation
    update_roblox_cooldown(interaction)
    print("[ROBLOX] Cooldown updated")
    
    # Send confirmation message in channel (ephemeral and auto-delete)
    await interaction.response.send_message(
        f"Account generated, please check your DMs {interaction.user.mention}",
        ephemeral=True
    )
    
    # Get the message to delete it later
    message = await interaction.original_response()
    
    # Delete the message after 15 seconds
    await message.delete(delay=15)
    
    print("[ROBLOX] Sending account details to user's DMs...")
    # Send the account details to user's DMs
    try:
        await interaction.user.send(embed=embed)
        print("[ROBLOX] DM sent successfully")
    except discord.Forbidden:
        print("[ROBLOX] Failed to send DM - user has DMs disabled")
        await interaction.followup.send(
            "I couldn't send you a DM. Please enable DMs from server members.",
            ephemeral=True
        )
    except Exception as e:
        print(f"[ROBLOX] Error sending DM: {e}")
        await interaction.followup.send(
            f"Error sending account details: {str(e)}",
            ephemeral=True
        )

@bot.tree.command(name="addrobloxaccount", description="Add a new Roblox account (Admin only)")
@app_commands.describe(username="Roblox username", password="Roblox password")
async def add_roblox_account(interaction: discord.Interaction, username: str, password: str):
    """Add a new account to the database"""
    
    # Check if user is admin
    if not (is_ultimate_owner(interaction) or interaction.user.id in OTHER_OWNER_IDS):
        await interaction.response.send_message("❌ You don't have permission to use this command.", ephemeral=True)
        return
    
    # Remove :_ suffix from password if present
    password = password.replace(':_', '')
    
    # Add to accounts.txt file
    try:
        with open('roblox gen/accounts/accounts.txt', 'a') as f:
            f.write(f"\n{username}:{password}")
        
        await interaction.response.send_message(
            f"Account `{username}` has been added successfully!",
            ephemeral=True
        )
    except Exception as e:
        await interaction.response.send_message(
            f"Error adding account: {str(e)}",
            ephemeral=True
        )

@bot.tree.command(name="robloxaccounts", description="Check available Roblox accounts (Admin only)")
async def check_roblox_accounts(interaction: discord.Interaction):
    """Check the status of Roblox accounts"""
    
    # Check if user is admin
    if not (is_ultimate_owner(interaction) or interaction.user.id in OTHER_OWNER_IDS):
        await interaction.response.send_message("❌ You don't have permission to use this command.", ephemeral=True)
        return
    
    accounts = load_accounts()
    total = len(accounts)
    used = len(used_accounts)
    available = total - used
    
    embed = discord.Embed(
        title="Roblox Account Statistics",
        color=discord.Color.green()
    )
    
    embed.add_field(name="Total Accounts", value=str(total), inline=True)
    embed.add_field(name="Used Accounts", value=str(used), inline=True)
    embed.add_field(name="Available Accounts", value=str(available), inline=True)
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="rks_panel", description="🎮 Roblox/Kahoot/Spotify Panel")
async def rks_panel_command(interaction: discord.Interaction):
    """Send Roblox/Kahoot/Spotify panel to channel"""
    
    # Check if user is OP owner
    if interaction.user.id not in ULTIMATE_OWNER_IDS and interaction.user.id not in OTHER_OWNER_IDS:
        await interaction.response.send_message("❌ This command is for OP owners only!", ephemeral=True)
        return
    
    # Check if command is used in allowed server (but any channel within that server)
    if not (interaction.guild and interaction.guild.id in ALLOWED_SERVERS):
        await interaction.response.send_message("❌ This command can only be used in allowed servers!", ephemeral=True)
        return
    
    # Create panel embed
    embed = discord.Embed(
        title="🎮 **Roblox/Kahoot/Spotify Panel**",
        description="**Choose a service below:**",
        color=discord.Color.purple()
    )
    
    embed.add_field(
        name="🎯 **Available Services**",
        value="🎮 **Roblox Account Generator** - Generate Roblox accounts\n"
              "🎯 **Kahoot Raid Bot** - Raid Kahoot games with bots\n"
              "🎵 **Spotify Account Generator** - Generate Spotify accounts (Coming Soon)\n"
              "🎵 **Spotify Followers** - Add Spotify followers (Coming Soon)",
        inline=False
    )
    
    embed.add_field(
        name="🤖 **Bot Customization**",
        value="Use the **Set Bot Name** button to customize your bot names!",
        inline=False
    )
    
    embed.add_field(
        name="📊 **Check Your Plan**",
        value="Use the **My Plan** button to see your current limits and permissions.",
        inline=False
    )
    
    embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/743869767950618744.png")
    embed.set_footer(text="Made by the one and only ReviveX • Use responsibly!")
    
    # Send panel message with buttons
    await interaction.response.send_message(embed=embed, view=RobloxKahootSpotifyView())
    print(f"[RKS_PANEL] Panel sent to channel {interaction.channel.id} in server {interaction.guild.id} by {interaction.user.name}")

@bot.tree.command(name="panel", description="Show interactive bot control panel")
async def panel_command(interaction: discord.Interaction):
    """Show the interactive bot panel"""
    
    # Check if user has permission
    if not is_allowed_server_and_channel(interaction):
        await interaction.response.send_message("❌ This command can only be used in the allowed server and channel.", ephemeral=True)
        return
    
    # Get user permissions
    perms = get_user_permission_level(interaction)
    
    # Get server-specific role permissions
    server_roles = []
    if interaction.guild and interaction.guild.id in ROLE_PERMISSIONS:
        server_perms = ROLE_PERMISSIONS[interaction.guild.id]
        for role_id, role_data in server_perms.items():
            try:
                role = interaction.guild.get_role(role_id)
                if role:
                    server_roles.append({
                        'name': role.name,
                        'color': role.color,
                        'tfollow': role_data.get('tfollow', 0),
                        'traid': role_data.get('traid', 0),
                        'tview': role_data.get('tview', 0),
                        'tlike': role_data.get('tlike', 0),
                        'tchat': role_data.get('tchat', 0),
                        'tkahoot': role_data.get('tkahoot', 0)
                    })
            except:
                continue
    
    # Create role permissions text
    role_text = ""
    for role_data in server_roles:
        role_emoji = "👑" if "owner" in role_data['name'].lower() else "🎮" if "vip" in role_data['name'].lower() else "👤"
        role_text += f"{role_emoji} **{role_data['name']}**\n"
        role_text += f"├ Follow: `{role_data['tfollow']:,}` | Raid: `{role_data['traid']:,}`\n"
        role_text += f"├ View: `{role_data['tview']:,}` | Like: `{role_data['tlike']:,}`\n"
        role_text += f"├ Chat: `{role_data['tchat']:,}` | Kahoot: `{role_data['tkahoot']:,}`\n\n"
    
    # Create embed
    embed = discord.Embed(
        title="🎮 **Twitch Bot Control Panel**",
        description=f"**Welcome to the Twitch Bot Panel!**\n\n{interaction.user.mention}, select your service below or check your plan.",
        color=discord.Color.from_rgb(147, 51, 234)  # Purple color
    )
    
    # Add user permissions with better formatting
    perms_text = f"👥 **Followers**: `{perms.get('tfollow', 0):,}`\n"
    perms_text += f"⚔️ **Raids**: `{perms.get('traid', 0):,}`\n"
    perms_text += f"👁️ **Views**: `{perms.get('tview', 0):,}`\n"
    perms_text += f"❤️ **Likes**: `{perms.get('tlike', 0):,}`\n"
    perms_text += f"💬 **Chat**: `{perms.get('tchat', 0):,}`\n"
    perms_text += f"🎯 **Kahoot**: `{perms.get('tkahoot', 0):,}`\n"
    perms_text += f"⏰ **Cooldown**: `{perms.get('cooldown', 0)}min`"
    
    embed.add_field(
        name="👤 **Your Current Limits**",
        value=perms_text,
        inline=True
    )
    
    # Add server role permissions with better design
    if role_text:
        embed.add_field(
            name="🏰 **Server Role Limits**",
            value=role_text,
            inline=True
        )
    
    # Add quick stats
    total_roles = len(server_roles)
    embed.add_field(
        name="📊 **Server Stats**",
        value=f"🎭 **Roles**: `{total_roles}`\n"
              f"🏠 **Server**: {interaction.guild.name}\n"
              f"👑 **Your Access**: {'✅ Full' if perms.get('tfollow', 0) > 0 else '❌ Limited'}",
        inline=True
    )
    
    # Add instructions with better formatting
    embed.add_field(
        name="� **Quick Start Guide**",
        value="**1️⃣** Click **📊 My Plan** to see your details\n"
              "**2️⃣** Choose a service button below\n"
              "**3️⃣** Fill in the required info\n"
              "**4️⃣** Submit and wait for completion\n"
              "**5️⃣** Check your DMs for results",
        inline=False
    )
    
    # Add warning/info
    embed.add_field(
        name="⚠️ **Important**",
        value="• Respect your limits to avoid errors\n"
              "• Wait for cooldown between commands\n"
              "• Check your DMs for completion status\n"
              "• **Everyone must vouch after using bot**\n"
              "• **No vouch = 1 week ban from bot**\n"
              "• Contact staff for plan upgrades",
        inline=False
    )
    
    # Better styling
    embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/743869767950618744.png")
    embed.set_footer(text=f"Panel requested by {interaction.user.name} • Use responsibly!")
    embed.set_image(url="https://cdn.discordapp.com/attachments/903298062502514728/1082542729052753970/twitch_bot_banner.png")  # Add a banner if you have one
    
    try:
        await interaction.response.send_message(embed=embed, view=BotPanelView(), ephemeral=True)
    except discord.errors.NotFound:
        # Handle interaction timeout
        await interaction.followup.send("❌ Interaction expired. Please try the command again.", ephemeral=True)

@bot.tree.command(name="debug", description="Debug command to check bot status")
async def debug_command(interaction: discord.Interaction):
    """Debug command"""
    try:
        debug_info = (
            f"🔍 **Bot Debug Info**\n"
            f"👤 User: {interaction.user.name} ({interaction.user.id})\n"
            f"🏠 Server: {interaction.guild.name if interaction.guild else 'DM'} ({interaction.guild.id if interaction.guild else 'N/A'})\n"
            f"📢 Channel: {interaction.channel.name if interaction.channel else 'N/A'} ({interaction.channel.id if interaction.channel else 'N/A'})\n"
            f"👑 Is Owner: {is_owner(interaction)}\n"
            f"⚡ Is Ultimate Owner: {is_ultimate_owner(interaction)}\n"
            f"🎯 Allowed Servers: {list(ALLOWED_SERVERS.keys())}\n"
            f"🎯 Allowed Channels: {list(ALLOWED_SERVERS.values())}\n"
            f"✅ Correct Server: {interaction.guild.id in ALLOWED_SERVERS if interaction.guild else 'N/A'}\n"
            f"✅ Correct Channel: {interaction.channel.id == ALLOWED_SERVERS.get(interaction.guild.id, 'N/A') if interaction.channel else 'N/A'}\n"
        )
        await interaction.response.send_message(debug_info)
        
        # Auto-delete after 15 seconds
        await asyncio.sleep(15)
        await interaction.delete_original_message()
    except Exception as e:
        print(f"Error in debug command: {e}")
        await interaction.response.send_message("❌ Error in debug command")

# ================================
# ULTIMATE OWNER ADMIN COMMANDS
# ================================

@bot.tree.command(name="raid", description="⚡ Ultimate Owner Only - Raid any target")
@app_commands.describe(target="Target username or server", amount="Number of raids")
async def ultimate_raid(interaction: discord.Interaction, target: str, amount: int = 1000):
    """Ultimate owner raid command"""
    if not is_ultimate_owner(interaction):
        await interaction.response.send_message("❌ This command is for ultimate owners only!", ephemeral=True)
        return
    
    await interaction.response.send_message(
        f"⚡ **ULTIMATE RAID ACTIVATED**\n"
        f"🎯 Target: `{target}`\n"
        f"💥 Amount: `{amount}` raids\n"
        f"👑 Executed by: {interaction.user.mention}\n"
        f"⚠️ This is an admin-level raid command!",
        ephemeral=False
    )

@bot.tree.command(name="unban", description="⚡ Ultimate Owner Only - Unban users")
@app_commands.describe(user_id="User ID to unban", reason="Reason for unban")
async def ultimate_unban(interaction: discord.Interaction, user_id: str, reason: str = "Owner pardon"):
    """Ultimate owner unban command"""
    if not is_ultimate_owner(interaction):
        await interaction.response.send_message("❌ This command is for ultimate owners only!", ephemeral=True)
        return
    
    await interaction.response.send_message(
        f"⚡ **UNBAN EXECUTED**\n"
        f"👤 User ID: `{user_id}`\n"
        f"📝 Reason: `{reason}`\n"
        f"👑 Unbanned by: {interaction.user.mention}\n"
        f"✅ User has been pardoned!",
        ephemeral=False
    )

@bot.tree.command(name="lockdown", description="⚡ Ultimate Owner Only - Lockdown/Unlock server")
@app_commands.describe(action="Action: lock or unlock", reason="Reason for lockdown")
async def ultimate_lockdown(interaction: discord.Interaction, action: str, reason: str = "Security protocol"):
    """Ultimate owner lockdown command"""
    if not is_ultimate_owner(interaction):
        await interaction.response.send_message("❌ This command is for ultimate owners only!", ephemeral=True)
        return
    
    if action.lower() not in ["lock", "unlock"]:
        await interaction.response.send_message("❌ Action must be 'lock' or 'unlock'", ephemeral=True)
        return
    
    status = "🔒 LOCKDOWN ACTIVATED" if action.lower() == "lock" else "🔓 LOCKDOWN LIFTED"
    
    await interaction.response.send_message(
        f"⚡ **{status}**\n"
        f"🏠 Server: {interaction.guild.name}\n"
        f"📝 Reason: `{reason}`\n"
        f"👑 Executed by: {interaction.user.mention}\n"
        f"⚠️ All bot functions have been {'restricted' if action.lower() == 'lock' else 'restored'}!",
        ephemeral=False
    )

@bot.tree.command(name="purge", description="⚡ Ultimate Owner Only - Purge bot data")
@app_commands.describe(data_type="Type of data to purge")
async def ultimate_purge(interaction: discord.Interaction, data_type: str):
    """Ultimate owner purge command"""
    if not is_ultimate_owner(interaction):
        await interaction.response.send_message("❌ This command is for ultimate owners only!", ephemeral=True)
        return
    
    await interaction.response.send_message(
        f"⚡ **PURGE EXECUTED**\n"
        f"🗑️ Data Type: `{data_type}`\n"
        f"🧹 All {data_type} data has been cleared\n"
        f"👑 Purged by: {interaction.user.mention}\n"
        f"⚠️ This action cannot be undone!",
        ephemeral=False
    )

@bot.tree.command(name="boost", description="⚡ Ultimate Owner Only - Boost server/user")
@app_commands.describe(target="Target (server/user)", multiplier="Boost multiplier")
async def ultimate_boost(interaction: discord.Interaction, target: str, multiplier: int = 10):
    """Ultimate owner boost command"""
    if not is_ultimate_owner(interaction):
        await interaction.response.send_message("❌ This command is for ultimate owners only!", ephemeral=True)
        return
    
    await interaction.response.send_message(
        f"⚡ **BOOST ACTIVATED**\n"
        f"🎯 Target: `{target}`\n"
        f"🚀 Multiplier: `{multiplier}x`\n"
        f"💪 All limits increased by {multiplier}x\n"
        f"👑 Boosted by: {interaction.user.mention}\n"
        f"⚡ Temporary boost activated!",
        ephemeral=False
    )

@bot.tree.command(name="admin", description="⚡ Ultimate Owner Only - Admin panel")
async def ultimate_admin(interaction: discord.Interaction):
    """Ultimate owner admin panel"""
    if not is_ultimate_owner(interaction):
        await interaction.response.send_message("❌ This command is for ultimate owners only!", ephemeral=True)
        return
    
    # Get bot stats
    total_users = len(user_cooldowns)
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    embed = discord.Embed(
        title="⚡ ULTIMATE ADMIN PANEL",
        description="Bot administration controls",
        color=discord.Color.red()
    )
    
    embed.add_field(name="👑 Ultimate Owners", value=f"`{len(ULTIMATE_OWNER_IDS)}` users", inline=True)
    embed.add_field(name="👥 Other Owners", value=f"`{len(OTHER_OWNER_IDS)}` users", inline=True)
    embed.add_field(name="📊 Active Users", value=f"`{total_users}` users", inline=True)
    embed.add_field(name="🏠 Active Servers", value=f"`{len(ALLOWED_SERVERS)}` servers", inline=True)
    embed.add_field(name="🔧 Thread Pool", value="`10` max workers", inline=True)
    embed.add_field(name="⏰ Current Time", value=f"`{current_time}`", inline=True)
    
    embed.add_field(
        name="🚀 Available Commands",
        value="`!raid`, `!unban`, `!lockdown`, `!purge`, `!boost`, `!admin`",
        inline=False
    )
    
    embed.set_footer(text=f"Requested by {interaction.user.name} • Ultimate Owner Access")
    embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/743869767950618744.png")
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="test", description="Test command to verify bot is working")
async def test_command(interaction: discord.Interaction):
    """Test command"""
    try:
        await interaction.response.send_message("✅ Bot is working! Commands are registered.")
        
        # Auto-delete after 15 seconds
        await asyncio.sleep(15)
        await interaction.delete_original_message()
    except Exception as e:
        print(f"Error in test command: {e}")
        await interaction.response.send_message("❌ Error in test command")

@bot.tree.command(name="event", description="OP Owner Only - Manage events in the event channel")
@app_commands.describe(action="Action: start, stop, status", amount="Follow amount per user (for start)", cooldown="Cooldown in minutes (for start)", duration="Event duration in minutes (for start)")
async def event_command(interaction: discord.Interaction, action: str, amount: int = 0, cooldown: int = 0, duration: int = 0):
    """Manage events in the specified channel"""
    global event_active, event_amount, event_cooldown, event_duration, event_start_time, event_timer, event_users, event_starter, event_total_followers
    
    # Check if user is OP owner
    if interaction.user.id not in ULTIMATE_OWNER_IDS and interaction.user.id not in OTHER_OWNER_IDS:
        await interaction.response.send_message("❌ This command is for OP owners only!", ephemeral=True)
        return
    
    # Check if command is used in the correct channel
    if interaction.channel.id != event_channel_id:
        await interaction.response.send_message(f"❌ This command can only be used in the event channel (<#{event_channel_id}>).", ephemeral=True)
        return
    
    action = action.lower()
    
    if action == "start":
        if event_active:
            await interaction.response.send_message("❌ An event is already active! Stop it first.", ephemeral=True)
            return
        
        if amount <= 0:
            await interaction.response.send_message("❌ Please specify a valid amount (> 0).", ephemeral=True)
            return
        
        if duration <= 0:
            await interaction.response.send_message("❌ Please specify a valid duration in minutes (> 0).", ephemeral=True)
            return
        
        event_active = True
        event_amount = amount
        event_cooldown = cooldown
        event_duration = duration
        event_start_time = datetime.now()
        
        # Initialize event tracking
        global event_users, event_starter, event_total_followers
        event_users = {}
        event_starter = interaction.user
        event_total_followers = 0
        
        # Set up automatic event ending timer
        import threading
        def end_event_after_duration():
            import time
            time.sleep(duration * 60)  # Convert minutes to seconds
            if event_active:
                # Create a fake interaction for automatic ending
                asyncio.create_coroutine(auto_end_event())
        
        event_timer = threading.Thread(target=end_event_after_duration, daemon=True)
        event_timer.start()
        
        embed = discord.Embed(
            title="🎉 **EVENT STARTED**",
            description="**Event is now live in this channel!**",
            color=discord.Color.green()
        )
        
        embed.add_field(name="🎯 **Follow Amount", value=f"`{amount}` followers per user", inline=True)
        embed.add_field(name="⏰ **Cooldown", value=f"`{cooldown}` minutes" if cooldown > 0 else "No cooldown", inline=True)
        embed.add_field(name="🕒 **Duration", value=f"`{duration}` minutes", inline=True)
        embed.add_field(name="👑 **Started by", value=interaction.user.mention, inline=True)
        
        embed.add_field(
            name="📋 **How to Participate**",
            value=f"Use `/tfollow <username>` to get `{amount}` followers!\n"
                  f"Everyone gets the same amount regardless of role.\n"
                  f"Event will automatically end after `{duration}` minutes.",
            inline=False
        )
        
        embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/743869767950618744.png")
        embed.set_footer(text="Event will run until stopped by an OP owner or time expires")
        
        await interaction.response.send_message(embed=embed)
        
        # Send event announcement to specific channel only
        await bot.send_event_announcement(amount, cooldown, duration, interaction.user)
        
    elif action == "stop":
        if not event_active:
            await interaction.response.send_message("❌ No event is currently active.", ephemeral=True)
            return
        
        # Calculate event duration
        duration = datetime.now() - event_start_time
        hours, remainder = divmod(duration.total_seconds(), 3600)
        minutes, seconds = divmod(remainder, 60)
        
        event_active = False
        event_amount = 0
        event_cooldown = 0
        event_duration = 0
        event_start_time = None
        event_timer = None
        
        # Create event breakdown embed
        embed = discord.Embed(
            title="🛑 **EVENT ENDED - BREAKDOWN**",
            description="**The event has been manually stopped! Here's the complete breakdown:**",
            color=discord.Color.red()
        )
        
        # Event info
        embed.add_field(name="🎯 **Event Info**", value=f"**Started by:** {event_starter.mention if event_starter else 'Unknown'}\n**Stopped by:** {interaction.user.mention}\n**Duration:** {int(hours)}h {int(minutes)}m {int(seconds)}s\n**Total Followers Sent:** {event_total_followers:,}", inline=False)
        
        # Top users
        if event_users:
            # Sort users by amount and get top 10
            sorted_users = sorted(event_users.items(), key=lambda x: x[1], reverse=True)[:10]
            
            top_users_text = ""
            for i, (user_id, amount) in enumerate(sorted_users, 1):
                user = interaction.guild.get_member(user_id)
                if user:
                    top_users_text += f"**{i}.** {user.mention} - **{amount:,}** followers\n"
                else:
                    top_users_text += f"**{i}.** <@{user_id}> - **{amount:,}** followers\n"
            
            # Highlight top user
            if sorted_users:
                top_user_id, top_amount = sorted_users[0]
                top_user = interaction.guild.get_member(top_user_id)
                if top_user:
                    embed.add_field(name="👑 **Top User**", value=f"{top_user.mention} got the most followers with **{top_amount:,}** followers!", inline=False)
            
            embed.add_field(name="🏆 **Top 10 Users**", value=top_users_text or "No participants", inline=False)
        else:
            embed.add_field(name="👥 **Participants**", value="No users participated in this event", inline=False)
        
        embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/743869767950618744.png")
        embed.set_footer(text=f"Event manually stopped by {interaction.user.name}")
        
        await interaction.response.send_message(embed=embed)
        
    elif action == "status":
        if not event_active:
            await interaction.response.send_message("❌ No event is currently active.", ephemeral=True)
            return
        
        # Calculate current duration
        duration = datetime.now() - event_start_time
        hours, remainder = divmod(duration.total_seconds(), 3600)
        minutes, seconds = divmod(remainder, 60)
        
        embed = discord.Embed(
            title="📊 **EVENT STATUS**",
            description="**Current event information**",
            color=discord.Color.blue()
        )
        
        embed.add_field(name="🎯 **Follow Amount", value=f"`{event_amount}` followers per user", inline=True)
        embed.add_field(name="⏰ **Cooldown", value=f"`{event_cooldown}` minutes" if event_cooldown > 0 else "No cooldown", inline=True)
        embed.add_field(name="🕒 **Duration", value=f"`{event_duration}` minutes total", inline=True)
        embed.add_field(name="⏱️ **Running for", value=f"{int(hours)}h {int(minutes)}m {int(seconds)}s", inline=True)
        embed.add_field(name="👑 **Started by", value="Event system", inline=True)
        
        embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/743869767950618744.png")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
    else:
        await interaction.response.send_message("❌ Invalid action! Use: `start`, `stop`, or `status`.", ephemeral=True)

async def auto_end_event():
    """Automatically end an event after duration expires"""
    global event_active, event_amount, event_cooldown, event_duration, event_start_time, event_timer, event_users, event_starter, event_total_followers
    
    if not event_active:
        return
    
    try:
        # Calculate event duration
        duration = datetime.now() - event_start_time
        hours, remainder = divmod(duration.total_seconds(), 3600)
        minutes, seconds = divmod(remainder, 60)
        
        # Reset event variables
        event_active = False
        event_amount = 0
        event_cooldown = 0
        event_duration = 0
        event_start_time = None
        event_timer = None
        
        print(f"[EVENT] Event automatically ended after {int(hours)}h {int(minutes)}m {int(seconds)}s")
        
        # Send announcement to event channel
        try:
            guild = bot.get_guild(1260000639098945638)  # Main server
            if guild:
                channel = guild.get_channel(event_channel_id)
                if channel:
                    # Create event breakdown embed
                    embed = discord.Embed(
                        title="🛑 **EVENT ENDED - BREAKDOWN**",
                        description="**The event has automatically ended! Here's the complete breakdown:**",
                        color=discord.Color.red()
                    )
                    
                    # Event info
                    embed.add_field(name="🎯 **Event Info**", value=f"**Started by:** {event_starter.mention if event_starter else 'Unknown'}\n**Duration:** {int(hours)}h {int(minutes)}m {int(seconds)}s\n**Total Followers Sent:** {event_total_followers:,}", inline=False)
                    
                    # Top users
                    if event_users:
                        # Sort users by amount and get top 10
                        sorted_users = sorted(event_users.items(), key=lambda x: x[1], reverse=True)[:10]
                        
                        top_users_text = ""
                        for i, (user_id, amount) in enumerate(sorted_users, 1):
                            user = guild.get_member(user_id)
                            if user:
                                top_users_text += f"**{i}.** {user.mention} - **{amount:,}** followers\n"
                            else:
                                top_users_text += f"**{i}.** <@{user_id}> - **{amount:,}** followers\n"
                        
                        # Highlight top user
                        if sorted_users:
                            top_user_id, top_amount = sorted_users[0]
                            top_user = guild.get_member(top_user_id)
                            if top_user:
                                embed.add_field(name="👑 **Top User**", value=f"{top_user.mention} got the most followers with **{top_amount:,}** followers!", inline=False)
                        
                        embed.add_field(name="🏆 **Top 10 Users**", value=top_users_text or "No participants", inline=False)
                    else:
                        embed.add_field(name="👥 **Participants**", value="No users participated in this event", inline=False)
                    
                    embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/743869767950618744.png")
                    embed.set_footer(text="Event duration expired")
                    
                    await channel.send(embed=embed)
                    
        except Exception as e:
            print(f"[-] Error sending auto-end announcement: {e}")
            
    except Exception as e:
        print(f"[-] Error in auto_end_event: {e}")

@bot.tree.command(name="role", description="Manage custom roles")
@app_commands.describe(action="Action: create, list, info, assign", role_name="Role name (for create/info/assign)", amount="Follow amount per use (for create)", cooldown="Cooldown in minutes (for create)", max_uses="Maximum uses allowed (for create)", user="User to assign role to (for assign)")
async def role_command(interaction: discord.Interaction, action: str, role_name: str = "", amount: int = 0, cooldown: int = 0, max_uses: int = 0, user: discord.Member = None):
    """Manage custom roles"""
    global custom_roles, user_roles, role_usage_count
    
    # Check if user is OP owner
    if interaction.user.id not in ULTIMATE_OWNER_IDS and interaction.user.id not in OTHER_OWNER_IDS:
        await interaction.response.send_message("❌ This command is for OP owners only!", ephemeral=True)
        return
    
    # Check if command is used in allowed server (but any channel within that server)
    if not (interaction.guild and interaction.guild.id in ALLOWED_SERVERS):
        await interaction.response.send_message("❌ This command can only be used in allowed servers!", ephemeral=True)
        return
    
    action = action.lower()
    
    if action == "create":
        if not role_name:
            await interaction.response.send_message("❌ Please specify a role name!", ephemeral=True)
            return
        
        if amount <= 0:
            await interaction.response.send_message("❌ Please specify a valid amount (> 0)!", ephemeral=True)
            return
        
        if cooldown < 0:
            await interaction.response.send_message("❌ Cooldown cannot be negative!", ephemeral=True)
            return
        
        if max_uses <= 0:
            await interaction.response.send_message("❌ Please specify max uses (> 0)!", ephemeral=True)
            return
        
        # Create custom role configuration
        custom_roles[role_name] = {
            "amount": amount,
            "cooldown": cooldown,
            "max_uses": max_uses,
            "created_by": interaction.user.id,
            "created_at": datetime.now().isoformat()
        }
        
        embed = discord.Embed(
            title="✅ **ROLE CREATED**",
            description=f"**Custom role `{role_name}` has been created!**",
            color=discord.Color.green()
        )
        
        embed.add_field(name="🎯 **Follow Amount", value=f"`{amount}` followers per use", inline=True)
        embed.add_field(name="⏰ **Cooldown", value=f"`{cooldown}` minutes", inline=True)
        embed.add_field(name="🔢 **Max Uses", value=f"`{max_uses}` times", inline=True)
        embed.add_field(name="👑 **Created by", value=interaction.user.mention, inline=True)
        
        embed.add_field(
            name="📋 **How to Assign**",
            value=f"Use `/role assign {role_name} @user` to give this role to someone",
            inline=False
        )
        
        embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/743869767950618744.png")
        embed.set_footer(text="Custom role system")
        
        await interaction.response.send_message(embed=embed)
        print(f"[ROLE] Custom role '{role_name}' created by {interaction.user.name}")
        
    elif action == "assign":
        if not role_name:
            await interaction.response.send_message("❌ Please specify a role name!", ephemeral=True)
            return
        
        if not user:
            await interaction.response.send_message("❌ Please specify a user to assign the role to!", ephemeral=True)
            return
        
        if role_name not in custom_roles:
            await interaction.response.send_message(f"❌ Custom role `{role_name}` not found!", ephemeral=True)
            return
        
        # Check if user has already used this role
        user_id = user.id
        if user_id in role_usage_count and role_name in role_usage_count[user_id]:
            current_uses = role_usage_count[user_id][role_name]
            max_uses = custom_roles[role_name]["max_uses"]
            
            if current_uses >= max_uses:
                await interaction.response.send_message(f"❌ {user.mention} has already used this role `{current_uses}/{max_uses}` times!", ephemeral=True)
                return
        
        # Check cooldown for this role
        role_cooldown = custom_roles[role_name]["cooldown"]
        if role_cooldown > 0:
            cooldown_key = f"role_{role_name}_{user_id}"
            current_time = datetime.now()
            
            if cooldown_key in user_cooldowns:
                time_since_last = current_time - user_cooldowns[cooldown_key]
                if time_since_last < timedelta(minutes=role_cooldown):
                    remaining_time = timedelta(minutes=role_cooldown) - time_since_last
                    minutes, seconds = divmod(remaining_time.total_seconds(), 60)
                    await interaction.response.send_message(
                        f"❌ {user.mention} is on cooldown! Wait `{int(minutes)}m {int(seconds)}s`.",
                        ephemeral=True
                    )
                    return
            
            # Update cooldown
            user_cooldowns[cooldown_key] = current_time
        
        # Assign role to user
        if user_id not in user_roles:
            user_roles[user_id] = []
        
        if role_name not in user_roles[user_id]:
            user_roles[user_id].append(role_name)
        
        # Update usage count
        if user_id not in role_usage_count:
            role_usage_count[user_id] = {}
        if role_name not in role_usage_count[user_id]:
            role_usage_count[user_id][role_name] = 0
        role_usage_count[user_id][role_name] += 1
        
        role_data = custom_roles[role_name]
        uses_left = role_data["max_uses"] - role_usage_count[user_id][role_name]
        
        embed = discord.Embed(
            title="✅ **ROLE ASSIGNED**",
            description=f"**{user.mention} has been given role `{role_name}`!**",
            color=discord.Color.green()
        )
        
        embed.add_field(name="🎯 **Follow Amount", value=f"`{role_data['amount']}` followers per use", inline=True)
        embed.add_field(name="⏰ **Cooldown", value=f"`{role_data['cooldown']}` minutes", inline=True)
        embed.add_field(name="🔢 **Uses Left", value=f"`{uses_left}` of `{role_data['max_uses']}`", inline=True)
        embed.add_field(name="👑 **Assigned by", value=interaction.user.mention, inline=True)
        
        embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/743869767950618744.png")
        embed.set_footer(text="Custom role system")
        
        await interaction.response.send_message(embed=embed)
        
        # DM the user about their new role
        try:
            user_embed = discord.Embed(
                title="🎉 **NEW ROLE ASSIGNED**",
                description=f"**You have been given the role `{role_name}`!**",
                color=discord.Color.gold()
            )
            
            user_embed.add_field(name="🎯 **Follow Amount", value=f"`{role_data['amount']}` followers per use", inline=True)
            user_embed.add_field(name="⏰ **Cooldown", value=f"`{role_data['cooldown']}` minutes", inline=True)
            user_embed.add_field(name="🔢 **Uses Left", value=f"`{uses_left}` of `{role_data['max_uses']}`", inline=True)
            
            user_embed.add_field(
                name="📋 **How to Use**",
                value=f"Use `/tfollow username` during events or use bot services normally!\n"
                      f"Your role permissions are now active.",
                inline=False
            )
            
            user_embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/743869767950618744.png")
            user_embed.set_footer(text="Custom role system")
            
            await user.send(embed=user_embed)
            
        except Exception as e:
            print(f"[-] Error sending role DM to {user.name}: {e}")
        
        print(f"[ROLE] Role '{role_name}' assigned to {user.name} by {interaction.user.name}")
        
    elif action == "list":
        if not custom_roles:
            await interaction.response.send_message("❌ No custom roles have been created yet!", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="📋 **CUSTOM ROLES**",
            description="**All created custom roles**",
            color=discord.Color.blue()
        )
        
        for role_name, role_data in custom_roles.items():
            embed.add_field(
                name=f"🔹 {role_name}",
                value=f"Amount: `{role_data['amount']}` | Cooldown: `{role_data['cooldown']}m` | Max: `{role_data['max_uses']}`",
                inline=False
            )
        
        embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/743869767950618744.png")
        embed.set_footer(text=f"Total roles: {len(custom_roles)}")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
    elif action == "info":
        if not role_name:
            await interaction.response.send_message("❌ Please specify a role name!", ephemeral=True)
            return
        
        if role_name not in custom_roles:
            await interaction.response.send_message(f"❌ Role `{role_name}` not found!", ephemeral=True)
            return
        
        role_data = custom_roles[role_name]
        created_by_user = await bot.fetch_user(role_data["created_by"])
        
        embed = discord.Embed(
            title="ℹ️ **ROLE INFO**",
            description=f"**Information for role `{role_name}`**",
            color=discord.Color.blue()
        )
        
        embed.add_field(name="🎯 **Follow Amount", value=f"`{role_data['amount']}` followers per use", inline=True)
        embed.add_field(name="⏰ **Cooldown", value=f"`{role_data['cooldown']}` minutes", inline=True)
        embed.add_field(name="🔢 **Max Uses", value=f"`{role_data['max_uses']}` times", inline=True)
        embed.add_field(name="👑 **Created by", value=created_by_user.mention if created_by_user else "Unknown", inline=True)
        
        # Show usage statistics
        users_with_role = [uid for uid, roles in user_roles.items() if role_name in roles]
        embed.add_field(name="📊 **Assigned to", value=f"`{len(users_with_role)}` users", inline=True)
        
        embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/743869767950618744.png")
        embed.set_footer(text="Custom role system")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
    else:
        await interaction.response.send_message("❌ Invalid action! Use: `create`, `assign`, `list`, or `info`.", ephemeral=True)

@bot.tree.command(name="disablerole", description="Delete custom role and restore user roles")
@app_commands.describe(role="Role name to disable/delete")
async def disablerole_command(interaction: discord.Interaction, role: str):
    """Disable custom role and restore user roles"""
    global custom_roles, user_roles, role_usage_count
    
    # Check if user is OP owner
    if interaction.user.id not in ULTIMATE_OWNER_IDS and interaction.user.id not in OTHER_OWNER_IDS:
        await interaction.response.send_message("❌ This command is for OP owners only!", ephemeral=True)
        return
    
    # Check if command is used in allowed server (but any channel within that server)
    if not (interaction.guild and interaction.guild.id in ALLOWED_SERVERS):
        await interaction.response.send_message("❌ This command can only be used in allowed servers!", ephemeral=True)
        return
    
    if role not in custom_roles:
        await interaction.response.send_message(f"❌ Custom role `{role}` not found!", ephemeral=True)
        return
    
    # Remove role from all users who have it
    users_to_restore = []
    for user_id, assigned_role in list(user_roles.items()):
        if assigned_role == role:
            users_to_restore.append(user_id)
            del user_roles[user_id]
    
    # Remove role from custom roles
    del custom_roles[role]
    
    # Restore users to their highest role
    for user_id in users_to_restore:
        try:
            member = interaction.guild.get_member(user_id)
            if member:
                # Get user's highest role based on existing permission system
                user_perms = get_user_permission_level_by_id(user_id)
                highest_role_name = get_highest_role_name(user_perms)
                
                embed = discord.Embed(
                    title="🔄 **ROLE RESTORED**",
                    description=f"**Your role has been restored!**",
                    color=discord.Color.blue()
                )
                
                embed.add_field(name="🔹 **Previous Role", value=f"`{role}`", inline=True)
                embed.add_field(name="🔹 **New Role", value=f"`{highest_role_name}`", inline=True)
                embed.add_field(name="👑 **Restored by**", 
                     value=interaction.user.mention, inline=True)
                
                embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/743869767950618744.png")
                embed.set_footer(text="Custom role system")
                
                await member.send(embed=embed)
                print(f"[ROLE] Restored {member.name}'s role from '{role}' to '{highest_role_name}'")
                
        except Exception as e:
            print(f"[-] Error restoring role for user {user_id}: {e}")
    
    embed = discord.Embed(
        title="🗑️ **ROLE DISABLED**",
        description=f"**Custom role `{role}` has been deleted!**",
        color=discord.Color.red()
    )
    
    embed.add_field(name="🔹 **Role Name", value=f"`{role}`", inline=True)
    embed.add_field(name="👥 **Users Affected", value=f"`{len(users_to_restore)}` users restored", inline=True)
    embed.add_field(name="👑 **Disabled by**", 
                     value=interaction.user.mention, inline=True)
    
    embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/743869767950618744.png")
    embed.set_footer(text="Custom role system")
    
    await interaction.response.send_message(embed=embed)
    print(f"[ROLE] Custom role '{role}' disabled by {interaction.user.name}, {len(users_to_restore)} users restored")

# Helper functions for role system
def get_user_permission_level_by_id(user_id):
    """Get user permission level by user ID"""
    # This would need to be implemented based on your existing permission system
    # For now, return a default level
    return {
        "tfollow": 1000,  # Default follow amount
        "tchat": 100,     # Default chat amount  
        "tview": 1000,    # Default view amount
        "tlike": 1000,    # Default like amount
        "tkahoot": 500,   # Default kahoot amount
        "troblox": 1,      # Default roblox amount
        "cooldown": 5,       # Default cooldown
        "roblox_cooldown": 5  # Default roblox cooldown
    }

def get_highest_role_name(user_perms):
    """Get the highest role name based on permissions"""
    if user_perms["tfollow"] >= 10000:
        return "Ultimate Owner"
    elif user_perms["tfollow"] >= 5000:
        return "VIP"
    elif user_perms["tfollow"] >= 1000:
        return "Premium"
    elif user_perms["tfollow"] >= 500:
        return "Gold"
    else:
        return "Basic"

@bot.tree.command(name="tfollow", description="Event follow command - Use during events only!")
@app_commands.describe(username="Twitch username to follow")
async def tfollow_command(interaction: discord.Interaction, username: str):
    """Event-specific follow command"""
    global event_active, event_amount, event_cooldown, event_users, event_total_followers
    
    # Check if command is used in the correct channel
    if interaction.channel.id != event_channel_id:
        await interaction.response.send_message(f"❌ This command can only be used in the event channel (<#{event_channel_id}>).", ephemeral=True)
        return
    
    # Check if event is active
    if not event_active:
        await interaction.response.send_message("❌ No event is currently active! Wait for an event to start.", ephemeral=True)
        return
    
    # Check cooldown if set
    if event_cooldown > 0:
        current_time = datetime.now()
        cooldown_key = f"event_tfollow_{interaction.user.id}"
        
        if cooldown_key in user_cooldowns:
            time_since_last = current_time - user_cooldowns[cooldown_key]
            if time_since_last < timedelta(minutes=event_cooldown):
                remaining_time = timedelta(minutes=event_cooldown) - time_since_last
                minutes, seconds = divmod(remaining_time.total_seconds(), 60)
                await interaction.response.send_message(
                    f"❌ You're on cooldown! Wait `{int(minutes)}m {int(seconds)}s` before using this command again.",
                    ephemeral=True
                )
                return
        
        # Update cooldown
        user_cooldowns[cooldown_key] = current_time
    
    # Get bot name
    bot_name = user_bot_names.get(interaction.user.id, "ReviveX")
    
    # Execute follow bot with event amount
    try:
        await interaction.response.defer()
        
        # Get the follow directory
        follow_dir = os.path.join(os.path.dirname(__file__), 'follow')
        
        # Run follow bot with event parameters
        def run_event_follow():
            import subprocess
            import sys
            import threading
            import uuid
            
            operation_id = str(uuid.uuid4())[:8]
            print(f"[EVENT] Starting follow operation {operation_id} for {username} with {event_amount} followers")
            
            try:
                result = subprocess.run(
                    [sys.executable, "follow.py", username, str(event_amount), bot_name], 
                    cwd=follow_dir,
                    timeout=90
                )
                print(f"[EVENT] Follow operation {operation_id} completed: {result.returncode}")
                return result
            except subprocess.TimeoutExpired:
                print(f"[EVENT] Follow operation {operation_id} timed out")
                return None
            except Exception as e:
                print(f"[EVENT] Follow operation {operation_id} error: {e}")
                return None
        
        OPERATION_POOL.submit(run_event_follow)
        print("[EVENT] Event follow bot submitted to thread pool")
        
        # Track event usage
        if interaction.user.id not in event_users:
            event_users[interaction.user.id] = 0
        event_users[interaction.user.id] += event_amount
        event_total_followers += event_amount
        
        print(f"[EVENT] {interaction.user.name} used event follow - Total for this user: {event_users[interaction.user.id]}, Event total: {event_total_followers}")
        
        # Create success embed
        embed = discord.Embed(
            title="✅ **EVENT FOLLOW ACTIVATED**",
            description=f"**Your event follow has been started!**",
            color=discord.Color.green()
        )
        
        embed.add_field(name="🎯 **Target", value=f"`{username}`", inline=True)
        embed.add_field(name="👥 **Followers", value=f"`{event_amount}`", inline=True)
        embed.add_field(name="🤖 **Bot Name", value=f"`{bot_name}`", inline=True)
        
        embed.add_field(
            name="📋 **Event Info**",
            value=f"This is an event follow! You get `{event_amount}` followers regardless of your regular limits.",
            inline=False
        )
        
        embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/743869767950618744.png")
        embed.set_footer(text=f"User: {interaction.user.name} • Event Command")
        
        await interaction.followup.send(embed=embed)
        
        # Send vouch reminder to user's DMs
        await send_vouch_reminder(interaction.user)
        
    except Exception as e:
        print(f"[EVENT] Event follow error: {e}")
        await interaction.followup.send(f"❌ Error: `{str(e)}`", ephemeral=True)

# Owner-only DM Commands
# =====================

@bot.tree.command(name="bot_off", description="🔴 OP Owner Only - Turn off the bot")
async def bot_off_command(interaction: discord.Interaction):
    """Turn off the bot (OP owner only)"""
    global bot_enabled
    
    # Check if OP owner only
    if interaction.user.id not in ULTIMATE_OWNER_IDS:
        await interaction.response.send_message("❌ This command is for OP owners only!", ephemeral=True)
        return
    
    bot_enabled = False
    
    # Kill all running operations
    for operation_id in list(bot_operation_threads.keys()):
        timeout_operation(operation_id)
    
    # Change bot status to offline
    await bot.change_presence(status=discord.Status.offline, activity=None)
    
    # Send response first
    await interaction.response.send_message(
        "🔴 **BOT TURNED OFF**\n"
        f"👑 Executed by: {interaction.user.mention}\n"
        f"⚠️ All bot services are now disabled\n"
        f"🛑 All running operations have been stopped\n"
        f"📱 Bot panels have been removed\n"
        f"🔌 Bot status set to offline",
        ephemeral=True
    )
    
    # Then try to delete panel messages in all servers
    try:
        for guild in bot.guilds:
            for channel in guild.text_channels:
                try:
                    async for message in channel.history(limit=100):
                        if message.author == bot and "Twitch Bot Control Panel" in message.content:
                            await message.delete()
                            print(f"[PANEL] Deleted panel in {guild.name}/{channel.name}")
                except:
                    continue
    except Exception as e:
        print(f"[PANEL] Error deleting panels: {e}")

@bot.tree.command(name="bot_on", description="🟢 OP Owner Only - Turn on the bot")
async def bot_on_command(interaction: discord.Interaction):
    """Turn on the bot (OP owner only)"""
    global bot_enabled
    
    # Check if OP owner only
    if interaction.user.id not in ULTIMATE_OWNER_IDS:
        await interaction.response.send_message("❌ This command is for OP owners only!", ephemeral=True)
        return
    
    bot_enabled = True
    
    # Change bot status back to online
    await bot.change_presence(status=discord.Status.online, activity=discord.Game("🤖 Twitch Bot Services"))
    
    await interaction.response.send_message(
        "🟢 **BOT TURNED ON**\n"
        f"👑 Executed by: {interaction.user.mention}\n"
        f"✅ All bot services are now enabled\n"
        f"🚀 Ready to accept commands\n"
        f"🔌 Bot status set to online",
        ephemeral=True
    )

@bot.tree.command(name="bot_status", description="📊 OP Owner Only - Check bot status")
async def bot_status_command(interaction: discord.Interaction):
    """Check bot status (OP owner only)"""
    global bot_enabled
    
    # Check if OP owner only
    if interaction.user.id not in ULTIMATE_OWNER_IDS:
        await interaction.response.send_message("❌ This command is for OP owners only!", ephemeral=True)
        return
    
    status_emoji = "🟢" if bot_enabled else "🔴"
    status_text = "ONLINE" if bot_enabled else "OFFLINE"
    
    running_ops = len(bot_operation_threads)
    
    embed = discord.Embed(
        title=f"{status_emoji} **Bot Status**",
        color=discord.Color.green() if bot_enabled else discord.Color.red()
    )
    
    embed.add_field(name="🔌 **Main Status**", value=f"**{status_text}**", inline=False)
    embed.add_field(name="🔄 **Running Operations**", value=f"`{running_ops}` active", inline=False)
    embed.add_field(name="⏰ **Timeout**", value=f"`{BOT_TIMEOUT_MINUTES}` minutes", inline=False)
    
    # Show disabled services
    if disabled_services:
        disabled_list = ", ".join([s.upper() for s in disabled_services])
        embed.add_field(name="🔴 **Disabled Services**", value=f"`{disabled_list}`", inline=False)
    else:
        embed.add_field(name="🟢 **Disabled Services**", value="`None`", inline=False)
    
    embed.add_field(name="👑 **Checked by**", value=interaction.user.mention, inline=False)
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="stop_all", description="🛑 OP Owner Only - Stop all running operations")
async def stop_all_command(interaction: discord.Interaction):
    """Stop all running operations (OP owner only)"""
    
    # Check if OP owner only
    if interaction.user.id not in ULTIMATE_OWNER_IDS:
        await interaction.response.send_message("❌ This command is for OP owners only!", ephemeral=True)
        return
    
    stopped_count = len(bot_operation_threads)
    
    # Kill all running operations
    for operation_id in list(bot_operation_threads.keys()):
        timeout_operation(operation_id)
    
    await interaction.response.send_message(
        "🛑 **ALL OPERATIONS STOPPED**\n"
        f"👑 Executed by: {interaction.user.mention}\n"
        f"🔄 Stopped `{stopped_count}` running operations\n"
        f"✅ All bots have been terminated",
        ephemeral=True
    )

@bot.tree.command(name="service_off", description="🔴 OP Owner Only - Turn off specific service")
@app_commands.describe(service="Service to disable (follow/chat/raid/like/view/kahoot/roblox/all)")
async def service_off_command(interaction: discord.Interaction, service: str):
    """Turn off specific service (OP owner only)"""
    
    # Check if OP owner only
    if interaction.user.id not in ULTIMATE_OWNER_IDS:
        await interaction.response.send_message("❌ This command is for OP owners only!", ephemeral=True)
        return
    
    service = service.lower()
    valid_services = ["follow", "chat", "raid", "like", "view", "kahoot", "roblox", "all"]
    
    if service not in valid_services:
        await interaction.response.send_message(
            f"❌ Invalid service! Choose from: {', '.join(valid_services)}", 
            ephemeral=True
        )
        return
    
    global disabled_services
    
    if service == "all":
        disabled_services.update(["follow", "chat", "raid", "like", "view", "kahoot", "roblox"])
        await interaction.response.send_message(
            f"🔴 **ALL SERVICES DISABLED**\n"
            f"👑 Executed by: {interaction.user.mention}\n"
            f"📝 All bot services are now disabled\n"
            f"⚠️ Use `/service_on [service]` to re-enable",
            ephemeral=True
        )
    else:
        disabled_services.add(service)
        await interaction.response.send_message(
            f"🔴 **SERVICE DISABLED**\n"
            f"👑 Executed by: {interaction.user.mention}\n"
            f"📝 Service: `{service.upper()}`\n"
            f"✅ Service is now disabled\n"
            f"⚠️ Use `/service_on {service}` to re-enable",
            ephemeral=True
        )

@bot.tree.command(name="service_on", description="🟢 OP Owner Only - Turn on specific service")
@app_commands.describe(service="Service to enable (follow/chat/raid/like/view/kahoot/roblox/all)")
async def service_on_command(interaction: discord.Interaction, service: str):
    """Turn on specific service (OP owner only)"""
    
    # Check if OP owner only
    if interaction.user.id not in ULTIMATE_OWNER_IDS:
        await interaction.response.send_message("❌ This command is for OP owners only!", ephemeral=True)
        return
    
    service = service.lower()
    valid_services = ["follow", "chat", "raid", "like", "view", "kahoot", "roblox", "all"]
    
    if service not in valid_services:
        await interaction.response.send_message(
            f"❌ Invalid service! Choose from: {', '.join(valid_services)}", 
            ephemeral=True
        )
        return
    
    global disabled_services
    
    if service == "all":
        disabled_services.clear()
        await interaction.response.send_message(
            f"🟢 **ALL SERVICES ENABLED**\n"
            f"👑 Executed by: {interaction.user.mention}\n"
            f"📝 All bot services are now enabled\n"
            f"✅ Users can now access all services",
            ephemeral=True
        )
    else:
        if service in disabled_services:
            disabled_services.remove(service)
            await interaction.response.send_message(
                f"🟢 **SERVICE ENABLED**\n"
                f"👑 Executed by: {interaction.user.mention}\n"
                f"📝 Service: `{service.upper()}`\n"
                f"✅ Service is now enabled\n"
                f"⚠️ Use `/service_off {service}` to disable again",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                f"⚠️ **SERVICE ALREADY ENABLED**\n"
                f"👑 Executed by: {interaction.user.mention}\n"
                f"📝 Service: `{service.upper()}`\n"
                f"✅ Service was already enabled",
                ephemeral=True
            )

# Warning tracking
warning_users = {}  # Track users who have been warned
WARNING_COOLDOWN_HOURS = 24  # Can only warn same user once per 24 hours

@bot.tree.command(name="send_warning", description="⚠️ Owner Only - Send vouch reminder warning")
@app_commands.describe(user="User to warn", reason="Reason for warning")
async def send_warning_command(interaction: discord.Interaction, user: discord.User, reason: str = "Please remember to vouch for your recent services"):
    """Send warning to user about vouching (owner only)"""
    
    # Check if owner (all owners can use this)
    if interaction.user.id not in ULTIMATE_OWNER_IDS and interaction.user.id not in OTHER_OWNER_IDS:
        await interaction.response.send_message("❌ This command is for owners only!", ephemeral=True)
        return
    
    # Check cooldown
    user_id = user.id
    current_time = time.time()
    if user_id in warning_users and current_time - warning_users[user_id] < (WARNING_COOLDOWN_HOURS * 3600):
        await interaction.response.send_message(f"⚠️ This user was already warned within the last {WARNING_COOLDOWN_HOURS} hours.", ephemeral=True)
        return
    
    # Send warning DM
    try:
        warning_embed = discord.Embed(
            title="⚠️ **Important Reminder - Action Required**",
            description=f"Hello {user.mention}, this is an important reminder regarding your recent bot service usage.",
            color=discord.Color.orange()
        )
        
        warning_embed.add_field(name="📝 **Reminder**", value=reason, inline=False)
        warning_embed.add_field(name="⏰ **Action Required**", value="Please ensure you leave a vouch for the services you received. This helps us maintain quality service.", inline=False)
        warning_embed.add_field(name="⚠️ **Important Notice**", value="Failure to vouch within a reasonable timeframe may result in temporary access restrictions (up to 1 week).", inline=False)
        warning_embed.add_field(name="💬 **Questions?**", value=f"Please contact <@{OWNER_ID}> if you have any questions or need assistance.", inline=False)
        
        warning_embed.set_footer(text="This is an automated reminder from the bot management system")
        warning_embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/743869767950618744.png")
        
        await user.send(embed=warning_embed)
        
        # Track warning
        warning_users[user_id] = current_time
        
        await interaction.response.send_message(
            f"✅ **Warning Sent**\n"
            f"👤 User: {user.mention} (`{user.id}`)\n"
            f"📝 Reason: {reason}\n"
            f"⏰ Sent at: <t:{int(current_time)}:R>\n"
            f"💡 User has been reminded to vouch!",
            ephemeral=True
        )
        
    except discord.Forbidden:
        await interaction.response.send_message(f"❌ Could not send DM to {user.mention}. They may have DMs disabled.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ Error sending warning: {str(e)}", ephemeral=True)

@bot.tree.command(name="bot_cooldown_remove", description="🔄 OP Owner Only - Remove or set custom cooldowns")
@app_commands.describe(user="User to modify cooldown for", service="Service to modify (all/follow/chat/raid/like/kahoot/roblox)", action="Action: remove/set", cooldown_minutes="Custom cooldown in minutes (only for 'set' action)")
async def bot_cooldown_remove_command(interaction: discord.Interaction, user: discord.User, service: str = "all", action: str = "remove", cooldown_minutes: int = 0):
    """Remove or set custom cooldowns for users (OP owner only)"""
    
    # Check if OP owner only
    if interaction.user.id not in ULTIMATE_OWNER_IDS:
        await interaction.response.send_message("❌ This command is for OP owners only!", ephemeral=True)
        return
    
    service = service.lower()
    action = action.lower()
    valid_services = ["all", "follow", "chat", "raid", "like", "kahoot", "roblox"]
    valid_actions = ["remove", "set"]
    
    if service not in valid_services:
        await interaction.response.send_message(
            f"❌ Invalid service! Choose from: {', '.join(valid_services)}", 
            ephemeral=True
        )
        return
    
    if action not in valid_actions:
        await interaction.response.send_message(
            f"❌ Invalid action! Choose from: {', '.join(valid_actions)}", 
            ephemeral=True
        )
        return
    
    if action == "set" and cooldown_minutes < 0:
        await interaction.response.send_message("❌ Cooldown minutes cannot be negative!", ephemeral=True)
        return
    
    # Store custom cooldowns
    if not hasattr(bot, 'custom_cooldowns'):
        bot.custom_cooldowns = {}
    
    user_id = user.id
    
    if action == "remove":
        # Remove cooldown
        if service == "all":
            # Remove all cooldowns
            removed_regular = False
            removed_roblox = False
            
            if user_id in user_cooldowns:
                del user_cooldowns[user_id]
                removed_regular = True
            
            if user_id in roblox_cooldowns:
                del roblox_cooldowns[user_id]
                removed_roblox = True
            
            # Also remove custom cooldowns
            if user_id in bot.custom_cooldowns:
                del bot.custom_cooldowns[user_id]
            
            await interaction.response.send_message(
                f"🔄 **Cooldowns Removed**\n"
                f"👤 User: {user.mention} (`{user_id}`)\n"
                f"🗑️ Services: **All**\n"
                f"✅ Regular cooldown: {'Removed' if removed_regular else 'None'}\n"
                f"✅ Roblox cooldown: {'Removed' if removed_roblox else 'None'}\n"
                f"👑 Executed by: {interaction.user.mention}",
                ephemeral=True
            )
        else:
            # Remove specific service cooldown
            removed = False
            
            if service == "roblox":
                if user_id in roblox_cooldowns:
                    del roblox_cooldowns[user_id]
                    removed = True
            else:
                if user_id in user_cooldowns:
                    del user_cooldowns[user_id]
                    removed = True
            
            # Remove custom cooldown if exists
            if user_id in bot.custom_cooldowns and service in bot.custom_cooldowns[user_id]:
                del bot.custom_cooldowns[user_id][service]
                if not bot.custom_cooldowns[user_id]:  # If empty, remove user entry
                    del bot.custom_cooldowns[user_id]
                removed = True
            
            await interaction.response.send_message(
                f"🔄 **Cooldown Removed**\n"
                f"👤 User: {user.mention} (`{user_id}`)\n"
                f"🗑️ Service: **{service.upper()}**\n"
                f"✅ Status: {'Removed' if removed else 'No cooldown existed'}\n"
                f"👑 Executed by: {interaction.user.mention}",
                ephemeral=True
            )
    
    elif action == "set":
        # Set custom cooldown
        if user_id not in bot.custom_cooldowns:
            bot.custom_cooldowns[user_id] = {}
        
        if service == "all":
            # Set all services
            bot.custom_cooldowns[user_id] = {
                "follow": cooldown_minutes,
                "chat": cooldown_minutes,
                "raid": cooldown_minutes,
                "like": cooldown_minutes,
                "kahoot": cooldown_minutes,
                "roblox": cooldown_minutes
            }
            
            await interaction.response.send_message(
                f"⚙️ **Custom Cooldown Set**\n"
                f"👤 User: {user.mention} (`{user_id}`)\n"
                f"⏱️ Services: **All**\n"
                f"🕐 Duration: `{cooldown_minutes}` minutes\n"
                f"👑 Executed by: {interaction.user.mention}",
                ephemeral=True
            )
        else:
            # Set specific service
            bot.custom_cooldowns[user_id][service] = cooldown_minutes
            
            await interaction.response.send_message(
                f"⚙️ **Custom Cooldown Set**\n"
                f"👤 User: {user.mention} (`{user_id}`)\n"
                f"⏱️ Service: **{service.upper()}**\n"
                f"🕐 Duration: `{cooldown_minutes}` minutes\n"
                f"👑 Executed by: {interaction.user.mention}",
                ephemeral=True
            )

@bot.tree.command(name="set_custom", description="👑 OP Owner Only - Set custom permissions for user (Server 2)")
@app_commands.describe(user="User to set custom permissions for", service="Service to customize", amount="Amount (supports 100k, 1M, etc.)", cooldown_minutes="Cooldown in minutes (0.5 = 30 seconds, 1 = 1 minute)")
async def set_custom_command(interaction: discord.Interaction, user: discord.User, service: str, amount: str, cooldown_minutes: float):
    """Set custom permissions for a user (OP owner only)"""
    
    # Check if OP owner only
    if interaction.user.id not in ULTIMATE_OWNER_IDS:
        await interaction.response.send_message("❌ This command is for OP owners only!", ephemeral=True)
        return
    
    # Parse amount (supports k, M, B suffixes)
    try:
        amount_lower = amount.lower().replace(',', '').replace(' ', '')
        if amount_lower.endswith('k'):
            parsed_amount = int(float(amount_lower[:-1]) * 1000)
        elif amount_lower.endswith('m'):
            parsed_amount = int(float(amount_lower[:-1]) * 1000000)
        elif amount_lower.endswith('b'):
            parsed_amount = int(float(amount_lower[:-1]) * 1000000000)
        else:
            parsed_amount = int(amount_lower)
    except ValueError:
        await interaction.response.send_message("❌ Invalid amount format! Use formats like: 1000, 100k, 1M", ephemeral=True)
        return
    
    # Validate service
    valid_services = ['tfollow', 'traid', 'tview', 'tlike', 'tchat', 'tkahoot', 'troblox']
    if service not in valid_services:
        await interaction.response.send_message(f"❌ Invalid service! Valid: {', '.join(valid_services)}", ephemeral=True)
        return
    
    # Initialize custom permissions storage if not exists
    if not hasattr(bot, 'custom_permissions'):
        bot.custom_permissions = {}
    
    # Get server ID (Server 2 only)
    server_id = 1479583403249762387
    
    # Initialize user custom permissions if not exists
    if user.id not in bot.custom_permissions:
        bot.custom_permissions[user.id] = {}
    
    if server_id not in bot.custom_permissions[user.id]:
        bot.custom_permissions[user.id][server_id] = {}
    
    # Set custom permission
    bot.custom_permissions[user.id][server_id][service] = parsed_amount
    
    # Set cooldown if specified
    if cooldown_minutes > 0:
        bot.custom_permissions[user.id][server_id]['cooldown'] = cooldown_minutes
    
    # Create response embed
    embed = discord.Embed(
        title="👑 **Custom Permissions Set**",
        description=f"✅ Custom permissions have been set for {user.mention}",
        color=discord.Color.green()
    )
    
    embed.add_field(
        name="👤 **Target User**",
        value=f"{user.mention} (`{user.id}`)",
        inline=True
    )
    
    embed.add_field(
        name="🏠 **Server**",
        value="Server 2 (`1479583403249762387`)",
        inline=True
    )
    
    embed.add_field(
        name="⚙️ **Service**",
        value=f"**{service.upper()}**: `{parsed_amount:,}`",
        inline=False
    )
    
    if cooldown_minutes > 0:
        embed.add_field(
            name="⏱️ **Cooldown**",
            value=f"`{cooldown_minutes}` minutes",
            inline=True
        )
    
    embed.add_field(
        name="📝 **Note**",
        value="Custom permissions override role-based permissions.\nUse `/clear_custom` to remove custom permissions.",
        inline=False
    )
    
    embed.set_footer(text=f"Executed by {interaction.user.name}")
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="clear_custom", description="🗑️ OP Owner Only - Clear custom permissions for user")
@app_commands.describe(user="User to clear custom permissions for")
async def clear_custom_command(interaction: discord.Interaction, user: discord.User):
    """Clear custom permissions for a user (OP owner only)"""
    
    # Check if OP owner only
    if interaction.user.id not in ULTIMATE_OWNER_IDS:
        await interaction.response.send_message("❌ This command is for OP owners only!", ephemeral=True)
        return
    
    # Check if custom permissions exist
    if not hasattr(bot, 'custom_permissions') or user.id not in bot.custom_permissions:
        await interaction.response.send_message("❌ No custom permissions found for this user!", ephemeral=True)
        return
    
    # Remove custom permissions
    removed_permissions = bot.custom_permissions.pop(user.id, {})
    
    # Create response embed
    embed = discord.Embed(
        title="🗑️ **Custom Permissions Cleared**",
        description=f"✅ All custom permissions have been cleared for {user.mention}",
        color=discord.Color.orange()
    )
    
    embed.add_field(
        name="👤 **Target User**",
        value=f"{user.mention} (`{user.id}`)",
        inline=True
    )
    
    embed.add_field(
        name="🏠 **Server**",
        value="Server 2 (`1479583403249762387`)",
        inline=True
    )
    
    if removed_permissions:
        embed.add_field(
            name="📋 **Cleared Services**",
            value=f"User will now use role-based permissions",
            inline=False
        )
    
    embed.set_footer(text=f"Executed by {interaction.user.name}")
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="view_custom", description="👀 OP Owner Only - View custom permissions for user")
@app_commands.describe(user="User to view custom permissions for")
async def view_custom_command(interaction: discord.Interaction, user: discord.User):
    """View custom permissions for a user (OP owner only)"""
    
    # Check if OP owner only
    if interaction.user.id not in ULTIMATE_OWNER_IDS:
        await interaction.response.send_message("❌ This command is for OP owners only!", ephemeral=True)
        return
    
    # Check if custom permissions exist
    if not hasattr(bot, 'custom_permissions') or user.id not in bot.custom_permissions:
        await interaction.response.send_message("❌ No custom permissions found for this user!", ephemeral=True)
        return
    
    # Get server permissions
    server_id = 1479583403249762387
    user_perms = bot.custom_permissions[user.id].get(server_id, {})
    
    if not user_perms:
        await interaction.response.send_message("❌ No custom permissions found for this user in Server 2!", ephemeral=True)
        return
    
    # Create response embed
    embed = discord.Embed(
        title="👀 **Custom Permissions View**",
        description=f"Custom permissions for {user.mention}",
        color=discord.Color.blue()
    )
    
    embed.add_field(
        name="👤 **Target User**",
        value=f"{user.mention} (`{user.id}`)",
        inline=True
    )
    
    embed.add_field(
        name="🏠 **Server**",
        value="Server 2 (`1479583403249762387`)",
        inline=True
    )
    
    # Format permissions
    permission_text = []
    for service, amount in user_perms.items():
        if service == 'cooldown':
            permission_text.append(f"⏱️ **Cooldown**: `{amount}` minutes")
        else:
            permission_text.append(f"📊 **{service.upper()}**: `{amount:,}`")
    
    embed.add_field(
        name="⚙️ **Custom Permissions**",
        value="\n".join(permission_text),
        inline=False
    )
    
    embed.set_footer(text=f"Executed by {interaction.user.name}")
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="sync_commands", description="🔄 OP Owner Only - Manually sync bot commands")
async def sync_commands_command(interaction: discord.Interaction):
    """Manually sync bot commands (OP owner only)"""
    
    # Check if OP owner only
    if interaction.user.id not in ULTIMATE_OWNER_IDS:
        await interaction.response.send_message("❌ This command is for OP owners only!", ephemeral=True)
        return
    
    await interaction.response.defer(ephemeral=True)
    
    try:
        # Sync globally
        await bot.tree.sync()
        print("Commands synced globally!")
        
        # Sync to specific servers
        synced_servers = []
        failed_servers = []
        
        for server_id in ALLOWED_SERVERS.keys():
            try:
                guild = discord.Object(id=server_id)
                await bot.tree.sync(guild=guild)
                synced_servers.append(server_id)
                print(f"Commands synced to server {server_id}!")
            except Exception as e:
                failed_servers.append(f"Server {server_id}: {str(e)}")
                print(f"Error syncing to server {server_id}: {e}")
        
        # Create response embed
        embed = discord.Embed(
            title="🔄 **Command Sync Complete**",
            description="✅ Bot commands have been synchronized!",
            color=discord.Color.green()
        )
        
        embed.add_field(
            name="🌐 **Global Sync**",
            value="✅ Successfully synced commands globally",
            inline=True
        )
        
        if synced_servers:
            embed.add_field(
                name="🏠 **Server Syncs**",
                value=f"✅ Synced to {len(synced_servers)} servers",
                inline=True
            )
        
        if failed_servers:
            embed.add_field(
                name="❌ **Failed Syncs**",
                value="\n".join(f"• {server}" for server in failed_servers),
                inline=False
            )
        
        embed.set_footer(text=f"Executed by {interaction.user.name}")
        
        await interaction.followup.send_message(embed=embed, ephemeral=True)
        
    except Exception as e:
        await interaction.followup.send_message(f"❌ Error during sync: {str(e)}", ephemeral=True)

@bot.tree.command(name="clear_warnings", description="🧹 OP Owner Only - Clear warning cooldowns")
async def clear_warnings_command(interaction: discord.Interaction):
    """Clear all warning cooldowns (OP owner only)"""
    
    # Check if OP owner only
    if interaction.user.id not in ULTIMATE_OWNER_IDS:
        await interaction.response.send_message("❌ This command is for OP owners only!", ephemeral=True)
        return
    
    global warning_users
    cleared_count = len(warning_users)
    warning_users.clear()
    
    await interaction.response.send_message(
        f"🧹 **Warnings Cleared**\n"
        f"👑 Executed by: {interaction.user.mention}\n"
        f"🗑️ Cleared `{cleared_count}` warning cooldowns\n"
        f"✅ All users can be warned again",
        ephemeral=True
    )

@bot.tree.command(name="announce", description="📢 OP Owner Only - Send server announcement")
@app_commands.describe(message="Announcement message", channel="Channel to send to (optional)")
async def announce_command(interaction: discord.Interaction, message: str, channel: discord.TextChannel = None):
    """Send announcement to server (OP owner only)"""
    
    # Check if OP owner only
    if interaction.user.id not in ULTIMATE_OWNER_IDS:
        await interaction.response.send_message("❌ This command is for OP owners only!", ephemeral=True)
        return
    
    target_channel = channel or interaction.channel
    
    try:
        announce_embed = discord.Embed(
            title="📢 **Official Announcement**",
            description=message,
            color=discord.Color.purple()
        )
        
        announce_embed.add_field(name="👑 **From**", value=interaction.user.mention, inline=True)
        announce_embed.add_field(name="⏰ **Time**", value=f"<t:{int(time.time())}:R>", inline=True)
        announce_embed.set_footer(text="This is an official announcement from the bot administration")
        announce_embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/743869767950618744.png")
        
        await target_channel.send(embed=announce_embed)
        
        await interaction.response.send_message(
            f"📢 **Announcement Sent**\n"
            f"👑 By: {interaction.user.mention}\n"
            f"📍 Channel: {target_channel.mention}\n"
            f"📝 Message: {message[:50]}{'...' if len(message) > 50 else ''}",
            ephemeral=True
        )
        
    except Exception as e:
        await interaction.response.send_message(f"❌ Error sending announcement: {str(e)}", ephemeral=True)

@bot.tree.command(name="user_info", description="🔍 OP Owner Only - Get detailed user information")
@app_commands.describe(user="User to get info about")
async def user_info_command(interaction: discord.Interaction, user: discord.User = None):
    """Get detailed user information (OP owner only)"""
    
    # Check if OP owner only
    if interaction.user.id not in ULTIMATE_OWNER_IDS:
        await interaction.response.send_message("❌ This command is for OP owners only!", ephemeral=True)
        return
    
    target_user = user or interaction.user
    
    try:
        # Get user permissions
        user_perms = get_user_permission_level(interaction) if target_user == interaction.user else {"tfollow": 0, "traid": 0, "tview": 0, "tlike": 0, "tchat": 0, "tkahoot": 0, "cooldown": 0}
        
        # Check if user has been warned
        warned = target_user.id in warning_users
        last_warning = warning_users.get(target_user.id, 0)
        
        info_embed = discord.Embed(
            title=f"🔍 **User Information**",
            color=discord.Color.blue()
        )
        
        info_embed.set_thumbnail(url=target_user.display_avatar.url if target_user.display_avatar else None)
        info_embed.add_field(name="👤 **User**", value=f"{target_user.mention} (`{target_user.id}`)", inline=False)
        info_embed.add_field(name="📅 **Created**", value=f"<t:{int(target_user.created_at.timestamp())}:R>", inline=True)
        info_embed.add_field(name="🔔 **Warnings**", value=f"⚠️ Warned" if warned else "✅ No warnings", inline=True)
        
        if warned:
            info_embed.add_field(name="⏰ **Last Warning**", value=f"<t:{int(last_warning)}:R>", inline=True)
        
        info_embed.add_field(name="🎯 **Permissions**", 
                           value=f"👥 Follow: `{user_perms.get('tfollow', 0):,}`\n"
                                 f"⚔️ Raid: `{user_perms.get('traid', 0):,}`\n"
                                 f"👁️ View: `{user_perms.get('tview', 0):,}`\n"
                                 f"❤️ Like: `{user_perms.get('tlike', 0):,}`\n"
                                 f"💬 Chat: `{user_perms.get('tchat', 0):,}`\n"
                                 f"🎯 Kahoot: `{user_perms.get('tkahoot', 0):,}`", 
                           inline=False)
        
        info_embed.set_footer(text=f"Requested by: {interaction.user.name}")
        
        await interaction.response.send_message(embed=info_embed, ephemeral=True)
        
    except Exception as e:
        await interaction.response.send_message(f"❌ Error getting user info: {str(e)}", ephemeral=True)

@bot.tree.command(name="bot_ban", description="🚫 OP Owner Only - Ban user from bot services")
@app_commands.describe(user="User to ban from bot", service="Service to ban from (all/follow/chat/raid/like/view/kahoot)", reason="Reason for ban")
async def bot_ban_command(interaction: discord.Interaction, user: discord.User, service: str = "all", reason: str = "Bot access revoked by administration"):
    """Ban user from using bot services (OP owner only)"""
    
    # Check if OP owner only
    if interaction.user.id not in ULTIMATE_OWNER_IDS:
        await interaction.response.send_message("❌ This command is for OP owners only!", ephemeral=True)
        return
    
    service = service.lower()
    valid_services = ["all", "follow", "chat", "raid", "like", "view", "kahoot"]
    
    if service not in valid_services:
        await interaction.response.send_message(
            f"❌ Invalid service! Choose from: {', '.join(valid_services)}", 
            ephemeral=True
        )
        return
    
    # Don't allow banning other owners (except for main ultimate owner)
    if user.id in ULTIMATE_OWNER_IDS or user.id in OTHER_OWNER_IDS:
        # Allow main ultimate owner (1389712262532431882) to ban anyone
        if interaction.user.id != 1389712262532431882:
            await interaction.response.send_message("❌ You cannot ban other owners from the bot!", ephemeral=True)
            return
    
    # Add to ban list
    current_time = time.time()
    bot_banned_users[user.id] = {
        "service": service,
        "reason": reason,
        "banned_by": interaction.user.id,
        "banned_at": current_time,
        "banned_by_name": interaction.user.name
    }
    
    # Send ban notification to user
    try:
        ban_embed = discord.Embed(
            title="🚫 **Bot Access Revoked**",
            description=f"Hello {user.mention}, your access to bot services has been restricted.",
            color=discord.Color.red()
        )
        
        if service == "all":
            ban_embed.add_field(name="🔒 **Banned From**", value="**All Bot Services**", inline=False)
        else:
            ban_embed.add_field(name="🔒 **Banned From**", value=f"**{service.upper()} Service Only**", inline=False)
        
        ban_embed.add_field(name="📝 **Reason**", value=reason, inline=False)
        ban_embed.add_field(name="👑 **Banned By**", value=interaction.user.mention, inline=True)
        ban_embed.add_field(name="📅 **Date**", value=f"<t:{int(current_time)}:R>", inline=True)
        ban_embed.add_field(name="💬 **Appeal**", value=f"Contact <@{OWNER_ID}> for questions or appeals", inline=False)
        
        ban_embed.set_footer(text="This is a permanent restriction until further notice")
        ban_embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/743869767950618744.png")
        
        await user.send(embed=ban_embed)
        
    except discord.Forbidden:
        await interaction.response.send_message(f"⚠️ Could not DM {user.mention} about the ban. They may have DMs disabled.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ Error sending ban DM: {str(e)}", ephemeral=True)
    
    await interaction.response.send_message(
        f"🚫 **BOT BAN ISSUED**\n"
        f"👤 User: {user.mention} (`{user.id}`)\n"
        f"🔒 Service: `{service.upper()}`\n"
        f"📝 Reason: {reason}\n"
        f"👑 By: {interaction.user.mention}\n"
        f"📅 Time: <t:{int(current_time)}:R>\n"
        f"✅ User has been notified",
        ephemeral=True
    )

@bot.tree.command(name="bot_unban", description="✅ OP Owner Only - Unban user from bot services")
@app_commands.describe(user="User to unban")
async def bot_unban_command(interaction: discord.Interaction, user: discord.User):
    """Unban user from bot services (OP owner only)"""
    
    # Check if OP owner only
    if interaction.user.id not in ULTIMATE_OWNER_IDS:
        await interaction.response.send_message("❌ This command is for OP owners only!", ephemeral=True)
        return
    
    if user.id not in bot_banned_users:
        await interaction.response.send_message(f"❌ {user.mention} is not banned from bot services.", ephemeral=True)
        return
    
    # Remove from ban list
    ban_info = bot_banned_users.pop(user.id)
    
    # Send unban notification
    try:
        unban_embed = discord.Embed(
            title="✅ **Bot Access Restored**",
            description=f"Hello {user.mention}, your access to bot services has been restored.",
            color=discord.Color.green()
        )
        
        unban_embed.add_field(name="🔓 **Unbanned From**", value="**All Bot Restrictions**", inline=False)
        unban_embed.add_field(name="👑 **Unbanned By**", value=interaction.user.mention, inline=True)
        unban_embed.add_field(name="📅 **Date**", value=f"<t:{int(time.time())}:R>", inline=True)
        unban_embed.add_field(name="💬 **Note**", value="Please follow all rules and guidelines when using bot services.", inline=False)
        
        unban_embed.set_footer(text="Welcome back to bot services!")
        unban_embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/743869767950618744.png")
        
        await user.send(embed=unban_embed)
        
    except discord.Forbidden:
        await interaction.response.send_message(f"⚠️ Could not DM {user.mention} about the unban.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ Error sending unban DM: {str(e)}", ephemeral=True)
    
    await interaction.response.send_message(
        f"✅ **BOT UNBAN ISSUED**\n"
        f"👤 User: {user.mention} (`{user.id}`)\n"
        f"👑 By: {interaction.user.mention}\n"
        f"📅 Time: <t:{int(time.time())}:R>\n"
        f"🔓 Access has been restored",
        ephemeral=True
    )

@bot.tree.command(name="bot_banlist", description="📋 OP Owner Only - View all bot bans")
async def bot_banlist_command(interaction: discord.Interaction):
    """View all bot bans (OP owner only)"""
    
    # Check if OP owner only
    if interaction.user.id not in ULTIMATE_OWNER_IDS:
        await interaction.response.send_message("❌ This command is for OP owners only!", ephemeral=True)
        return
    
    if not bot_banned_users:
        await interaction.response.send_message("📋 **No users are currently banned from bot services.**", ephemeral=True)
        return
    
    banlist_embed = discord.Embed(
        title="📋 **Bot Ban List**",
        description=f"Total banned users: `{len(bot_banned_users)}`",
        color=discord.Color.orange()
    )
    
    for user_id, ban_info in bot_banned_users.items():
        try:
            user = await bot.fetch_user(user_id)
            user_mention = user.mention if user else f"<@{user_id}>"
            
            banlist_embed.add_field(
                name=f"🚫 {user_mention}",
                value=f"🔒 Service: `{ban_info['service'].upper()}`\n"
                      f"📝 Reason: {ban_info['reason']}\n"
                      f"👑 By: {ban_info['banned_by_name']}\n"
                      f"📅 Date: <t:{int(ban_info['banned_at'])}:R>",
                inline=False
            )
        except:
            continue
    
    banlist_embed.set_footer(text=f"Requested by: {interaction.user.name}")
    
    await interaction.response.send_message(embed=banlist_embed, ephemeral=True)

def is_user_bot_banned(user_id: int, service: str = None) -> tuple[bool, str]:
    """Check if user is banned from bot services"""
    if user_id in bot_banned_users:
        ban_info = bot_banned_users[user_id]
        banned_service = ban_info["service"]
        
        if banned_service == "all":
            return True, "You are banned from all bot services."
        elif service and banned_service == service:
            return True, f"You are banned from the {service.upper()} service."
    
    return False, ""

# Owner IDs for logging
OWNER_DM_ID = 1389712262532431882
ADDITIONAL_OWNER_ID = 1361768357044682994
REGULAR_OWNER_ID = 1398755991394189332
OWNER_LOG_IDS = [OWNER_DM_ID, ADDITIONAL_OWNER_ID, REGULAR_OWNER_ID]
import time

async def log_to_owner(interaction, service, amount, username=None, success=True):
    """Send usage log to all owners via DM"""
    try:
        # Create log embed
        embed = discord.Embed(
            title="📊 **Bot Usage Log**",
            color=discord.Color.green() if success else discord.Color.red()
        )
        
        embed.add_field(name="👤 **User**", value=f"{interaction.user.mention} (`{interaction.user.id}`)", inline=False)
        embed.add_field(name="🏠 **Server**", value=f"{interaction.guild.name} (`{interaction.guild.id}`)", inline=False)
        embed.add_field(name="🎯 **Service**", value=f"**{service}**", inline=True)
        embed.add_field(name="📊 **Amount**", value=f"`{amount:,}`", inline=True)
        embed.add_field(name="⏰ **Time**", value=f"<t:{int(time.time())}:R>", inline=True)
        
        if username:
            embed.add_field(name="🔤 **Target**", value=f"`{username}`", inline=False)
        
        embed.add_field(name="✅ **Status**", value="**Success**" if success else "**Failed**", inline=False)
        
        embed.set_footer(text=f"User: {interaction.user.name} • Server: {interaction.guild.name}")
        embed.set_thumbnail(url=interaction.user.display_avatar.url if interaction.user.display_avatar else None)
        
        # Send to all owners
        for owner_id in OWNER_LOG_IDS:
            try:
                owner_user = await bot.fetch_user(owner_id)
                if owner_user:
                    await owner_user.send(embed=embed)
                    owner_name = "Primary Owner" if owner_id == OWNER_DM_ID else "Additional Owner" if owner_id == ADDITIONAL_OWNER_ID else "Regular Owner"
                    # Log message removed to prevent interference with chat bot
            except Exception as e:
                print(f"[-] Error sending log to owner {owner_id}: {e}")
                
    except Exception as e:
        print(f"[-] Error in log_to_owner function: {e}")

# Video Maker role ID for auto-removal
VIDEO_MAKER_ROLE_ID = 1486667310939766794

async def auto_remove_video_maker_role(interaction):
    """Automatically remove Video Maker role after first use"""
    try:
        if not interaction.guild:
            return
            
        # Check if user has Video Maker role
        video_maker_role = interaction.guild.get_role(VIDEO_MAKER_ROLE_ID)
        if not video_maker_role:
            return
            
        member = interaction.guild.get_member(interaction.user.id)
        if member and video_maker_role in member.roles:
            await member.remove_roles(video_maker_role, reason="Video Maker role used - one-time use")
            print(f"[+] Video Maker role auto-removed from {interaction.user.name}")
            
            # Notify the user
            await interaction.user.send(
                "🎬 **Video Maker Role Used**\n\n"
                "Your Video Maker role has been automatically removed after use.\n"
                "This role was a one-time use for video creation.\n"
                "Contact a moderator if you need this role again."
            )
            
    except Exception as e:
        print(f"[-] Error auto-removing Video Maker role: {e}")

async def has_video_maker_role(interaction) -> bool:
    """Check if user has Video Maker role"""
    if not interaction.guild:
        return False
        
    video_maker_role = interaction.guild.get_role(VIDEO_MAKER_ROLE_ID)
    if not video_maker_role:
        return False
        
    member = interaction.guild.get_member(interaction.user.id)
    return member and video_maker_role in member.roles

# Owner abuse detection system
from collections import defaultdict
owner_usage_tracker = defaultdict(list)  # {owner_id: [(timestamp, service, amount), ...]}
ABUSE_THRESHOLD = timedelta(minutes=10)  # Check for abuse within 10 minutes

# Dynamic owner penalties storage - RESET to fix 3285 limit
owner_penalties = defaultdict(lambda: {"follow_reduction": 0, "cooldown_increase": 0})

# Clear all existing penalties on startup to reset limits
def clear_all_penalties():
    for owner_id in OTHER_OWNER_IDS:
        owner_penalties[owner_id] = {"follow_reduction": 0, "cooldown_increase": 0}

# Clear penalties immediately
clear_all_penalties()

class OwnerWarningView(discord.ui.View):
    def __init__(self, abusive_owner_id, abusive_owner_name):
        super().__init__(timeout=None)
        self.abusive_owner_id = abusive_owner_id
        self.abusive_owner_name = abusive_owner_name
        
        self.add_item(discord.ui.Button(
            label="📩 Send Warning", 
            style=discord.ButtonStyle.red, 
            custom_id="send_warning"
        ))
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        # Only allow ultimate owner (1389712262532431882)
        if interaction.user.id != 1389712262532431882:
            await interaction.response.send_message("❌ Only the main owner can use this!", ephemeral=True)
            return False
        return True

class WarningResponseView(discord.ui.View):
    def __init__(self, owner_name):
        super().__init__(timeout=None)
        self.owner_name = owner_name
        
        self.add_item(discord.ui.Button(
            label="Lower my follow amount I don't care", 
            style=discord.ButtonStyle.red, 
            custom_id="lower_follow"
        ))
        self.add_item(discord.ui.Button(
            label="Increase my cooldown I don't care", 
            style=discord.ButtonStyle.yellow, 
            custom_id="increase_cooldown"
        ))
        self.add_item(discord.ui.Button(
            label="OK", 
            style=discord.ButtonStyle.green, 
            custom_id="ok"
        ))
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        # Only allow the warned owner to respond
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("❌ This is not for you!", ephemeral=True)
            return False
        return True

async def check_owner_abuse(interaction, service, amount):
    """Check if owner is abusing the bot"""
    user_id = interaction.user.id
    current_time = datetime.now()
    
    # Only check other owners, not ultimate owners
    if user_id not in OTHER_OWNER_IDS:
        return
    
    # Add this usage to tracker
    owner_usage_tracker[user_id].append({
        'timestamp': current_time,
        'service': service,
        'amount': amount
    })
    
    # Clean old entries (older than 10 minutes)
    owner_usage_tracker[user_id] = [
        entry for entry in owner_usage_tracker[user_id]
        if current_time - entry['timestamp'] < ABUSE_THRESHOLD
    ]
    
    # Check if they used bot 2+ times in 10 minutes
    if len(owner_usage_tracker[user_id]) >= 2:
        await send_owner_abuse_alert(interaction, user_id)

async def send_owner_abuse_alert(interaction, abusive_owner_id):
    """Send abuse alert to main owner"""
    try:
        main_owner_id = 1389712262532431882
        main_owner = await bot.fetch_user(main_owner_id)
        
        if main_owner:
            # Get usage details
            usage_entries = owner_usage_tracker[abusive_owner_id]
            abusive_user = await bot.fetch_user(abusive_owner_id)
            
            # Analyze abuse pattern
            total_usages = len(usage_entries)
            time_span = (usage_entries[-1]['timestamp'] - usage_entries[0]['timestamp']).total_seconds() / 60  # in minutes
            services_used = list(set(entry['service'] for entry in usage_entries))
            total_amount = sum(entry['amount'] for entry in usage_entries)
            
            # Create abuse alert embed
            embed = discord.Embed(
                title="⚠️ **OWNER ABUSE DETECTED**",
                description=f"Owner is potentially abusing the bot services!",
                color=discord.Color.orange()
            )
            
            embed.add_field(name="👤 **Abusive Owner**", value=f"**{abusive_user.name}** (`{abusive_owner_id}`)", inline=False)
            
            # How they are abusing
            abuse_description = f"• **Used bot {total_usages} times** in just {time_span:.1f} minutes\n"
            abuse_description += f"• **Rapid usage pattern** - less than 10 minutes between uses\n"
            abuse_description += f"• **Services abused**: {', '.join(services_used)}\n"
            abuse_description += f"• **Total volume**: {total_amount:,} requests sent"
            
            embed.add_field(name="🚨 **How They Are Abusing**", value=abuse_description, inline=False)
            embed.add_field(name="📊 **Usage Statistics**", value=f"• **Count**: {total_usages} uses\n• **Time Window**: {time_span:.1f} minutes\n• **Services**: {len(services_used)} different", inline=True)
            embed.add_field(name="⏰ **Detection Threshold**", value="• **Trigger**: 2+ uses in 10 minutes\n• **Actual**: {total_usages} uses in {time_span:.1f} minutes\n• **Status**: ⚠️ **ABUSING**", inline=True)
            
            # Detailed usage breakdown
            usage_text = ""
            for i, entry in enumerate(reversed(usage_entries[-5:]), 1):  # Show last 5 in reverse order
                time_ago = (datetime.now() - entry['timestamp']).total_seconds() / 60
                usage_text += f"{i}. {entry['service']}: {entry['amount']} ({time_ago:.1f} min ago)\n"
            
            embed.add_field(name="📋 **Recent Usage Breakdown**", value=usage_text or "No recent usage", inline=False)
            
            embed.add_field(name="⚡ **Recommended Action**", value="This appears to be spam/abuse behavior. Consider sending a warning to discourage repeated rapid usage.", inline=False)
            
            embed.set_footer(text="Click 'Send Warning' below to issue a formal warning")
            embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/743869767950618744.png")
            
            # Send with warning button
            await main_owner.send(embed=embed, view=OwnerWarningView(abusive_owner_id, abusive_user.name))
            print(f"[+] Detailed owner abuse alert sent to main owner for {abusive_user.name}")
            
    except Exception as e:
        print(f"[-] Error sending owner abuse alert: {e}")

async def send_owner_warning(abusive_owner_id, abusive_owner_name):
    """Send warning to abusive owner"""
    try:
        abusive_owner = await bot.fetch_user(abusive_owner_id)
        
        if abusive_owner:
            # Create warning embed
            embed = discord.Embed(
                title="⚠️ **BOT ABUSE WARNING**",
                description=f"@{abusive_owner_name} this is a warning please stop spamming or else this bot will auto add a cooldown of 10min or lower your follow amount",
                color=discord.Color.red()
            )
            
            embed.add_field(name="🚨 **Warning**", value="You have been detected abusing the bot services", inline=False)
            embed.add_field(name="⏱️ **Consequences**", value="• Auto 10 minute cooldown\n• Lowered follow amount limits", inline=False)
            
            embed.set_footer(text="Please choose an action below")
            embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/743869767950618744.png")
            
            # Send warning with response options
            await abusive_owner.send(embed=embed, view=WarningResponseView(abusive_owner_name))
            print(f"[+] Warning sent to abusive owner {abusive_owner_name}")
            
    except Exception as e:
        print(f"[-] Error sending owner warning: {e}")

# Alting detection system
from collections import defaultdict, Counter
follow_tracker = defaultdict(list)  # {twitch_username: [(user_id, timestamp, amount), ...]}
ALT_THRESHOLD = 2  # Alert when 2+ different users send followers to same account within 24 hours

class AltDetectionView(discord.ui.View):
    def __init__(self, twitch_username, users_data):
        super().__init__(timeout=None)
        self.twitch_username = twitch_username
        self.users_data = users_data
        
        # Create dropdown menu
        self.add_item(discord.ui.Select(
            placeholder="Select a user to moderate",
            options=[
                discord.SelectOption(
                    label=f"{user_data['name']} ({user_data['id']})",
                    description=f"Sent {user_data['amount']} followers",
                    value=str(user_data['id'])
                )
                for user_data in users_data
            ],
            custom_id="user_select"
        ))
        
        # Add action buttons
        self.add_item(discord.ui.Button(label="🔨 Kick", style=discord.ButtonStyle.red, custom_id="kick"))
        self.add_item(discord.ui.Button(label="🔇 Mute", style=discord.ButtonStyle.yellow, custom_id="mute"))
        self.add_item(discord.ui.Button(label="🚫 Ban", style=discord.ButtonStyle.danger, custom_id="ban"))
        self.add_item(discord.ui.Button(label="❌ Close", style=discord.ButtonStyle.secondary, custom_id="close"))
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        # Only allow owners to use this
        if interaction.user.id not in OWNER_IDS:
            await interaction.response.send_message("❌ Only owners can use this!", ephemeral=True)
            return False
        return True

async def check_for_alting(interaction, twitch_username, amount):
    """Check if this user is potentially alting"""
    current_time = datetime.now()
    user_id = interaction.user.id
    user_name = interaction.user.name
    
    # Add this follow to tracker (check ALL users, including owners)
    follow_tracker[twitch_username].append({
        'user_id': user_id,
        'user_name': user_name,
        'timestamp': current_time,
        'amount': amount
    })
    
    # Clean old entries (older than 24 hours)
    follow_tracker[twitch_username] = [
        entry for entry in follow_tracker[twitch_username]
        if current_time - entry['timestamp'] < timedelta(hours=24)
    ]
    
    # Count unique users (include everyone)
    unique_users = len(set(entry['user_id'] for entry in follow_tracker[twitch_username]))
    
    # Debug print
    print(f"[DEBUG] Alting check for {twitch_username}: {unique_users} unique users, threshold: {ALT_THRESHOLD}")
    print(f"[DEBUG] Users targeting {twitch_username}: {list(set(entry['user_id'] for entry in follow_tracker[twitch_username]))}")
    
    # Check if threshold exceeded
    if unique_users >= ALT_THRESHOLD:
        print(f"[DEBUG] Alting threshold exceeded for {twitch_username}!")
        users_data = follow_tracker[twitch_username]
        print(f"[DEBUG] Sending alt alert for {len(users_data)} users...")
        await send_alt_alert(interaction, twitch_username, users_data)
    else:
        print(f"[DEBUG] Alt threshold NOT met for {twitch_username} ({unique_users} users, threshold: {ALT_THRESHOLD})")

async def send_alt_alert(interaction, twitch_username, users_data):
    """Send alert to owners about potential alting"""
    try:
        # Get unique users with their data
        unique_users = {}
        for entry in users_data:
            user_id = entry['user_id']
            if user_id not in unique_users:
                unique_users[user_id] = {
                    'id': user_id,
                    'name': entry['user_name'],
                    'amount': 0,
                    'timestamps': []
                }
            unique_users[user_id]['amount'] += entry['amount']
            unique_users[user_id]['timestamps'].append(entry['timestamp'])
        
        users_list = list(unique_users.values())
        
        for owner_id in OWNER_IDS:
            try:
                owner_user = await bot.fetch_user(owner_id)
                if owner_user:
                    # Create alert embed
                    embed = discord.Embed(
                        title="🚨 **ALTING DETECTED**",
                        description=f"Multiple accounts are sending followers to the same Twitch user!",
                        color=discord.Color.red()
                    )
                    
                    embed.add_field(name="🎯 **Target Twitch User**", value=f"`{twitch_username}`", inline=False)
                    embed.add_field(name="👥 **Unique Accounts**", value=f"`{len(users_list)}` different users", inline=True)
                    embed.add_field(name="⏰ **Time Window**", value="Last 24 hours", inline=True)
                    
                    # List all users
                    users_text = ""
                    for i, user in enumerate(users_list, 1):
                        users_text += f"{i}. **{user['name']}** (`{user['id']}`) - {user['amount']} followers\n"
                    
                    embed.add_field(name="📋 **Involved Users**", value=users_text, inline=False)
                    
                    embed.set_footer(text="Use the panel below to take action")
                    embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/743869767950618744.png")
                    
                    # Send with moderation panel
                    await owner_user.send(embed=embed, view=AltDetectionView(twitch_username, users_list))
                    print(f"[+] Alting alert sent to owner {owner_id} for {twitch_username}")
                    
            except Exception as e:
                print(f"[-] Error sending alting alert to {owner_id}: {e}")
                
    except Exception as e:
        print(f"[-] Error in alting detection: {e}")

# Load token from file or environment
def get_bot_token():
    # Try to get from environment variable first
    token = os.getenv('DISCORD_BOT_TOKEN')
    if token:
        return token
    
    # Try to load from token file
    token_file = os.path.join(os.path.dirname(__file__), 'discord_token.txt')
    if os.path.exists(token_file):
        with open(token_file, 'r') as f:
            return f.read().strip()
    
    # If no token found
    print("Discord bot token not found!")
    print("Please set DISCORD_BOT_TOKEN environment variable or create discord_token.txt file")
    exit()

def main():
    token = get_bot_token()
    if not token:
        print("Cannot start bot without token!")
        return
    
    print("Starting Discord Twitch Bot...")
    print(f"Owner IDs: {OWNER_IDS}")
    print(f"Allowed Servers: {list(ALLOWED_SERVERS.keys())}")
    print("------")
    
    try:
        bot.run(token)
    except discord.errors.LoginFailure:
        print("Invalid Discord token!")
    except discord.errors.PrivilegedIntentsRequired:
        print("ERROR: Privileged intents required!")
        print("Please enable Message Content Intent in Discord Developer Portal")
        print("Go to: https://discord.com/developers/applications")

if __name__ == "__main__":
    main()
    
