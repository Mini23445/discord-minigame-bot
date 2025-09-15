import discord
from discord.ext import commands
import json
import os
import random
import asyncio
from datetime import datetime, timedelta
import time
import sys
import aiofiles

# Railway logging setup
import logging
logging.basicConfig(level=logging.INFO)

print("🚀 Starting Discord Bot...")

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

# Configuration
ADMIN_ROLE_ID = 1410911675351306250
LOG_CHANNEL_ID = 1413818486404415590
PURCHASE_LOG_CHANNEL_ID = 1413885597826813972

# Roles that get extra entries in giveaways (customize these IDs for your server)
# Format: {role_id: extra_entries}
PRIORITY_ROLES = {
    1410917252190179369: 7,  # Highest priority role - 7 extra entries
    1410917163933503521: 5,  # Medium priority role - 5 extra entries  
    1410917146459897928: 3,  # Low priority role - 3 extra entries
}

# Data storage
user_data = {}
shop_data = []
cooldowns = {"daily": {}, "work": {}, "crime": {}, "gift": {}, "buy": {}, "coinflip": {}, "duel": {}, "giveaway": {}}
pending_duels = {}
active_giveaways = {}
giveaway_daily_totals = {}  # Track daily giveaway amounts

# Data file paths
USER_DATA_FILE = 'user_data.json'
SHOP_DATA_FILE = 'shop_data.json'
COOLDOWNS_FILE = 'cooldowns.json'
GIVEAWAYS_FILE = 'giveaways.json'
DAILY_GIVEAWAYS_FILE = 'daily_giveaways.json'

WORK_JOBS = [
    "worked as a cashier at the supermarket", "stocked shelves at the grocery store", 
    "bagged groceries for customers", "worked the deli counter", "organized the produce section",
    "cleaned shopping carts", "collected carts from the parking lot", "worked customer service desk",
    "restocked the dairy section", "faced products on shelves", "worked the bakery counter",
    "unloaded delivery trucks", "worked overnight stocking shift", "operated the floor buffer",
    "cleaned the break room", "worked at Target", "worked at Walmart", "worked at Best Buy",
    "worked at Home Depot", "worked at CVS pharmacy", "worked the drive-thru window",
    "flipped burgers at McDonald's", "worked the fryer at KFC", "prepped vegetables at Subway",
    "worked as a server at Applebee's", "bussed tables at Olive Garden", "worked as a host at Chili's",
    "cleaned the kitchen at Taco Bell", "worked the pizza oven", "delivered pizzas",
    "worked at Starbucks", "worked at Dunkin Donuts", "made sandwiches at Subway",
    "filed paperwork at an office", "answered phones at a call center", "did data entry",
    "made copies and scanned documents", "worked reception desk", "sorted mail at post office",
    "updated customer databases", "scheduled appointments", "worked at bank teller window",
    "helped customers at DMV", "worked at phone store", "worked at gas station",
    "loaded boxes at Amazon warehouse", "worked construction cleanup", "painted houses",
    "helped people move", "worked landscaping", "cleaned office buildings", "worked at car wash",
    "did home repairs", "worked at recycling center", "unloaded freight trucks",
    "worked factory assembly line", "cleaned windows", "delivered for DoorDash",
    "drove for Uber", "worked at movie theater", "worked at gym front desk",
    "worked at library", "tutored kids", "walked dogs", "pet-sat", "house-sat", "baby-sat"
]

CRIME_ACTIVITIES = [
    "took extra napkins from fast food", "used work wifi for personal stuff", 
    "took longer breaks than allowed", "used company printer for personal use",
    "took pens from work", "ate someone's lunch from office fridge",
    "used sick day when not really sick", "browsed social media during work",
    "took extra coffee from break room", "left work 5 minutes early",
    "used work bathroom excessively", "took free mints from restaurant",
    "opened bag of chips before paying", "ate grapes while shopping",
    "used express lane with too many items", "didn't return shopping cart",
    "cut in line at checkout", "price-checked everything twice",
    "used student discount without being student", "tried on clothes with no intention to buy",
    "squeezed all the bread loaves", "spoiled movie endings", "left someone on read",
    "didn't hold elevator door", "took the good parking spot", "walked slowly in front of people",
    "chewed loudly in quiet places", "talked during movies", "didn't say thanks when door was held",
    "cut in line at coffee shop", "took up two seats on bus", "used someone's Netflix password",
    "didn't skip YouTube ads for creator", "used free trial with fake email",
    "downloaded music illegally", "used fake birthday for discounts",
    "made multiple email accounts for free trials", "used VPN to get cheaper prices",
    "shared streaming passwords", "used incognito mode to avoid cookies",
    "jaywalked across street", "littered a gum wrapper", "parked slightly over the line",
    "used bathroom without buying anything", "took extra sauce packets",
    "mixed different sodas at fountain", "didn't tip delivery driver enough",
    "returned item after using it once", "claimed package was lost when it wasn't",
    "used expired coupon"
]

async def load_data():
    """Load all data from files"""
    global user_data, shop_data, cooldowns, active_giveaways, giveaway_daily_totals
    
    try:
        # Load user data
        if os.path.exists(USER_DATA_FILE):
            async with aiofiles.open(USER_DATA_FILE, 'r') as f:
                contents = await f.read()
                user_data = json.loads(contents)
                print(f"✅ Loaded user data for {len(user_data)} users")
        else:
            print("ℹ️ No user data file found, starting fresh")
            user_data = {}
            
        # Load shop data
        if os.path.exists(SHOP_DATA_FILE):
            async with aiofiles.open(SHOP_DATA_FILE, 'r') as f:
                contents = await f.read()
                shop_data = json.loads(contents)
                print(f"✅ Loaded {len(shop_data)} shop items")
        else:
            print("ℹ️ No shop data file found, starting fresh")
            shop_data = []
            
        # Load cooldowns
        if os.path.exists(COOLDOWNS_FILE):
            async with aiofiles.open(COOLDOWNS_FILE, 'r') as f:
                contents = await f.read()
                cooldowns = json.loads(contents)
                print("✅ Loaded cooldown data")
        else:
            print("ℹ️ No cooldowns file found, starting fresh")
            cooldowns = {"daily": {}, "work": {}, "crime": {}, "gift": {}, "buy": {}, "coinflip": {}, "duel": {}, "giveaway": {}}
        
        # Load active giveaways
        if os.path.exists(GIVEAWAYS_FILE):
            async with aiofiles.open(GIVEAWAYS_FILE, 'r') as f:
                contents = await f.read()
                active_giveaways = json.loads(contents)
                print(f"✅ Loaded {len(active_giveaways)} active giveaways")
        else:
            print("ℹ️ No giveaways file found, starting fresh")
            active_giveaways = {}
            
        # Load daily giveaway totals
        if os.path.exists(DAILY_GIVEAWAYS_FILE):
            async with aiofiles.open(DAILY_GIVEAWAYS_FILE, 'r') as f:
                contents = await f.read()
                giveaway_daily_totals = json.loads(contents)
                print("✅ Loaded daily giveaway totals")
        else:
            print("ℹ️ No daily giveaways file found, starting fresh")
            giveaway_daily_totals = {}
            
    except Exception as e:
        print(f"⚠️ Error loading data: {e}")
        # Initialize empty data structures if loading fails
        user_data = {}
        shop_data = []
        cooldowns = {"daily": {}, "work": {}, "crime": {}, "gift": {}, "buy": {}, "coinflip": {}, "duel": {}, "giveaway": {}}
        active_giveaways = {}
        giveaway_daily_totals = {}

async def save_data():
    """Save all data to files"""
    try:
        # Save user data
        async with aiofiles.open(USER_DATA_FILE, 'w') as f:
            await f.write(json.dumps(user_data, indent=2))
        
        # Save shop data
        async with aiofiles.open(SHOP_DATA_FILE, 'w') as f:
            await f.write(json.dumps(shop_data, indent=2))
        
        # Save cooldowns
        async with aiofiles.open(COOLDOWNS_FILE, 'w') as f:
            await f.write(json.dumps(cooldowns, indent=2))
            
        # Save active giveaways
        async with aiofiles.open(GIVEAWAYS_FILE, 'w') as f:
            await f.write(json.dumps(active_giveaways, indent=2))
            
        # Save daily giveaway totals
        async with aiofiles.open(DAILY_GIVEAWAYS_FILE, 'w') as f:
            await f.write(json.dumps(giveaway_daily_totals, indent=2))
            
        print("💾 Data saved successfully")
        return True
    except Exception as e:
        print(f"⚠️ Error saving data: {e}")
        return False

async def force_save_on_exit():
    """Force save data when bot shuts down"""
    print("🔄 Bot shutting down, saving data...")
    try:
        if await save_data():
            print("💾 Data saved on exit")
        else:
            print("❌ Failed to save data on exit")
    except Exception as e:
        print(f"⚠️ Error saving on exit: {e}")

async def log_action(action_type, title, description, color=0x0099ff, user=None, fields=None):
    """Send log message to the log channel"""
    try:
        log_channel = bot.get_channel(LOG_CHANNEL_ID)
        if not log_channel:
            print(f"⚠️ Log channel {LOG_CHANNEL_ID} not found!")
            return
        
        embed = discord.Embed(
            title=title,
            description=description,
            color=color,
            timestamp=datetime.now()
        )
        
        if user:
            embed.set_author(name=user.display_name, icon_url=user.display_avatar.url)
        
        if fields:
            for field in fields:
                embed.add_field(
                    name=field.get("name", "Field"),
                    value=field.get("value", "No value"),
                    inline=field.get("inline", True)
                )
        
        embed.set_footer(text=f"Action: {action_type}")
        await log_channel.send(embed=embed)
        
    except Exception as e:
        print(f"⚠️ Error sending log: {e}")

