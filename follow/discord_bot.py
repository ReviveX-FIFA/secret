import discord
from discord import app_commands
from discord.ext import commands
import json
import os
import random
import asyncio
import aiohttp
from collections import defaultdict
from datetime import datetime, timedelta

# ==========================================
#         CONFIGURATION
# ==========================================

BOT_TOKEN = "revivexorg"

# ==========================================
ROLE_LIMITS: dict[str, dict[str, int | None]] = {
    'member': {'limit': 50, 'cooldown': 180},      # 3 min
    'diamond': {'limit': 550, 'cooldown': 60},     # 1 min
    'premium': {'limit': 1000, 'cooldown': 0},     # no cooldown
    'owner': {'limit': None, 'cooldown': 0},
    '1x Booster': {'limit': 150, 'cooldown': 120},
    '2x Booster': {'limit': 500, 'cooldown': 60},
    'Bronze': {'limit': 100, 'cooldown': 130},
}

# Proxy
PROXY = "http://rotating:VW1w218cjKdfxr8J@pm0.prxgo.com:7778"

# Cooldowns tracker
user_cooldowns = {}

class TwitchFollowerBot(commands.Bot):
    
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        
        super().__init__(command_prefix="!", intents=intents)
        
        self.followed_records = defaultdict(set)
        self.proxies = self.load_proxies()
        
    async def setup_hook(self):
        await self.tree.sync()
        print(f"[+] Commands synced!")
    
    def load_tokens(self):
        """Load Twitch tokens"""
        tokens = []
        if os.path.exists("tokens.txt"):
            with open("tokens.txt", "r") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.isspace():
                        tokens.append(line)
        return tokens
    
    def load_proxies(self):
        """Load proxies from proxies.txt, fallback to hardcoded proxy"""
        proxies = []
        if os.path.exists("proxies.txt"):
            with open("proxies.txt", "r") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.isspace():
                        # Ensure proxy format (add http:// if missing)
                        if not line.startswith("http"):
                            line = "http://" + line
                        proxies.append(line)
        
        # Fallback to hardcoded proxy if no proxies loaded
        if not proxies:
            proxies = [PROXY]
        
        return proxies
    
    def get_user_role(self, member: discord.Member):
        """Get user's highest role - FIXED VERSION"""
        
        # FIRST: Check if user has admin/owner permissions
        if member.guild_permissions.administrator:
            print(f"[DEBUG] {member.name} has admin permissions -> OWNER")
            return "owner"
        
        # Get all role names (lowercase for comparison)
        user_role_names = {role.name.lower() for role in member.roles}
        print(f"[DEBUG] {member.name} roles: {user_role_names}")
        
        # Priority order with variants (case-insensitive)
        role_checks = [
            ("owner", ["owner", "admin", "administrator", "co-owner"]),
            ("premium", ["premium", "prem", "vip"]),
            ("diamond", ["diamond", "💎", "dia"]),
            ("2x Booster", ["2x booster", "2x", "booster level 2", "server booster 2", "nitro booster 2"]),
            ("1x Booster", ["1x booster", "1x", "booster", "server booster", "nitro booster"]),
            ("Bronze", ["bronze", "🥉", "bronz"]),
        ]
        
        # Check each priority role
        for role_key, role_variants in role_checks:
            for variant in role_variants:
                if variant in user_role_names:
                    print(f"[DEBUG] {member.name} matched '{variant}' -> {role_key}")
                    return role_key
        
        print(f"[DEBUG] {member.name} no special role -> member")
        return "member"
    
    def check_cooldown(self, user_id: int, role: str):
        """Check if user is on cooldown"""
        if ROLE_LIMITS[role]['cooldown'] == 0:
            return True, 0
        
        if user_id in user_cooldowns:
            time_passed = (datetime.now() - user_cooldowns[user_id]).total_seconds()
            cooldown = ROLE_LIMITS[role]['cooldown']
            
            if time_passed < cooldown:
                remaining = int(cooldown - time_passed)
                return False, remaining
        
        return True, 0
    
    async def get_user_id(self, username: str):
        """Get Twitch user ID with proxy fallback"""
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

        # Try with proxy first, then fallback to direct connection
        proxies_to_try = []
        
        # Add random proxy if available
        if self.proxies:
            proxies_to_try.append(random.choice(self.proxies))
        
        # Add None (direct connection) as fallback
        proxies_to_try.append(None)
        
        for proxy in proxies_to_try:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        "https://gql.twitch.tv/gql",
                        headers=headers,
                        data=payload,
                        proxy=proxy,
                        timeout=aiohttp.ClientTimeout(total=30)
                    ) as response:
                        if response.status == 200:
                            data = await response.json()
                            return data[0]["data"]["user"]["id"]
            except:
                # Try next proxy on failure
                continue
        
        return None
    
    async def execute_follow(self, target_id: str, token: str, session):
        """Execute single follow with proxy fallback"""
        headers = {
            "Accept": "application/json",
            "Accept-Language": "en-US",
            "Authorization": f"OAuth {token}",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
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

        # Try with proxy first, then fallback to direct connection
        proxies_to_try = []
        
        # Add random proxy if available
        if self.proxies:
            proxies_to_try.append(random.choice(self.proxies))
        
        # Add None (direct connection) as fallback
        proxies_to_try.append(None)
        
        for proxy in proxies_to_try:
            try:
                async with session.post(
                    "https://gql.twitch.tv/gql",
                    data=payload,
                    headers=headers,
                    proxy=proxy,
                    timeout=aiohttp.ClientTimeout(total=15)
                ) as response:
                    result_text = await response.text()
                    
                    if response.status in (200, 204) and "errors" not in result_text.lower():
                        return True
                    
            except:
                # Try next proxy on failure
                continue
        
        return False
    
    async def send_follows(self, target_id: str, count: int, username: str):
        """Send follows as fast as possible"""
        tokens = self.load_tokens()
        
        if not tokens:
            return 0, "No tokens loaded"
        
        # Filter unused tokens
        unused_tokens = [
            token for token in tokens 
            if token not in self.followed_records or target_id not in self.followed_records[token]
        ]
        
        if len(unused_tokens) < count:
            count = len(unused_tokens)
        
        success_count = 0
        lock = asyncio.Lock()
        
        # Ultra fast connector
        connector = aiohttp.TCPConnector(
            limit=0,  # No limit
            limit_per_host=0,  # No limit per host
            ttl_dns_cache=300,
            use_dns_cache=True,
            ssl=False,
            keepalive_timeout=60,
            enable_cleanup_closed=True
        )
        
        async with aiohttp.ClientSession(
            connector=connector,
            timeout=aiohttp.ClientTimeout(total=10)
        ) as session:
            
            async def follow_task(token):
                nonlocal success_count
                
                result = await self.execute_follow(target_id, token, session)
                
                if result:
                    async with lock:
                        success_count += 1
                        self.followed_records[token].add(target_id)
                
                return result
            
            # Fire ALL tasks at once - maximum speed
            tasks = [follow_task(unused_tokens[i]) for i in range(count)]
            await asyncio.gather(*tasks, return_exceptions=True)
        
        return success_count, None

bot = TwitchFollowerBot()

@bot.tree.command(name="tfollow", description="Send Twitch follows")
@app_commands.describe(
    username="Twitch username to follow",
    amount="Number of follows (optional - based on your role)"
)
async def tfollow(
    interaction: discord.Interaction,
    username: str,
    amount: int = None
):
    # Defer reply
    await interaction.response.defer(ephemeral=False)
    
    # Get user role
    role = bot.get_user_role(interaction.user)
    role_data = ROLE_LIMITS[role]
    
    print(f"[COMMAND] User: {interaction.user.name} | Role detected: {role} | Limit: {role_data['limit']}")
    
    # Check cooldown
    can_use, remaining = bot.check_cooldown(interaction.user.id, role)
    
    if not can_use:
        error_embed = discord.Embed(
            title="⏱️ Cooldown Active",
            description=f"You must wait **{remaining}s** before using this command again.",
            color=discord.Color.red()
        )
        error_embed.set_footer(text=f"Role: {role.upper()}")
        
        msg = await interaction.followup.send(embed=error_embed)
        await asyncio.sleep(5)
        await msg.delete()
        return
    
    # Determine follow count
    if amount is None:
        follow_count = role_data['limit'] if role_data['limit'] else 10000
    else:
        if role == 'owner':
            follow_count = amount
        else:
            if role_data['limit'] and amount > role_data['limit']:
                follow_count = role_data['limit']
            else:
                follow_count = amount
    
    print(f"[COMMAND] Follow count: {follow_count}")
    
    # Create processing embed
    processing_embed = discord.Embed(
        title="🔄 Processing Follow Request",
        description=f"**Target:** `{username}`\n**Follows:** `{follow_count}`",
        color=discord.Color.blue()
    )
    processing_embed.add_field(name="Status", value="🔍 Fetching user ID...", inline=False)
    processing_embed.set_footer(text=f"Requested by {interaction.user.name} • Role: {role.upper()}")
    processing_embed.timestamp = discord.utils.utcnow()
    
    msg = await interaction.followup.send(embed=processing_embed)
    
    # Get Twitch user ID
    target_id = await bot.get_user_id(username)
    
    if not target_id:
        error_embed = discord.Embed(
            title="❌ User Not Found",
            description=f"Could not find Twitch user: **{username}**",
            color=discord.Color.red()
        )
        error_embed.set_footer(text=f"Requested by {interaction.user.name}")
        
        await msg.edit(embed=error_embed)
        await asyncio.sleep(5)
        await msg.delete()
        return
    
    # Update embed - sending follows
    processing_embed.set_field_at(0, name="Status", value="📤 Sending follows...", inline=False)
    await msg.edit(embed=processing_embed)
    
    # Send follows
    success_count, error = await bot.send_follows(target_id, follow_count, username)
    
    if error:
        error_embed = discord.Embed(
            title="❌ Error",
            description=f"**Error:** {error}",
            color=discord.Color.red()
        )
        await msg.edit(embed=error_embed)
        await asyncio.sleep(5)
        await msg.delete()
        return
    
    # Update cooldown
    user_cooldowns[interaction.user.id] = datetime.now()
    
    # Success embed
    success_embed = discord.Embed(
        title="✅ Follows Sent Successfully",
        color=discord.Color.green()
    )
    
    success_embed.add_field(
        name="📊 Results",
        value=f"**Target:** `{username}`\n**Sent:** `{success_count}/{follow_count}`\n**Success Rate:** `{(success_count/follow_count*100):.1f}%`",
        inline=False
    )
    
    success_embed.add_field(
        name="👤 User Info",
        value=f"**User:** {interaction.user.mention}\n**Role:** `{role.upper()}`",
        inline=True
    )
    
    if role_data['cooldown'] > 0:
        success_embed.add_field(
            name="⏱️ Next Use",
            value=f"<t:{int((datetime.now() + timedelta(seconds=role_data['cooldown'])).timestamp())}:R>",
            inline=True
        )
    
    success_embed.set_thumbnail(url="https://static-cdn.jtvnw.net/ttv-boxart/518203-144x192.jpg")
    success_embed.set_footer(text="Follow Bot by N1TR00")
    success_embed.timestamp = discord.utils.utcnow()
    
    await msg.edit(embed=success_embed)
    
    # Delete after 10 seconds
    await asyncio.sleep(10)
    await msg.delete()

@bot.event
async def on_ready():
    print(f"""
╔══════════════════════════════════════════════════════════╗
║        DISCORD TWITCH FOLLOWER BOT - FIXED               ║
║              By N1TR00                                   ║
╚══════════════════════════════════════════════════════════╝

[+] Bot: {bot.user.name}
[+] Guilds: {len(bot.guilds)}
[+] Proxy: pm0.prxgo.com:7777

[ROLE LIMITS] - FIXED DETECTION
  Member:      50 follows   | 3min cooldown
  Bronze:      100 follows  | 2min 10s cooldown
  1x Booster:  150 follows  | 2min cooldown
  2x Booster:  500 follows  | 1min cooldown
  Diamond:     550 follows  | 1min cooldown  
  Premium:     1000 follows | No cooldown
  Owner:       UNLIMITED    | No cooldown

[+] Role detection now checks:
  - Administrator permissions (auto OWNER)
  - Case-insensitive matching
  - Multiple role name variants

[+] Bot is ready!
    """)

# Run bot
if __name__ == "__main__":
    if BOT_TOKEN == "":
        print("[!] Please set your bot token!")
    else:
        bot.run(BOT_TOKEN)