async def log_purchase(user, item_name, price, quantity=1):
    """Log purchase to purchase log channel"""
    try:
        purchase_channel = bot.get_channel(PURCHASE_LOG_CHANNEL_ID)
        if not purchase_channel:
            print(f"⚠️ Purchase log channel {PURCHASE_LOG_CHANNEL_ID} not found!")
            return
        
        embed = discord.Embed(
            title="🛒 Purchase Made",
            color=0x00ff00,
            timestamp=datetime.now()
        )
        
        embed.add_field(name="User", value=user.mention, inline=True)
        embed.add_field(name="Item", value=item_name, inline=True)
        embed.add_field(name="Quantity", value=str(quantity), inline=True)
        embed.add_field(name="Total Cost", value=f"{price * quantity:,} 🪙", inline=True)
        embed.add_field(name="Unit Price", value=f"{price:,} 🪙", inline=True)
        
        embed.set_author(name=user.display_name, icon_url=user.display_avatar.url)
        await purchase_channel.send(embed=embed)
        
    except Exception as e:
        print(f"⚠️ Error sending purchase log: {e}")

def get_user_balance(user_id):
    """Get user balance"""
    return user_data.get(str(user_id), {}).get('balance', 0)

def update_balance(user_id, amount):
    """Update user balance"""
    user_id = str(user_id)
    if user_id not in user_data:
        user_data[user_id] = {'balance': 0, 'total_earned': 0, 'total_spent': 0}
    
    user_data[user_id]['balance'] += amount
    if amount > 0:
        user_data[user_id]['total_earned'] = user_data[user_id].get('total_earned', 0) + amount
    else:
        user_data[user_id]['total_spent'] = user_data[user_id].get('total_spent', 0) + abs(amount)
    
    return user_data[user_id]['balance']

def get_rank(balance):
    """Get user rank"""
    if balance >= 100000: return "🏆 Legendary"
    elif balance >= 50000: return "💎 Elite"
    elif balance >= 20000: return "🥇 VIP"
    elif balance >= 10000: return "🥈 Premium"
    elif balance >= 5000: return "🥉 Gold"
    elif balance >= 1000: return "🟢 Silver"
    else: return "🔵 Starter"

def can_use_command(user_id, command_type, hours):
    """Check if user can use command with persistent cooldowns"""
    user_id = str(user_id)
    if user_id not in cooldowns[command_type]:
        return True, None
    
    try:
        last_used = datetime.fromisoformat(cooldowns[command_type][user_id])
        next_use = last_used + timedelta(hours=hours)
        if datetime.now() >= next_use:
            return True, None
        return False, next_use
    except:
        return True, None

def can_use_short_cooldown(user_id, command_type, seconds):
    """Check short cooldowns"""
    user_id = str(user_id)
    if user_id not in cooldowns[command_type]:
        return True
    
    try:
        last_used = float(cooldowns[command_type][user_id])
        if time.time() - last_used >= seconds:
            return True
        return False
    except:
        return True

def set_short_cooldown(user_id, command_type):
    """Set short cooldown using timestamp"""
    cooldowns[command_type][str(user_id)] = str(time.time())

def format_time(next_use):
    """Format time remaining"""
    try:
        remaining = next_use - datetime.now()
        hours = int(remaining.total_seconds() // 3600)
        minutes = int((remaining.total_seconds() % 3600) // 60)
        if hours > 0:
            return f"{hours}h {minutes}m"
        return f"{minutes}m"
    except:
        return "soon"

def is_admin(user):
    """Check if user is admin"""
    return any(role.id == ADMIN_ROLE_ID for role in user.roles)

# Auto-save task
async def auto_save():
    """Auto save every 30 seconds"""
    while True:
        await asyncio.sleep(30)
        await save_data()

# Clean up expired duels
async def cleanup_expired_duels():
    """Clean up expired duel challenges"""
    while True:
        await asyncio.sleep(300)  # 5 minutes
        current_time = datetime.now()
        expired_duels = []
        
        for duel_key, duel_data in pending_duels.items():
            try:
                created_at = duel_data['created_at']
                if (current_time - created_at).total_seconds() > 300:
                    expired_duels.append(duel_key)
            except:
                expired_duels.append(duel_key)
        
        for expired_key in expired_duels:
            del pending_duels[expired_key]

# Clean up expired giveaways
async def cleanup_expired_giveaways():
    """Clean up expired giveaways"""
    while True:
        await asyncio.sleep(60)  # 1 minute
        current_time = datetime.now()
        expired_giveaways = []
        
        for giveaway_id, giveaway_data in active_giveaways.items():
            try:
                end_time = datetime.fromisoformat(giveaway_data['end_time'])
                if current_time >= end_time:
                    expired_giveaways.append(giveaway_id)
            except:
                expired_giveaways.append(giveaway_id)
        
        for expired_id in expired_giveaways:
            del active_giveaways[expired_id]
            await save_data()

# Reset daily giveaway totals at midnight
async def reset_daily_giveaway_totals():
    """Reset daily giveaway totals at midnight"""
    while True:
        now = datetime.now()
        # Calculate time until next midnight
        next_midnight = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        wait_seconds = (next_midnight - now).total_seconds()
        
        await asyncio.sleep(wait_seconds)
        
        # Reset daily totals
        giveaway_daily_totals.clear()
        await save_data()
        print("🔄 Reset daily giveaway totals")

@bot.event
async def on_ready():
    print(f'🚀 {bot.user} is online!')
    await load_data()
    
    # Start background tasks
    bot.auto_save_task = asyncio.create_task(auto_save())
    bot.cleanup_task = asyncio.create_task(cleanup_expired_duels())
    bot.giveaway_cleanup_task = asyncio.create_task(cleanup_expired_giveaways())
    bot.daily_reset_task = asyncio.create_task(reset_daily_giveaway_totals())
    
    try:
        synced = await bot.tree.sync()
        print(f"✅ Synced {len(synced)} commands")
    except Exception as e:
        print(f"❌ Failed to sync: {e}")

@bot.event
async def on_message(message):
    if not message.author.bot and message.guild:
        tokens = random.randint(1, 5)
        update_balance(message.author.id, tokens)
    await bot.process_commands(message)

@bot.tree.command(name="balance", description="Check your token balance")
async def balance(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    balance = get_user_balance(interaction.user.id)
    data = user_data.get(user_id, {})
    earned = data.get('total_earned', 0)
    spent = data.get('total_spent', 0)
    rank = get_rank(balance)
    
    embed = discord.Embed(
        title="💰 Token Wallet",
        color=0x7B68EE,
        timestamp=datetime.now()
    )
    
    embed.add_field(name="Current Balance", value=f"**{balance:,}** 🪙", inline=True)
    embed.add_field(name="Rank", value=rank, inline=True)
    embed.add_field(name="Total Spent", value=f"{spent:,} 🪙", inline=True)
    embed.add_field(name="Total Earned", value=f"{earned:,} 🪙", inline=True)
    embed.add_field(name="‎", value="‎", inline=True)
    embed.add_field(name="‎", value="‎", inline=True)
    
    embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
    embed.set_footer(text="💬 Chat to earn 1-5 tokens per message")
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="daily", description="Claim daily tokens (24h cooldown)")
async def daily(interaction: discord.Interaction):
    can_use, next_use = can_use_command(interaction.user.id, "daily", 24)
    
    if not can_use:
        time_left = format_time(next_use)
        await interaction.response.send_message(f"⏰ Daily already claimed! Come back in **{time_left}**", ephemeral=True)
        return
    
    tokens = random.randint(1, 50)
    new_balance = update_balance(interaction.user.id, tokens)
    cooldowns["daily"][str(interaction.user.id)] = datetime.now().isoformat()
    await save_data()
    
    embed = discord.Embed(title="🎁 Daily Reward!", color=0x00ff00)
    embed.add_field(name="Earned", value=f"{tokens:,} 🪙", inline=True)
    embed.add_field(name="Balance", value=f"{new_balance:,} 🪙", inline=True)
    embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="work", description="Work for tokens (3h cooldown)")
async def work(interaction: discord.Interaction):
    can_use, next_use = can_use_command(interaction.user.id, "work", 3)
    
    if not can_use:
        time_left = format_time(next_use)
        await interaction.response.send_message(f"💼 Still tired! Rest for **{time_left}** more", ephemeral=True)
        return
    
    tokens = random.randint(1, 100)
    job = random.choice(WORK_JOBS)
    new_balance = update_balance(interaction.user.id, tokens)
    cooldowns["work"][str(interaction.user.id)] = datetime.now().isoformat()
    await save_data()
    
    embed = discord.Embed(title="💼 Work Complete!", color=0x4CAF50)
    embed.add_field(name="Job", value=f"You {job}", inline=False)
    embed.add_field(name="Earned", value=f"{tokens:,} 🪙", inline=True)
    embed.add_field(name="Balance", value=f"{new_balance:,} 🪙", inline=True)
    embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="crime", description="Commit crime for tokens (1h cooldown, risky!)")
async def crime(interaction: discord.Interaction):
    can_use, next_use = can_use_command(interaction.user.id, "crime", 1)
    
    if not can_use:
        time_left = format_time(next_use)
        await interaction.response.send_message(f"🚔 Lay low for **{time_left}** more!", ephemeral=True)
        return
    
    success = random.choice([True, False])
    activity = random.choice(CRIME_ACTIVITIES)
    
    if success:
        tokens = random.randint(1, 100)
        new_balance = update_balance(interaction.user.id, tokens)
        embed = discord.Embed(title="🎭 Crime Success!", color=0x00ff00)
        embed.add_field(name="Crime", value=f"You {activity}", inline=False)
        embed.add_field(name="Gained", value=f"+{tokens:,} 🪙", inline=True)
    else:
        tokens = random.randint(1, 200)
        current = get_user_balance(interaction.user.id)
        tokens = min(tokens, current)
        new_balance = update_balance(interaction.user.id, -tokens)
        embed = discord.Embed(title="🚔 Crime Failed!", color=0xff4444)
        embed.add_field(name="Crime", value=f"Tried to {activity}", inline=False)
        embed.add_field(name="Lost", value=f"-{tokens:,} 🪙", inline=True)
    
    embed.add_field(name="Balance", value=f"{new_balance:,} 🪙", inline=True)
    embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
    
    cooldowns["crime"][str(interaction.user.id)] = datetime.now().isoformat()
    await save_data()
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="coinflip", description="Bet tokens on a coinflip")
async def coinflip(interaction: discord.Interaction, amount: int, choice: str):
    if not can_use_short_cooldown(interaction.user.id, "coinflip", 5):
        await interaction.response.send_message("⏰ Please wait 5 seconds between coinflips!", ephemeral=True)
        return
    
    if amount <= 0:
        await interaction.response.send_message("❌ Bet amount must be greater than 0!", ephemeral=True)
        return
    
    choice = choice.lower()
    if choice not in ['heads', 'tails', 'h', 't']:
        await interaction.response.send_message("❌ Choose 'heads' or 'tails' (or 'h'/'t')!", ephemeral=True)
        return
    
    if choice in ['h', 'heads']:
        choice = 'heads'
    else:
        choice = 'tails'
    
    balance = get_user_balance(interaction.user.id)
    if balance < amount:
        await interaction.response.send_message(f"❌ Insufficient funds! You need **{amount - balance:,}** more tokens.", ephemeral=True)
        return

    win_chance = 50.0  # 50% chance to win
    random_number = random.uniform(0, 100)
    won = random_number <= win_chance
    
    result = choice if won else ('tails' if choice == 'heads' else 'heads')
    
    if won:
        winnings = amount
        new_balance = update_balance(interaction.user.id, winnings)
        embed = discord.Embed(title="🪙 Coinflip - YOU WON!", color=0x00ff00)
        embed.add_field(name="Your Choice", value=choice.title(), inline=True)
        embed.add_field(name="Result", value=f"🪙 {result.title()}", inline=True)
        embed.add_field(name="Winnings", value=f"+{winnings:,} 🪙", inline=True)
    else:
        new_balance = update_balance(interaction.user.id, -amount)
        embed = discord.Embed(title="🪙 Coinflip - YOU LOST!", color=0xff4444)
        embed.add_field(name="Your Choice", value=choice.title(), inline=True)
        embed.add_field(name="Result", value=f"🪙 {result.title()}", inline=True)
        embed.add_field(name="Lost", value=f"-{amount:,} 🪙", inline=True)
    
    embed.add_field(name="New Balance", value=f"{new_balance:,} 🪙", inline=False)
    embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
    
    set_short_cooldown(interaction.user.id, "coinflip")
    await save_data()
    
    await log_action(
        "COINFLIP",
        f"🪙 Coinflip {'Win' if won else 'Loss'}",
        f"{interaction.user.mention} {'won' if won else 'lost'} **{amount:,} tokens** on coinflip",
        color=0x00ff00 if won else 0xff4444,
        user=interaction.user,
        fields=[
            {"name": "Bet Amount", "value": f"{amount:,} 🪙", "inline": True},
            {"name": "Choice", "value": choice.title(), "inline": True},
            {"name": "Result", "value": result.title(), "inline": True},
            {"name": "Outcome", "value": "Won" if won else "Lost", "inline": True}
        ]
    )
    
    await interaction.response.send_message(embed=embed)

class DuelAcceptView(discord.ui.View):
    def __init__(self, challenger_id, challenged_id, amount):
        super().__init__(timeout=60)
        self.challenger_id = challenger_id
        self.challenged_id = challenged_id
        self.amount = amount
    
    @discord.ui.button(label="✅ Accept Duel", style=discord.ButtonStyle.green)
    async def accept_duel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.challenged_id:
            await interaction.response.send_message("❌ This duel is not for you!", ephemeral=True)
            return
        
        challenger_balance = get_user_balance(self.challenger_id)
        challenged_balance = get_user_balance(self.challenged_id)
        
        if challenger_balance < self.amount:
            await interaction.response.send_message("❌ The challenger no longer has enough tokens!", ephemeral=True)
            return
        
        if challenged_balance < self.amount:
            await interaction.response.send_message(f"❌ You don't have enough tokens! Need {self.amount - challenged_balance:,} more.", ephemeral=True)
            return
        
        duel_key = f"{self.challenger_id}_{self.challenged_id}"
        if duel_key in pending_duels:
            del pending_duels[duel_key]
        
        winner_id = random.choice([self.challenger_id, self.challenged_id])
        loser_id = self.challenged_id if winner_id == self.challenger_id else self.challenger_id
        
        update_balance(winner_id, self.amount)
        update_balance(loser_id, -self.amount)
        await save_data()
        
        winner = bot.get_user(winner_id)
        loser = bot.get_user(loser_id)
        challenger = bot.get_user(self.challenger_id)
        challenged = bot.get_user(self.challenged_id)
        
        embed = discord.Embed(title="⚔️ Duel Complete!", color=0xFFD700)
        embed.add_field(name="Winner", value=f"🏆 {winner.mention}", inline=True)
        embed.add_field(name="Loser", value=f"💀 {loser.mention}", inline=True)
        embed.add_field(name="Amount", value=f"{self.amount:,} 🪙", inline=True)
        embed.add_field(name="Winner's Balance", value=f"{get_user_balance(winner_id):,} 🪙", inline=True)
        embed.add_field(name="Loser's Balance", value=f"{get_user_balance(loser_id):,} 🪙", inline=True)
        embed.add_field(name="‎", value="‎", inline=True)
        
        embed.set_footer(text="The coin has decided!")
        
        await log_action(
            "DUEL",
            "⚔️ Duel Completed",
            f"Duel between {challenger.mention} and {challenged.mention}",
            color=0xFFD700,
            user=winner,
            fields=[
                {"name": "Challenger", "value": challenger.mention, "inline": True},
                {"name": "Challenged", "value": challenged.mention, "inline": True},
                {"name": "Amount", "value": f"{self.amount:,} 🪙", "inline": True},
                {"name": "Winner", "value": winner.mention, "inline": True}
            ]
        )
        
        await interaction.response.edit_message(embed=embed, view=None)
    
    @discord.ui.button(label="❌ Decline Duel", style=discord.ButtonStyle.red)
    async def decline_duel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.challenged_id:
            await interaction.response.send_message("❌ This duel is not for you!", ephemeral=True)
            return
        
        duel_key = f"{self.challenger_id}_{self.challenged_id}"
        if duel_key in pending_duels:
            del pending_duels[duel_key]
        
        challenger = bot.get_user(self.challenger_id)
        embed = discord.Embed(
            title="❌ Duel Declined", 
            description=f"{interaction.user.mention} declined the duel challenge from {challenger.mention}.",
            color=0xff4444
        )
        
        await interaction.response.edit_message(embed=embed, view=None)

@bot.tree.command(name="duel", description="Challenge another user to a coinflip duel")
async def duel(interaction: discord.Interaction, user: discord.Member, amount: int):
    if not can_use_short_cooldown(interaction.user.id, "duel", 10):
        await interaction.response.send_message("⏰ Please wait 10 seconds between duel challenges!", ephemeral=True)
        return
    
    if amount <= 0:
        await interaction.response.send_message("❌ Duel amount must be greater than 0!", ephemeral=True)
        return
    
    if user.id == interaction.user.id:
        await interaction.response.send_message("❌ You can't duel yourself!", ephemeral=True)
        return
    
    if user.bot:
        await interaction.response.send_message("❌ You can't duel bots!", ephemeral=True)
        return
    
    challenger_balance = get_user_balance(interaction.user.id)
    if challenger_balance < amount:
        await interaction.response.send_message(f"❌ You need **{amount - challenger_balance:,}** more tokens to make this challenge!", ephemeral=True)
        return
    
    challenged_balance = get_user_balance(user.id)
    if challenged_balance < amount:
        await interaction.response.send_message(f"❌ {user.mention} doesn't have enough tokens for this duel! They need {amount - challenged_balance:,} more.", ephemeral=True)
        return
    
    duel_key = f"{interaction.user.id}_{user.id}"
    reverse_duel_key = f"{user.id}_{interaction.user.id}"
    
    if duel_key in pending_duels or reverse_duel_key in pending_duels:
        await interaction.response.send_message("❌ There's already a pending duel between you two!", ephemeral=True)
        return
    
    pending_duels[duel_key] = {
        'challenger': interaction.user.id,
        'challenged': user.id,
        'amount': amount,
        'created_at': datetime.now()
    }
    
    set_short_cooldown(interaction.user.id, "duel")
    
    embed = discord.Embed(
        title="⚔️ Duel Challenge!",
        description=f"{interaction.user.mention} challenges {user.mention} to a duel!",
        color=0xFFD700
    )
    
    embed.add_field(name="💰 Stakes", value=f"{amount:,} 🪙", inline=True)
    embed.add_field(name="🎯 Rules", value="Winner takes all!\nCoinflip decides the victor", inline=True)
    embed.add_field(name="⏰ Expires", value="60 seconds", inline=True)
    
    embed.add_field(name="💪 Challenger Balance", value=f"{challenger_balance:,} 🪙", inline=True)
    embed.add_field(name="🎲 Challenged Balance", value=f"{challenged_balance:,} 🪙", inline=True)
    embed.add_field(name="‎", value="‎", inline=True)
    
    embed.set_footer(text=f"{user.display_name}, will you accept this challenge?")
    
    view = DuelAcceptView(interaction.user.id, user.id, amount)
    await interaction.response.send_message(embed=embed, view=view)

@bot.tree.command(name="gift", description="Gift tokens to another user (max 3k per day)")
async def gift(interaction: discord.Interaction, user: discord.Member, amount: int):
    if not can_use_short_cooldown(interaction.user.id, "gift", 3):
        await interaction.response.send_message("⏰ Please wait 3 seconds between gifts!", ephemeral=True)
        return
    
    if amount <= 0:
        await interaction.response.send_message("❌ Amount must be greater than 0!", ephemeral=True)
        return
    
    if amount > 3000:
        await interaction.response.send_message("❌ You can only gift up to 3,000 tokens per day!", ephemeral=True)
        return
    
    if user.id == interaction.user.id:
        await interaction.response.send_message("❌ Can't gift to yourself!", ephemeral=True)
        return
    
    if user.bot:
        await interaction.response.send_message("❌ Can't gift to bots!", ephemeral=True)
        return
    
    # Check daily gift limit
    user_id = str(interaction.user.id)
    today = datetime.now().date().isoformat()
    
    if user_id not in giveaway_daily_totals:
        giveaway_daily_totals[user_id] = {}
    
    if today not in giveaway_daily_totals[user_id]:
        giveaway_daily_totals[user_id][today] = 0
    
    if giveaway_daily_totals[user_id][today] + amount > 3000:
        remaining = 3000 - giveaway_daily_totals[user_id][today]
        await interaction.response.send_message(f"❌ You can only gift {remaining:,} more tokens today!", ephemeral=True)
        return
    
    giver_balance = get_user_balance(interaction.user.id)
    if giver_balance < amount:
        await interaction.response.send_message(f"❌ Need **{amount - giver_balance:,}** more tokens!", ephemeral=True)
        return
    
    update_balance(interaction.user.id, -amount)
    update_balance(user.id, amount)
    giveaway_daily_totals[user_id][today] += amount
    set_short_cooldown(interaction.user.id, "gift")
    await save_data()
    
    await log_action(
        "GIFT",
        "🎁 Token Gift",
        f"{interaction.user.mention} gifted **{amount:,} tokens** to {user.mention}",
        color=0xffb347,
        user=interaction.user,
        fields=[
            {"name": "Giver", "value": interaction.user.mention, "inline": True},
            {"name": "Receiver", "value": user.mention, "inline": True},
            {"name": "Amount", "value": f"{amount:,} 🪙", "inline": True},
            {"name": "Daily Total", "value": f"{giveaway_daily_totals[user_id][today]:,}/3,000 🪙", "inline": True}
        ]
    )
    
    message = f"🎁 {interaction.user.mention} gifted **{amount:,} tokens** 🪙 to {user.mention}! 🎉"
    await interaction.response.send_message(message)

# Purchase confirmation view
class PurchaseConfirmView(discord.ui.View):
    def __init__(self, item, user_id):
        super().__init__(timeout=60)
        self.item = item
        self.user_id = user_id
    
    @discord.ui.button(label="✅ Confirm Purchase", style=discord.ButtonStyle.green)
    async def confirm_purchase(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ This is not your purchase!", ephemeral=True)
            return
        
        balance = get_user_balance(interaction.user.id)
        if balance < self.item['price']:
            await interaction.response.send_message(
                f"❌ Insufficient funds! You need **{self.item['price'] - balance:,}** more tokens.",
                ephemeral=True
            )
            return
        
        new_balance = update_balance(interaction.user.id, -self.item['price'])
        await save_data()
        
        # Log the purchase
        await log_purchase(interaction.user, self.item['name'], self.item['price'])
        
        embed = discord.Embed(title="✅ Purchase Successful!", color=0x00ff00)
        embed.add_field(name="Item", value=self.item['name'], inline=True)
        embed.add_field(name="Cost", value=f"{self.item['price']:,} 🪙", inline=True)
        embed.add_field(name="New Balance", value=f"{new_balance:,} 🪙", inline=True)
        
        if self.item.get('description'):
            embed.add_field(name="Description", value=self.item['description'], inline=False)
        
        embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
        await interaction.response.edit_message(embed=embed, view=None)
    
    @discord.ui.button(label="❌ Cancel", style=discord.ButtonStyle.red)
    async def cancel_purchase(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ This is not your purchase!", ephemeral=True)
            return
        
        embed = discord.Embed(title="❌ Purchase Cancelled", description="Your purchase has been cancelled.", color=0xff4444)
        await interaction.response.edit_message(embed=embed, view=None)

# Shop view with buttons
class ShopView(discord.ui.View):
    def __init__(self, user_balance):
        super().__init__(timeout=300)
        self.user_balance = user_balance
        
        for i, item in enumerate(shop_data[:25]):
            affordable = user_balance >= item['price']
            button = discord.ui.Button(
                label=f"{item['name']} - {item['price']:,}🪙",
                style=discord.ButtonStyle.green if affordable else discord.ButtonStyle.grey,
                disabled=not affordable,
                custom_id=f"buy_{i}"
            )
            button.callback = self.create_buy_callback(i)
            self.add_item(button)
    
    def create_buy_callback(self, item_index):
        async def buy_callback(interaction):
            await self.show_purchase_confirmation(interaction, item_index)
        return buy_callback
    
    async def show_purchase_confirmation(self, interaction, item_index):
        if item_index >= len(shop_data):
            await interaction.response.send_message("❌ Invalid item!", ephemeral=True)
            return
        
        item = shop_data[item_index]
        balance = get_user_balance(interaction.user.id)
        
        if balance < item['price']:
            await interaction.response.send_message(
                f"❌ Insufficient funds! You need **{item['price'] - balance:,}** more tokens.",
                ephemeral=True
            )
            return
        
        embed = discord.Embed(title="🛒 Purchase Confirmation", color=0xFFD700)
        embed.add_field(name="Item", value=item['name'], inline=True)
        embed.add_field(name="Cost", value=f"{item['price']:,} 🪙", inline=True)
        embed.add_field(name="Your Balance", value=f"{balance:,} 🪙", inline=True)
        embed.add_field(name="Balance After", value=f"{balance - item['price']:,} 🪙", inline=True)
        
        if item.get('description'):
            embed.add_field(name="Description", value=item['description'], inline=False)
        
        embed.set_footer(text="Are you sure you want to buy this item?")
        
        view = PurchaseConfirmView(item, interaction.user.id)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

@bot.tree.command(name="shop", description="Browse the token shop")
async def shop(interaction: discord.Interaction):
    balance = get_user_balance(interaction.user.id)
    
    embed = discord.Embed(title="🛒 Token Shop", color=0x0099ff)
    embed.add_field(name="Your Balance", value=f"**{balance:,}** 🪙", inline=False)
    
    if not shop_data:
        embed.description = "🚫 No items available!"
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    items_text = ""
    for item in shop_data[:10]:
        affordable = "✅" if balance >= item['price'] else "❌"
        items_text += f"{affordable} **{item['name']}** - {item['price']:,} 🪙\n"
        if item.get('description'):
            items_text += f"    *{item['description'][:50]}{'...' if len(item['description']) > 50 else ''}*\n"
        items_text += "\n"
    
    embed.add_field(name="Available Items", value=items_text, inline=False)
    embed.set_footer(text="Click the buttons below to purchase items!")
    
    view = ShopView(balance)
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

@bot.tree.command(name="buy", description="Buy an item from the shop")
async def buy(interaction: discord.Interaction, item_name: str, quantity: int = 1):
    # Check 3 second cooldown
    if not can_use_short_cooldown(interaction.user.id, "buy", 3):
        await interaction.response.send_message("⏰ Please wait 3 seconds between purchases!", ephemeral=True)
        return
    
    if quantity <= 0:
        await interaction.response.send_message("❌ Quantity must be at least 1!", ephemeral=True)
        return
    
    # Find the item
    item = None
    for shop_item in shop_data:
        if shop_item['name'].lower() == item_name.lower():
            item = shop_item
            break
    
    if not item:
        similar = [i['name'] for i in shop_data if item_name.lower() in i['name'].lower()]
        error_msg = f"❌ Item **{item_name}** not found!"
        if similar:
            error_msg += f"\n\nDid you mean: {', '.join(similar[:3])}"
        await interaction.response.send_message(error_msg, ephemeral=True)
        return
    
    balance = get_user_balance(interaction.user.id)
    total_cost = item['price'] * quantity
    
    if balance < total_cost:
        await interaction.response.send_message(
            f"❌ Insufficient funds!\n"
            f"**Cost:** {total_cost:,} 🪙 ({item['price']:,} × {quantity})\n"
            f"**Your Balance:** {balance:,} 🪙\n"
            f"**Need:** {total_cost - balance:,} more tokens",
            ephemeral=True
        )
        return
    
    # Purchase successful
    new_balance = update_balance(interaction.user.id, -total_cost)
    set_short_cooldown(interaction.user.id, "buy")
    await save_data()
    
    # Log the purchase
    await log_purchase(interaction.user, item['name'], item['price'], quantity)
    
    embed = discord.Embed(title="✅ Purchase Successful!", color=0x00ff00)
    embed.add_field(name="Item", value=item['name'], inline=True)
    embed.add_field(name="Quantity", value=str(quantity), inline=True)
    embed.add_field(name="Total Cost", value=f"{total_cost:,} 🪙", inline=True)
    embed.add_field(name="New Balance", value=f"{new_balance:,} 🪙", inline=False)
    
    if item.get('description'):
        embed.add_field(name="Description", value=item['description'], inline=False)
    
    embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
    await interaction.response.send_message(embed=embed, ephemeral=True)

# Shop management modals and views
class AddItemModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="Add Shop Item")
    
    name = discord.ui.TextInput(label="Item Name")
    price = discord.ui.TextInput(label="Price")
    description = discord.ui.TextInput(label="Description", required=False, style=discord.TextStyle.long)
    
    async def on_submit(self, interaction: discord.Interaction):
        if not is_admin(interaction.user):
            await interaction.response.send_message("❌ Admin only!", ephemeral=True)
            return
            
        try:
            price_val = int(self.price.value)
            if price_val <= 0:
                await interaction.response.send_message("❌ Price must be positive!", ephemeral=True)
                return
        except:
            await interaction.response.send_message("❌ Invalid price!", ephemeral=True)
            return
        
        for item in shop_data:
            if item['name'].lower() == self.name.value.lower():
                await interaction.response.send_message("❌ Item already exists!", ephemeral=True)
                return
        
        new_item = {
            'name': self.name.value,
            'price': price_val,
            'description': self.description.value or ""
        }
        
        shop_data.append(new_item)
        await save_data()
        
        # Log shop item addition
        await log_action(
            "SHOP_ADD",
            "🛒 Shop Item Added",
            f"**{interaction.user.mention}** added new item to shop",
            color=0x00ff00,
            user=interaction.user,
            fields=[
                {"name": "Item Name", "value": new_item['name'], "inline": True},
                {"name": "Price", "value": f"{new_item['price']:,} 🪙", "inline": True},
                {"name": "Description", "value": new_item['description'] or "No description", "inline": False}
            ]
        )
        
        embed = discord.Embed(title="✅ Item Added!", color=0x00ff00)
        embed.add_field(name="Name", value=new_item['name'], inline=False)
        embed.add_field(name="Price", value=f"{new_item['price']:,} 🪙", inline=False)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

class UpdateItemModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="Update Shop Item")
    
    item_number = discord.ui.TextInput(label="Item Number", placeholder="Enter number (1, 2, 3...)")
    name = discord.ui.TextInput(label="New Name (optional)", required=False)
    price = discord.ui.TextInput(label="New Price (optional)", required=False)
    description = discord.ui.TextInput(label="New Description (optional)", required=False, style=discord.TextStyle.long)
    
    async def on_submit(self, interaction: discord.Interaction):
        if not is_admin(interaction.user):
            await interaction.response.send_message("❌ Admin only!", ephemeral=True)
            return
            
        try:
            item_idx = int(self.item_number.value) - 1
            if item_idx < 0 or item_idx >= len(shop_data):
                await interaction.response.send_message(f"❌ Invalid item number! Must be 1-{len(shop_data)}", ephemeral=True)
                return
        except:
            await interaction.response.send_message("❌ Item number must be a valid number!", ephemeral=True)
            return
        
        if self.name.value.strip():
            for i, item in enumerate(shop_data):
                if i != item_idx and item['name'].lower() == self.name.value.lower():
                    await interaction.response.send_message("❌ Item with this name already exists!", ephemeral=True)
                    return
            shop_data[item_idx]['name'] = self.name.value.strip()
        
        if self.price.value.strip():
            try:
                new_price = int(self.price.value)
                if new_price <= 0:
                    await interaction.response.send_message("❌ Price must be greater than 0!", ephemeral=True)
                    return
                shop_data[item_idx]['price'] = new_price
            except:
                await interaction.response.send_message("❌ Price must be a valid number!", ephemeral=True)
                return
            
        
        if self.description.value.strip():
            shop_data[item_idx]['description'] = self.description.value.strip()
        
        await save_data()
        
        # Log shop item update
        await log_action(
            "SHOP_UPDATE",
            "✏️ Shop Item Updated",
            f"**{interaction.user.mention}** updated shop item",
            color=0x0099ff,
            user=interaction.user,
            fields=[
                {"name": "Item", "value": shop_data[item_idx]['name'], "inline": True},
                {"name": "Price", "value": f"{shop_data[item_idx]['price']:,} 🪙", "inline": True},
                {"name": "Changes Made", "value": "Updated item properties", "inline": False}
            ]
        )
        
        embed = discord.Embed(title="✅ Item Updated!", color=0x0099ff)
        embed.add_field(name="Item", value=shop_data[item_idx]['name'], inline=True)
        embed.add_field(name="Price", value=f"{shop_data[item_idx]['price']:,} 🪙", inline=True)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

class DeleteItemModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="Delete Shop Item")
    
    item_number = discord.ui.TextInput(label="Item Number", placeholder="Enter number (1, 2, 3...)")
    confirmation = discord.ui.TextInput(label="Type 'DELETE' to confirm", placeholder="This cannot be undone!")
    
    async def on_submit(self, interaction: discord.Interaction):
        if not is_admin(interaction.user):
            await interaction.response.send_message("❌ Admin only!", ephemeral=True)
            return
            
        if self.confirmation.value.upper() != "DELETE":
            await interaction.response.send_message("❌ You must type 'DELETE' to confirm!", ephemeral=True)
            return
        
        try:
            item_idx = int(self.item_number.value) - 1
            if item_idx < 0 or item_idx >= len(shop_data):
                await interaction.response.send_message(f"❌ Invalid item number! Must be 1-{len(shop_data)}", ephemeral=True)
                return
        except:
            await interaction.response.send_message("❌ Item number must be a valid number!", ephemeral=True)
            return
        
        deleted_item = shop_data.pop(item_idx)
        await save_data()
        
        # Log shop item deletion
        await log_action(
            "SHOP_DELETE",
            "🗑️ Shop Item Deleted",
            f"**{interaction.user.mention}** deleted shop item",
            color=0xff4444,
            user=interaction.user,
            fields=[
                {"name": "Deleted Item", "value": deleted_item['name'], "inline": True},
                {"name": "Price", "value": f"{deleted_item['price']:,} 🪙", "inline": True},
                {"name": "Description", "value": deleted_item.get('description', 'No description'), "inline": False}
            ]
        )
        
        embed = discord.Embed(title="✅ Item Deleted!", color=0xff4444)
        embed.add_field(name="Deleted Item", value=deleted_item['name'], inline=True)
        embed.add_field(name="Price", value=f"{deleted_item['price']:,} 🪙", inline=True)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

class ShopManageView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)
    
    @discord.ui.button(label="➕ Add Item", style=discord.ButtonStyle.green)
    async def add_item(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_admin(interaction.user):
            await interaction.response.send_message("❌ Admin only!", ephemeral=True)
            return
        await interaction.response.send_modal(AddItemModal())
    
    @discord.ui.button(label="✏️ Update Item", style=discord.ButtonStyle.blurple)
    async def update_item(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_admin(interaction.user):
            await interaction.response.send_message("❌ Admin only!", ephemeral=True)
            return
        
        if not shop_data:
            await interaction.response.send_message("❌ No items in shop to update!", ephemeral=True)
            return
        
        await interaction.response.send_modal(UpdateItemModal())
    
    @discord.ui.button(label="🗑️ Delete Item", style=discord.ButtonStyle.red)
    async def delete_item(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_admin(interaction.user):
            await interaction.response.send_message("❌ Admin only!", ephemeral=True)
            return
        
        if not shop_data:
            await interaction.response.send_message("❌ No items in shop to delete!", ephemeral=True)
            return
        
        await interaction.response.send_modal(DeleteItemModal())

@bot.tree.command(name="addshop", description="Manage shop (Admin only)")
async def addshop(interaction: discord.Interaction):
    if not is_admin(interaction.user):
        await interaction.response.send_message("❌ Admin only!", ephemeral=True)
        return
    
    embed = discord.Embed(title="🛍️ Shop Management", color=0xff9900)
    embed.add_field(name="📊 Stats", value=f"**Items:** {len(shop_data)}\n**Status:** {'Active' if shop_data else 'Empty'}", inline=True)
    
    if shop_data:
        total_value = sum(item['price'] for item in shop_data)
        cheapest = min(shop_data, key=lambda x: x['price'])
        most_expensive = max(shop_data, key=lambda x: x['price'])
        
        embed.add_field(
            name="💰 Price Range", 
            value=f"**Cheapest:** {cheapest['price']:,} 🪙\n**Most Expensive:** {most_expensive['price']:,} 🪙\n**Total Value:** {total_value:,} 🪙", 
            inline=True
        )
        
        items_list = "\n".join([f"{i+1}. **{item['name']}** - {item['price']:,} 🪙" for i, item in enumerate(shop_data[:10])])
        if len(shop_data) > 10:
            items_list += f"\n... and {len(shop_data) - 10} more items"
        embed.add_field(name="🛒 Current Items", value=items_list, inline=False)
    else:
        embed.add_field(name="🛒 Current Items", value="*No items in shop*", inline=False)
    
    embed.add_field(
        name="🔧 Available Actions",
        value="• **Add Item** - Create new shop items\n• **Update Item** - Modify existing items\n• **Delete Item** - Remove items from shop",
        inline=False
    )
    
    embed.set_footer(text="Use the buttons below to manage the shop")
    
    view = ShopManageView()
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

class ResetConfirmView(discord.ui.View):
    def __init__(self, original_user_id):
        super().__init__(timeout=30)
        self.original_user_id = original_user_id
    
    @discord.ui.button(label="🗑️ YES, RESET ALL DATA", style=discord.ButtonStyle.danger)
    async def confirm_reset(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.original_user_id:
            await interaction.response.send_message("❌ Only the command user can confirm!", ephemeral=True)
            return
        
        # Reset all data
        global user_data, cooldowns
        user_data.clear()
        cooldowns = {"daily": {}, "work": {}, "crime": {}, "gift": {}, "buy": {}, "coinflip": {}, "duel": {}, "giveaway": {}}
        await save_data()
        
        success_embed = discord.Embed(
            title="✅ Data Reset Complete",
            description="All user data has been permanently deleted.\nUsers will start fresh with 0 tokens.",
            color=0x00ff00
        )
        success_embed.set_footer(text=f"Reset by {interaction.user.display_name}")
        
        await interaction.response.edit_message(embed=success_embed, view=None)
        
        # Log data reset action
        await log_action(
            "DATA_RESET",
            "🗑️ All Data Reset",
            f"**{interaction.user.mention}** performed a complete data reset",
            color=0xff0000,
            user=interaction.user,
            fields=[
                {"name": "Action", "value": "All user data deleted", "inline": True},
                {"name": "Users Affected", "value": "All server members", "inline": True},
                {"name": "Reset Time", "value": f"<t:{int(datetime.now().timestamp())}:F>", "inline": False}
            ]
        )
    
    @discord.ui.button(label="❌ Cancel", style=discord.ButtonStyle.secondary)
    async def cancel_reset(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.original_user_id:
            await interaction.response.send_message("❌ Only the command user can cancel!", ephemeral=True)
            return
        
        cancel_embed = discord.Embed(
            title="❌ Reset Cancelled",
            description="Data reset has been cancelled. All user data remains intact.",
            color=0x808080
        )
        
        await interaction.response.edit_message(embed=cancel_embed, view=None)

@bot.tree.command(name="resetdata", description="Reset all user data (Admin only)")
async def resetdata(interaction: discord.Interaction, confirmation_code: str):
    if not is_admin(interaction.user):
        await interaction.response.send_message("❌ Admin only!", ephemeral=True)
        return
    
    if confirmation_code != "BgH7459njrYEy7":
        await interaction.response.send_message("❌ Invalid confirmation code!", ephemeral=True)
        return
    
    # Ask for final confirmation
    embed = discord.Embed(
        title="⚠️ DATA RESET CONFIRMATION",
        description="**Are you absolutely sure you want to reset ALL user data?**\n\n"
                   "This will permanently delete:\n"
                   "• All user balances\n"
                   "• All earning/spending history\n"
                   "• All cooldown timers\n"
                   "• Purchase records\n\n"
                   "**THIS CANNOT BE UNDONE!**",
        color=0xff0000
    )
    
    view = ResetConfirmView(interaction.user.id)
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

@bot.tree.command(name="leaderboard", description="View the top token holders")
async def leaderboard(interaction: discord.Interaction, page: int = 1):
    if not user_data:
        embed = discord.Embed(
            title="📊 Token Leaderboard",
            description="No users have earned tokens yet!",
            color=0x0099ff
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    sorted_users = []
    for user_id, data in user_data.items():
        balance = data.get('balance', 0)
        if balance > 0:
            try:
                user = bot.get_user(int(user_id))
                if user:
                    sorted_users.append({
                        'user': user,
                        'balance': balance,
                        'rank': get_rank(balance)
                    })
            except:
                continue
    
    sorted_users.sort(key=lambda x: x['balance'], reverse=True)
    
    if not sorted_users:
        embed = discord.Embed(
            title="📊 Token Leaderboard",
            description="No users with tokens found!",
            color=0x0099ff
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    per_page = 10
    max_pages = (len(sorted_users) + per_page - 1) // per_page
    page = max(1, min(page, max_pages))
    
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    page_users = sorted_users[start_idx:end_idx]
    
    embed = discord.Embed(
        title="📊 Token Leaderboard",
        color=0xFFD700,
        timestamp=datetime.now()
    )
    
    leaderboard_text = ""
    for i, user_data_item in enumerate(page_users, start=start_idx + 1):
        user = user_data_item['user']
        balance = user_data_item['balance']
        rank = user_data_item['rank']
        
        if i == 1:
            medal = "🥇"
        elif i == 2:
            medal = "🥈"
        elif i == 3:
            medal = "🥉"
        else:
            medal = f"**{i}.**"
        
        leaderboard_text += f"{medal} **{user.display_name}** - {balance:,} 🪙 {rank}\n"
    
    embed.add_field(name="Rankings", value=leaderboard_text, inline=False)
    
    user_position = None
    for i, user_data_item in enumerate(sorted_users, 1):
        if user_data_item['user'].id == interaction.user.id:
            user_position = i
            break
    
    if user_position and (user_position < start_idx + 1 or user_position > end_idx):
        user_balance = get_user_balance(interaction.user.id)
        user_rank = get_rank(user_balance)
        embed.add_field(
            name="Your Position",
            value=f"**#{user_position}** - {user_balance:,} 🪙 {user_rank}",
            inline=False
        )
    
    embed.set_footer(text=f"Page {page}/{max_pages} • {len(sorted_users)} total users")
    
    await interaction.response.send_message(embed=embed, ephemeral=False)

@bot.tree.command(name="adminbalance", description="Check user balance (Admin only)")
async def adminbalance(interaction: discord.Interaction, user: discord.Member):
    if not is_admin(interaction.user):
        await interaction.response.send_message("❌ Admin only!", ephemeral=True)
        return
    
    user_id = str(user.id)
    balance = get_user_balance(user.id)
    data = user_data.get(user_id, {})
    earned = data.get('total_earned', 0)
    spent = data.get('total_spent', 0)
    rank = get_rank(balance)
    
    embed = discord.Embed(title=f"💰 {user.display_name}'s Wallet", color=0xFF6B6B)
    embed.add_field(name="Balance", value=f"**{balance:,}** 🪙", inline=True)
    embed.add_field(name="Rank", value=rank, inline=True)
    embed.add_field(name="Spent", value=f"{spent:,} 🪙", inline=True)
    embed.add_field(name="Earned", value=f"{earned:,} 🪙", inline=True)
    embed.set_author(name=user.display_name, icon_url=user.display_avatar.url)
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="addtoken", description="Add tokens (Admin only)")
async def addtoken(interaction: discord.Interaction, user: discord.Member, amount: int):
    if not is_admin(interaction.user):
        await interaction.response.send_message("❌ Admin only!", ephemeral=True)
        return
    
    if amount <= 0:
        await interaction.response.send_message("❌ Amount must be positive!", ephemeral=True)
        return
    
    new_balance = update_balance(user.id, amount)
    await save_data()
    
    await log_action(
        "ADD_TOKENS",
        "💰 Tokens Added",
        f"**{interaction.user.mention}** added **{amount:,} tokens** to {user.mention}",
        color=0x00ff00,
        user=interaction.user,
        fields=[
            {"name": "Target User", "value": user.mention, "inline": True},
            {"name": "Amount Added", "value": f"{amount:,} 🪙", "inline": True},
            {"name": "New Balance", "value": f"{new_balance:,} 🪙", "inline": True}
        ]
    )
    
    embed = discord.Embed(title="✅ Tokens Added", color=0x00ff00)
    embed.add_field(name="User", value=user.mention, inline=True)
    embed.add_field(name="Added", value=f"{amount:,} 🪙", inline=True)
    embed.add_field(name="New Balance", value=f"{new_balance:,} 🪙", inline=True)
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="removetoken", description="Remove tokens from a user (Admin only)")
async def removetoken(interaction: discord.Interaction, user: discord.Member, amount: int):
    if not is_admin(interaction.user):
        await interaction.response.send_message("❌ Admin only!", ephemeral=True)
        return
    
    if amount <= 0:
        await interaction.response.send_message("❌ Amount must be positive!", ephemeral=True)
        return
    
    current_balance = get_user_balance(user.id)
    if current_balance < amount:
        await interaction.response.send_message(
            f"❌ User only has {current_balance:,} tokens! Cannot remove {amount:,} tokens.",
            ephemeral=True
        )
        return
    
    new_balance = update_balance(user.id, -amount)
    await save_data()
    
    await log_action(
        "REMOVE_TOKENS",
        "💰 Tokens Removed",
        f"**{interaction.user.mention}** removed **{amount:,} tokens** from {user.mention}",
        color=0xff4444,
        user=interaction.user,
        fields=[
            {"name": "Target User", "value": user.mention, "inline": True},
            {"name": "Amount Removed", "value": f"{amount:,} 🪙", "inline": True},
            {"name": "New Balance", "value": f"{new_balance:,} 🪙", "inline": True}
        ]
    )
    
    embed = discord.Embed(title="✅ Tokens Removed", color=0xff4444)
    embed.add_field(name="User", value=user.mention, inline=True)
    embed.add_field(name="Removed", value=f"{amount:,} 🪙", inline=True)
    embed.add_field(name="New Balance", value=f"{new_balance:,} 🪙", inline=True)
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

# Giveaway entry button
class GiveawayEnterView(discord.ui.View):
    def __init__(self, giveaway_id):
        super().__init__(timeout=25)  # 25 second timeout
        self.giveaway_id = giveaway_id
    
    @discord.ui.button(label="🎉 Enter Giveaway", style=discord.ButtonStyle.green, emoji="🎉")
    async def enter_giveaway(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.giveaway_id not in active_giveaways:
            await interaction.response.send_message("❌ This giveaway has ended!", ephemeral=True)
            return
        
        giveaway = active_giveaways[self.giveaway_id]
        
        # Check if user already entered
        if str(interaction.user.id) in giveaway['entries']:
            await interaction.response.send_message("❌ You've already entered this giveaway!", ephemeral=True)
            return
        
        # Calculate entries based on roles
        entries = 1  # Base entry
        
        # Add bonus entries for special roles
        for role_id, bonus_entries in PRIORITY_ROLES.items():
            if any(role.id == role_id for role in interaction.user.roles):
                entries += bonus_entries
        
        # Add user to entries
        giveaway['entries'][str(interaction.user.id)] = entries
        giveaway['total_entries'] += entries
        
        await save_data()
        
        role_bonus_text = ""
        for role_id, bonus_entries in PRIORITY_ROLES.items():
            if any(role.id == role_id for role in interaction.user.roles):
                role_bonus_text += f"• <@&{role_id}>: +{bonus_entries} entries\n"
        
        if role_bonus_text:
            bonus_message = f"\n**Role Bonuses:**\n{role_bonus_text}"
        else:
            bonus_message = ""
        
        await interaction.response.send_message(
            f"✅ You've entered the giveaway with **{entries}** entries! Good luck!{bonus_message}",
            ephemeral=True
        )

@bot.tree.command(name="giveaway", description="Start a token giveaway (15 seconds)")
async def giveaway(interaction: discord.Interaction, amount: int, winners: int):
    # Check cooldown
    if not can_use_short_cooldown(interaction.user.id, "giveaway", 15):
    await interaction.response.send_message("⏰ Please wait **{time_left}** before starting another giveaway!", ephemeral=True)
    return
    
# Validate parameters
if amount < 50:
    await interaction.response.send_message("❌ Giveaway amount must be at least 50 tokens!", ephemeral=True)
    return
    
    if amount > 5000:
        await interaction.response.send_message("❌ Maximum giveaway amount is 5,000 tokens!", ephemeral=True)
        return
    
    if winners < 1 or winners > 12:
        await interaction.response.send_message("❌ Number of winners must be between 1 and 12!", ephemeral=True)
        return
    
    # Check daily giveaway limit (50k per user)
    user_id = str(interaction.user.id)
    today = datetime.now().date().isoformat()
    
    if user_id not in giveaway_daily_totals:
        giveaway_daily_totals[user_id] = {}
    
    if today not in giveaway_daily_totals[user_id]:
        giveaway_daily_totals[user_id][today] = 0
    
    if giveaway_daily_totals[user_id][today] + amount > 50000:
        remaining = 50000 - giveaway_daily_totals[user_id][today]
        await interaction.response.send_message(
            f"❌ You can only giveaway {remaining:,} more tokens today! (50k daily limit)",
            ephemeral=True
        )
        return
    
    # Check if user has enough tokens
    balance = get_user_balance(interaction.user.id)
    if balance < amount:
        await interaction.response.send_message(f"❌ You need **{amount - balance:,}** more tokens to start this giveaway!", ephemeral=True)
        return
    
    # Deduct tokens from user
    new_balance = update_balance(interaction.user.id, -amount)
    giveaway_daily_totals[user_id][today] += amount
    set_short_cooldown(interaction.user.id, "giveaway")
    
    # Create giveaway
    giveaway_id = f"{interaction.user.id}_{int(time.time())}"
    prize_per_winner = amount // winners
    
    active_giveaways[giveaway_id] = {
        'creator': interaction.user.id,
        'amount': amount,
        'winners': winners,
        'prize_per_winner': prize_per_winner,
        'entries': {},
        'total_entries': 0,
        'created_at': datetime.now().isoformat(),
        'end_time': (datetime.now() + timedelta(seconds=25)).isoformat()
    }
    
    await save_data()
    
    # Create embed with improved UI
    embed = discord.Embed(
        title="🎉 TOKEN GIVEAWAY 🎉",
        description=f"Hosted by {interaction.user.mention}",
        color=0xFFD700,
        timestamp=datetime.now()
    )
    
    # Add thumbnail
    embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/1125274830004781156.webp?size=96&quality=lossless")
    
    # Main prize info
    embed.add_field(
        name="🏆 TOTAL PRIZE", 
        value=f"**{amount:,}** 🪙", 
        inline=True
    )
    embed.add_field(
        name="👑 WINNERS", 
        value=f"**{winners}** lucky winners", 
        inline=True
    )
    embed.add_field(
        name="💰 PRIZE PER WINNER", 
        value=f"**{prize_per_winner:,}** 🪙", 
        inline=True
    )
    
    # Time and entries
    embed.add_field(
        name="⏰ TIME REMAINING", 
        value="**25 seconds**", 
        inline=True
    )
    embed.add_field(
        name="🎫 ENTRIES", 
        value="**0** entries", 
        inline=True
    )
    embed.add_field(
        name="🎲 YOUR CHANCES", 
        value="Enter to see!", 
        inline=True
    )
    
    # Role bonus section
    role_bonus_text = "\n".join([f"<@&{role_id}>: **+{bonus} entries**" for role_id, bonus in PRIORITY_ROLES.items()])
    if role_bonus_text:
        embed.add_field(
            name="🌟 ROLE BONUSES", 
            value=role_bonus_text, 
            inline=False
        )
    
    # Footer with instructions
    embed.set_footer(
        text="Click the button below to enter! • Ends in 25 seconds",
        icon_url="https://cdn.discordapp.com/emojis/1125272129399365632.webp?size=96&quality=lossless"
    )
    
    view = GiveawayEnterView(giveaway_id)
    message = await interaction.response.send_message(embed=embed, view=view)
    
    # Update the giveaway message every 5 seconds with progress
    async def update_giveaway_message():
        for i in range(5):  # 5 updates (25 seconds total)
            await asyncio.sleep(5)
            
            if giveaway_id not in active_giveaways:
                break
                
            giveaway = active_giveaways[giveaway_id]
            time_left = 20 - (i * 5)
            
            # Update embed
            updated_embed = discord.Embed(
                title="🎉 TOKEN GIVEAWAY 🎉",
                description=f"Hosted by {interaction.user.mention}",
                color=0xFFD700,
                timestamp=datetime.now()
            )
            
            updated_embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/1125274830004781156.webp?size=96&quality=lossless")
            updated_embed.add_field(name="🏆 TOTAL PRIZE", value=f"**{amount:,}** 🪙", inline=True)
            updated_embed.add_field(name="👑 WINNERS", value=f"**{winners}** lucky winners", inline=True)
            updated_embed.add_field(name="💰 PRIZE PER WINNER", value=f"**{prize_per_winner:,}** 🪙", inline=True)
            updated_embed.add_field(name="⏰ TIME REMAINING", value=f"**{time_left} seconds**", inline=True)
            updated_embed.add_field(name="🎫 ENTRIES", value=f"**{giveaway['total_entries']:,}** entries", inline=True)
            
            # Calculate approximate chances
            if giveaway['total_entries'] > 0:
                approx_chance = min(100, round((winners / giveaway['total_entries']) * 100, 1))
                updated_embed.add_field(name="🎲 YOUR CHANCES", value=f"**~{approx_chance}%** chance to win", inline=True)
            else:
                updated_embed.add_field(name="🎲 YOUR CHANCES", value="Be the first to enter!", inline=True)
            
            if role_bonus_text:
                updated_embed.add_field(name="🌟 ROLE BONUSES", value=role_bonus_text, inline=False)
            
            updated_embed.set_footer(
                text=f"Click the button below to enter! • Ends in {time_left} seconds",
                icon_url="https://cdn.discordapp.com/emojis/1125272129399365632.webp?size=96&quality=lossless"
            )
            
            try:
                await interaction.edit_original_response(embed=updated_embed, view=view)
            except:
                break
    
    # Start the update task
    asyncio.create_task(update_giveaway_message())
    
    # Wait for giveaway to end
    await asyncio.sleep(25)
    
    # End the giveaway
    if giveaway_id in active_giveaways:
        giveaway = active_giveaways[giveaway_id]
        
        if giveaway['total_entries'] > 0:
            # Select winners
            all_entries = []
            for user_id, entries in giveaway['entries'].items():
                all_entries.extend([user_id] * entries)
            
            selected_winners = random.sample(all_entries, min(giveaway['winners'], len(set(all_entries))))
            unique_winners = list(set(selected_winners))
            
            # Distribute prizes
            winner_mentions = []
            for winner_id in unique_winners:
                try:
                    winner = await bot.fetch_user(int(winner_id))
                    update_balance(winner.id, giveaway['prize_per_winner'])
                    winner_mentions.append(winner.mention)
                except:
                    continue
            
            # Create results embed with improved UI
            result_embed = discord.Embed(
                title="🎊 GIVEAWAY ENDED 🎊",
                description=f"Hosted by {interaction.user.mention}",
                color=0x00ff00,
                timestamp=datetime.now()
            )
            
            result_embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/1125272129399365632.webp?size=96&quality=lossless")
            
            # Results summary
            result_embed.add_field(name="🏆 TOTAL PRIZE", value=f"**{giveaway['amount']:,}** 🪙", inline=True)
            result_embed.add_field(name="👑 WINNERS", value=f"**{len(unique_winners)}/{giveaway['winners']}**", inline=True)
            result_embed.add_field(name="💰 PRIZE PER WINNER", value=f"**{giveaway['prize_per_winner']:,}** 🪙", inline=True)
            result_embed.add_field(name="🎫 TOTAL ENTRIES", value=f"**{giveaway['total_entries']:,}**", inline=True)
            result_embed.add_field(name="👥 PARTICIPANTS", value=f"**{len(giveaway['entries'])}**", inline=True)
            result_embed.add_field(name="⏰ DURATION", value="**25 seconds**", inline=True)
            
            # Winners list
            if winner_mentions:
                winners_text = "\n".join(winner_mentions)
                if len(winners_text) > 1024:
                    winners_text = f"🎉 {len(unique_winners)} winners selected!"
                result_embed.add_field(name="🎊 LUCKY WINNERS", value=winners_text, inline=False)
            
            result_embed.set_footer(
                text="Congratulations to the winners! • Tokens have been distributed",
                icon_url="https://cdn.discordapp.com/emojis/1125274830004781156.webp?size=96&quality=lossless"
            )
            
            # Log the giveaway
            await log_action(
                "GIVEAWAY",
                "🎉 Giveaway Completed",
                f"**{interaction.user.mention}** hosted a giveaway of **{giveaway['amount']:,} tokens**",
                color=0xFFD700,
                user=interaction.user,
                fields=[
                    {"name": "Total Prize", "value": f"{giveaway['amount']:,} 🪙", "inline": True},
                    {"name": "Winners", "value": f"{len(unique_winners)}/{giveaway['winners']}", "inline": True},
                    {"name": "Prize per Winner", "value": f"{giveaway['prize_per_winner']:,} 🪙", "inline": True},
                    {"name": "Total Entries", "value": f"{giveaway['total_entries']:,}", "inline": True},
                    {"name": "Unique Participants", "value": f"{len(giveaway['entries'])}", "inline": True},
                    {"name": "Winners", "value": "\n".join(winner_mentions) if winner_mentions else "No winners", "inline": False}
                ]
            )
            
            # Update the message
            try:
                await interaction.edit_original_response(embed=result_embed, view=None)
            except:
                pass
            
        else:
            # No entries, refund the creator
            update_balance(interaction.user.id, giveaway['amount'])
            giveaway_daily_totals[user_id][today] -= giveaway['amount']
            
            refund_embed = discord.Embed(
                title="🎉 GIVEAWAY ENDED",
                description="No one entered the giveaway. Tokens have been refunded.",
                color=0xff4444
            )
            
            refund_embed.set_footer(text="Better luck next time!")
            
            try:
                await interaction.edit_original_response(embed=refund_embed, view=None)
            except:
                pass
        
        # Remove giveaway from active list
        del active_giveaways[giveaway_id]
        await save_data()

@bot.tree.command(name="giveawayinfo", description="Check your daily giveaway limits")
async def giveawayinfo(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    today = datetime.now().date().isoformat()
    
    daily_gifted = giveaway_daily_totals.get(user_id, {}).get(today, 0)
    daily_giveaway = giveaway_daily_totals.get(user_id, {}).get(today, 0)
    
    embed = discord.Embed(
        title="📊 Giveaway Information",
        description="Your daily limits and usage",
        color=0x0099ff,
        timestamp=datetime.now()
    )
    
    embed.add_field(
        name="🎁 Daily Gift Limit", 
        value=f"**{daily_gifted:,}/3,000** 🪙 used today\n*Resets at midnight*", 
        inline=True
    )
    
    embed.add_field(
        name="🎉 Daily Giveaway Limit", 
        value=f"**{daily_giveaway:,}/50,000** 🪙 used today\n*Resets at midnight*", 
        inline=True
    )
    
    # Calculate time until reset
    now = datetime.now()
    next_midnight = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    time_until_reset = next_midnight - now
    hours, remainder = divmod(time_until_reset.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    embed.add_field(
        name="⏰ Time Until Reset", 
        value=f"**{hours}h {minutes}m {seconds}s**", 
        inline=False
    )
    
    # Role bonus info
    role_bonus_text = "\n".join([f"<@&{role_id}>: +{bonus} entries" for role_id, bonus in PRIORITY_ROLES.items()])
    if role_bonus_text:
        embed.add_field(
            name="🌟 Role Bonuses", 
            value=role_bonus_text, 
            inline=False
        )
    
    embed.set_footer(text="Host giveaways to share your wealth!")
    embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.command(name="about")
async def about(ctx):
    """Traditional text command for bot info"""
    embed = discord.Embed(
        title="🤖 Bot Commands Guide",
        description="Here are all the commands you can use to earn and spend tokens!",
        timestamp=datetime.now()
    )
    
    # Economy Commands
    embed.add_field(
        name="💰 Economy Commands",
        value=(
            "`/balance` - Check your token balance and stats\n"
            "`/daily` - Claim daily tokens (24h cooldown)\n"
            "`/work` - Work for tokens (3h cooldown)\n"
            "`/crime` - Risky crime for tokens (1h cooldown)\n"
            "`/coinflip <amount> <heads/tails>` - Bet tokens on coinflip\n"
            "`/duel <user> <amount>` - Challenge someone to coinflip\n"
            "`/gift <user> <amount>` - Gift tokens to another user\n"
            "`/giveaway <amount> <winners>` - Start a token giveaway\n"
            "`/giveawayinfo` - Check your daily limits"
        ),
        inline=False
    )
    
    # Shop Commands
    embed.add_field(
        name="🛒 Shop Commands",
        value=(
            "`/shop` - Browse available items for purchase\n"
            "`/buy <item_name> [quantity]` - Buy items from the shop"
        ),
        inline=False
    )
    
    # Info Commands
    embed.add_field(
        name="📊 Information Commands",
        value=(
            "`/leaderboard [page]` - View top token holders\n"
            "`!about` - Show this help message"
        ),
        inline=False
    )
    
    # Admin Commands
    if is_admin(ctx.author):
        embed.add_field(
            name="⚙️ Admin Commands",
            value=(
                "`/addtoken <user> <amount>` - Add tokens to user\n"
                "`/removetoken <user> <amount>` - Remove tokens from user\n"
                "`/adminbalance <user>` - Check user's balance\n"
                "`/addshop` - Manage shop items\n"
                "`/resetdata <code>` - Reset all user data"
            ),
            inline=False
        )
    
    # Token Earning Info
    embed.add_field(
        name="💬 Passive Earning",
        value="You earn **1-5 tokens** automatically for each message you send in the server!",
        inline=False
    )
    
    # Rank System
    embed.add_field(
        name="🏆 Rank System",
        value=(
            "🔵 **Starter** - 0+ tokens\n"
            "🟢 **Silver** - 1,000+ tokens\n"
            "🥉 **Gold** - 5,000+ tokens\n"
            "🥈 **Premium** - 10,000+ tokens\n"
            "🥇 **VIP** - 20,000+ tokens\n"
            "💎 **Elite** - 50,000+ tokens\n"
            "🏆 **Legendary** - 100,000+ tokens"
        ),
        inline=False
    )
    
    # Giveaway Info
    embed.add_field(
        name="🎉 Giveaway System",
        value=(
            "• Anyone can host giveaways\n"
            "• Maximum prize: 10,000 tokens per giveaway\n"
            "• Maximum 50,000 tokens per day per user\n"
            "• 1-12 winners\n"
            "• 25 second duration\n"
            "• Special roles get bonus entries:\n"
            "  - <@&1410911675351306250>: +7 entries\n"
            "  - <@&1410911675351306251>: +5 entries\n"
            "  - <@&1410911675351306252>: +3 entries"
        ),
        inline=False
    )
    
    # Gift Limits
    embed.add_field(
        name="🎁 Gift Limits",
        value=(
            "• Maximum 3,000 tokens per day per user\n"
            "• 3 second cooldown between gifts\n"
            "• Check `/giveawayinfo` for your daily usage"
        ),
        inline=False
    )
    
    # Tips
    embed.add_field(
        name="💡 Tips",
        value=(
            "• Use `/daily` every 24 hours for free tokens\n"
            "• `/work` is safe but has a 3-hour cooldown\n"
            "• `/crime` is risky but can give more tokens\n"
            "• Chat regularly to earn passive tokens\n"
            "• Check `/leaderboard` to see your ranking\n"
            "• Host giveaways to share your wealth!"
        ),
        inline=False
    )
    
    embed.set_footer(text="Need help? Ask an admin!")
    embed.set_thumbnail(url=bot.user.display_avatar.url)
    
    await ctx.send(embed=embed)

# Run the bot
if __name__ == "__main__":
    TOKEN = os.getenv('DISCORD_BOT_TOKEN')
    
    if not TOKEN:
        print("❌ ERROR: DISCORD_BOT_TOKEN environment variable not found!")
        print("💡 Set it in Railway dashboard under Variables tab")
        sys.exit(1)
    
    try:
        print("🔑 Token found, connecting to Discord...")
        # Register cleanup handler
        import signal
        def handle_exit(signum, frame):
            loop = asyncio.get_event_loop()
            loop.run_until_complete(force_save_on_exit())
            sys.exit(0)
            
        signal.signal(signal.SIGTERM, handle_exit)
        signal.signal(signal.SIGINT, handle_exit)
        
        bot.run(TOKEN, log_handler=None)
    except discord.LoginFailure:
        print("❌ Invalid bot token!")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error starting bot: {e}")
        sys.exit(1)
