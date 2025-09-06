import discord
from discord.ext import commands
import json
import os
import random
import asyncio
from datetime import datetime, timedelta
import signal
import sys

# Bot configuration
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

# Configuration
ADMIN_ROLE_ID = 1410911675351306250
LOG_CHANNEL_ID = 1413818486404415590
PURCHASE_LOG_CHANNEL_ID = 1413885597826813972

# File paths for data storage
USER_DATA_FILE = 'user_data.json'
SHOP_DATA_FILE = 'shop_data.json'

# Data cache to prevent frequent file I/O
user_data_cache = {}
shop_data_cache = []
cache_dirty = False

# Cooldown tracking
daily_cooldowns = {}
work_cooldowns = {}
crime_cooldowns = {}

# Work jobs list
WORK_JOBS = [
    "delivered pizzas", "walked dogs", "cleaned houses", "tutored students",
    "fixed computers", "painted fences", "washed cars", "mowed lawns",
    "helped elderly", "organized files", "stocked shelves", "served coffee",
    "delivered packages", "babysat kids", "cleaned pools", "raked leaves"
]

# Crime activities list
CRIME_ACTIVITIES = [
    "pickpocketed a stranger", "hacked a vending machine", "sneaked into a movie",
    "stole candy from a store", "jumped a subway turnstile", "copied homework",
    "took extra napkins", "used someone's WiFi", "downloaded music illegally",
    "parked in a no-parking zone", "jaywalked across the street", "littered"
]

async def log_action(action_type, title, description, color=0x0099ff, user=None, fields=None, channel_id=None):
    """Log actions to the specified channel"""
    try:
        target_channel_id = channel_id or LOG_CHANNEL_ID
        channel = bot.get_channel(target_channel_id)
        if not channel:
            print(f"⚠️ Log channel {target_channel_id} not found!")
            return
        
        embed = discord.Embed(
            title=f"🔷 {title}",
            description=description,
            color=color,
            timestamp=datetime.now()
        )
        
        if user:
            embed.set_author(
                name=f"{user.display_name} ({user.name})",
                icon_url=user.display_avatar.url
            )
            embed.add_field(name="User ID", value=f"`{user.id}`", inline=True)
        
        if fields:
            for field in fields:
                embed.add_field(
                    name=field.get('name', ''),
                    value=field.get('value', ''),
                    inline=field.get('inline', True)
                )
        
        embed.set_footer(text=f"Action: {action_type}")
        await channel.send(embed=embed)
        
    except Exception as e:
        print(f"Failed to log action: {e}")

def load_data(filename, default_data=None):
    """Load data from JSON file"""
    if default_data is None:
        default_data = {}
    try:
        if os.path.exists(filename):
            with open(filename, 'r') as f:
                return json.load(f)
        else:
            return default_data
    except:
        return default_data

def save_data(filename, data):
    """Save data to JSON file"""
    try:
        with open(filename, 'w') as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print(f"Error saving {filename}: {e}")

def init_cache():
    """Initialize data cache"""
    global user_data_cache, shop_data_cache, daily_cooldowns, work_cooldowns, crime_cooldowns
    user_data_cache = load_data(USER_DATA_FILE, {})
    shop_data_cache = load_data(SHOP_DATA_FILE, [])
    
    # Load cooldowns
    cooldown_data = load_data('cooldowns.json', {})
    daily_cooldowns = cooldown_data.get('daily', {})
    work_cooldowns = cooldown_data.get('work', {})
    crime_cooldowns = cooldown_data.get('crime', {})

def save_cache():
    """Save cache to files"""
    global cache_dirty
    if cache_dirty:
        save_data(USER_DATA_FILE, user_data_cache)
        save_data(SHOP_DATA_FILE, shop_data_cache)
        
        # Save cooldowns
        cooldown_data = {
            'daily': daily_cooldowns,
            'work': work_cooldowns,
            'crime': crime_cooldowns
        }
        save_data('cooldowns.json', cooldown_data)
        cache_dirty = False

def cleanup_and_exit():
    """Save all data before exit"""
    print("🔄 Saving data before shutdown...")
    save_cache()
    print("✅ Data saved successfully!")

# Register cleanup handlers
def signal_handler(sig, frame):
    cleanup_and_exit()
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

def get_user_balance(user_id):
    """Get user's token balance from cache"""
    global user_data_cache
    return user_data_cache.get(str(user_id), {}).get('balance', 0)

def update_user_balance(user_id, amount):
    """Update user's token balance in cache"""
    global user_data_cache, cache_dirty
    user_id_str = str(user_id)
    
    if user_id_str not in user_data_cache:
        user_data_cache[user_id_str] = {'balance': 0, 'total_earned': 0, 'total_spent': 0, 'purchases': []}
    
    user_data_cache[user_id_str]['balance'] += amount
    if amount > 0:
        user_data_cache[user_id_str]['total_earned'] = user_data_cache[user_id_str].get('total_earned', 0) + amount
    elif amount < 0:
        user_data_cache[user_id_str]['total_spent'] = user_data_cache[user_id_str].get('total_spent', 0) + abs(amount)
    
    cache_dirty = True
    return user_data_cache[user_id_str]['balance']

def add_purchase_history(user_id, item_name, price, quantity=1):
    """Add purchase to user's history"""
    global user_data_cache, cache_dirty
    user_id_str = str(user_id)
    
    if user_id_str not in user_data_cache:
        user_data_cache[user_id_str] = {'balance': 0, 'total_earned': 0, 'total_spent': 0, 'purchases': []}
    
    purchase = {
        'item': item_name,
        'price': price,
        'quantity': quantity,
        'total_cost': price * quantity,
        'timestamp': datetime.now().isoformat()
    }
    
    if 'purchases' not in user_data_cache[user_id_str]:
        user_data_cache[user_id_str]['purchases'] = []
    
    user_data_cache[user_id_str]['purchases'].append(purchase)
    cache_dirty = True

def get_shop_items():
    """Get all shop items from cache"""
    global shop_data_cache
    return shop_data_cache

def save_shop_items(items):
    """Save shop items to cache"""
    global shop_data_cache, cache_dirty
    shop_data_cache = items
    cache_dirty = True

def is_admin(user):
    """Check if user has admin role"""
    return any(role.id == ADMIN_ROLE_ID for role in user.roles)

def get_user_rank(balance):
    """Get user rank based on balance"""
    if balance >= 100000:
        return "🏆 Legendary"
    elif balance >= 50000:
        return "💎 Elite"
    elif balance >= 20000:
        return "🥇 VIP"
    elif balance >= 10000:
        return "🥈 Premium"
    elif balance >= 5000:
        return "🥉 Gold"
    elif balance >= 1000:
        return "🟢 Silver"
    else:
        return "🔵 Starter"

def can_use_daily(user_id):
    """Check if user can use daily command"""
    user_id_str = str(user_id)
    if user_id_str not in daily_cooldowns:
        return True, None
    
    last_used = datetime.fromisoformat(daily_cooldowns[user_id_str])
    next_use = last_used + timedelta(hours=24)
    
    if datetime.now() >= next_use:
        return True, None
    else:
        return False, next_use

def can_use_work(user_id):
    """Check if user can use work command"""
    user_id_str = str(user_id)
    if user_id_str not in work_cooldowns:
        return True, None
    
    last_used = datetime.fromisoformat(work_cooldowns[user_id_str])
    next_use = last_used + timedelta(hours=3)
    
    if datetime.now() >= next_use:
        return True, None
    else:
        return False, next_use

def can_use_crime(user_id):
    """Check if user can use crime command"""
    user_id_str = str(user_id)
    if user_id_str not in crime_cooldowns:
        return True, None
    
    last_used = datetime.fromisoformat(crime_cooldowns[user_id_str])
    next_use = last_used + timedelta(hours=1)  # 1 hour cooldown for crime
    
    if datetime.now() >= next_use:
        return True, None
    else:
        return False, next_use

def format_time_remaining(next_use):
    """Format remaining time until next use"""
    remaining = next_use - datetime.now()
    hours, remainder = divmod(int(remaining.total_seconds()), 3600)
    minutes, _ = divmod(remainder, 60)
    
    if hours > 0:
        return f"{hours}h {minutes}m"
    else:
        return f"{minutes}m"

# Auto-save task
async def auto_save_task():
    """Automatically save cache every 30 seconds"""
    while True:
        await asyncio.sleep(30)
        save_cache()

@bot.event
async def on_ready():
    print(f'{bot.user} has landed! 🚀')
    init_cache()
    # Start auto-save task
    bot.loop.create_task(auto_save_task())
    
    await log_action(
        "BOT_START",
        "🤖 Bot Started",
        f"**{bot.user.name}** is now online and ready!",
        color=0x00ff00
    )
    
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s)")
    except Exception as e:
        print(f"Failed to sync commands: {e}")

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    
    if message.guild:
        tokens_earned = random.randint(1, 5)
        new_balance = update_user_balance(message.author.id, tokens_earned)
        
    await bot.process_commands(message)

@bot.tree.command(name="balance", description="Check your token balance")
async def balance(interaction: discord.Interaction):
    user_balance = get_user_balance(interaction.user.id)
    user_data = user_data_cache.get(str(interaction.user.id), {})
    total_earned = user_data.get('total_earned', 0)
    total_spent = user_data.get('total_spent', 0)
    rank = get_user_rank(user_balance)
    
    embed = discord.Embed(
        title="💰 Token Wallet",
        color=0x7B68EE,
        timestamp=datetime.now()
    )
    
    embed.add_field(
        name="Current Balance",
        value=f"**{user_balance:,}** 🪙",
        inline=True
    )
    embed.add_field(
        name="Rank",
        value=rank,
        inline=True
    )
    embed.add_field(
        name="Total Spent",
        value=f"{total_spent:,} 🪙",
        inline=True
    )
    embed.add_field(
        name="Total Earned",
        value=f"{total_earned:,} 🪙",
        inline=True
    )
    embed.add_field(
        name="‎",  # Invisible character for spacing
        value="‎",
        inline=True
    )
    embed.add_field(
        name="‎",  # Invisible character for spacing
        value="‎",
        inline=True
    )
    
    embed.set_author(
        name=interaction.user.display_name,
        icon_url=interaction.user.display_avatar.url
    )
    embed.set_footer(text="💬 Chat to earn 1-5 tokens per message")
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="adminbalance", description="Check any user's token balance (Admin only)")
async def adminbalance(interaction: discord.Interaction, user: discord.Member):
    if not is_admin(interaction.user):
        await interaction.response.send_message("❌ You don't have permission to use this command!", ephemeral=True)
        return
    
    user_balance = get_user_balance(user.id)
    user_data = user_data_cache.get(str(user.id), {})
    total_earned = user_data.get('total_earned', 0)
    total_spent = user_data.get('total_spent', 0)
    purchases = user_data.get('purchases', [])
    rank = get_user_rank(user_balance)
    
    embed = discord.Embed(
        title=f"💰 {user.display_name}'s Token Wallet",
        color=0xFF6B6B,
        timestamp=datetime.now()
    )
    
    embed.add_field(
        name="Current Balance",
        value=f"**{user_balance:,}** 🪙",
        inline=True
    )
    embed.add_field(
        name="Rank",
        value=rank,
        inline=True
    )
    embed.add_field(
        name="Total Spent",
        value=f"{total_spent:,} 🪙",
        inline=True
    )
    embed.add_field(
        name="Total Earned",
        value=f"{total_earned:,} 🪙",
        inline=True
    )
    embed.add_field(
        name="Total Purchases",
        value=f"{len(purchases)} items",
        inline=True
    )
    embed.add_field(
        name="Account Created",
        value=f"<t:{int(user.created_at.timestamp())}:R>",
        inline=True
    )
    
    embed.set_author(
        name=user.display_name,
        icon_url=user.display_avatar.url
    )
    embed.set_footer(text=f"Viewed by {interaction.user.display_name}")
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="daily", description="Claim your daily tokens (24h cooldown)")
async def daily(interaction: discord.Interaction):
    can_use, next_use = can_use_daily(interaction.user.id)
    
    if not can_use:
        time_remaining = format_time_remaining(next_use)
        await interaction.response.send_message(
            f"⏰ You've already claimed your daily reward! Come back in **{time_remaining}**.",
            ephemeral=True
        )
        return
    
    # Give random tokens between 1-50
    tokens_earned = random.randint(1, 50)
    new_balance = update_user_balance(interaction.user.id, tokens_earned)
    
    # Update cooldown
    daily_cooldowns[str(interaction.user.id)] = datetime.now().isoformat()
    save_cache()
    
    embed = discord.Embed(
        title="🎁 Daily Reward Claimed!",
        color=0x00ff00,
        timestamp=datetime.now()
    )
    embed.add_field(name="Tokens Earned", value=f"{tokens_earned:,} 🪙", inline=True)
    embed.add_field(name="New Balance", value=f"{new_balance:,} 🪙", inline=True)
    embed.add_field(name="Next Daily", value="<t:" + str(int((datetime.now() + timedelta(hours=24)).timestamp())) + ":R>", inline=False)
    
    embed.set_author(
        name=interaction.user.display_name,
        icon_url=interaction.user.display_avatar.url
    )
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="work", description="Work a job to earn tokens (3h cooldown)")
async def work(interaction: discord.Interaction):
    can_use, next_use = can_use_work(interaction.user.id)
    
    if not can_use:
        time_remaining = format_time_remaining(next_use)
        await interaction.response.send_message(
            f"💼 You're still tired from your last job! Rest for **{time_remaining}** more.",
            ephemeral=True
        )
        return
    
    # Give random tokens between 1-100
    tokens_earned = random.randint(1, 100)
    job = random.choice(WORK_JOBS)
    new_balance = update_user_balance(interaction.user.id, tokens_earned)
    
    # Update cooldown
    work_cooldowns[str(interaction.user.id)] = datetime.now().isoformat()
    save_cache()
    
    embed = discord.Embed(
        title="💼 Work Complete!",
        color=0x4CAF50,
        timestamp=datetime.now()
    )
    embed.add_field(name="Job", value=f"You {job}", inline=False)
    embed.add_field(name="Tokens Earned", value=f"{tokens_earned:,} 🪙", inline=True)
    embed.add_field(name="New Balance", value=f"{new_balance:,} 🪙", inline=True)
    embed.add_field(name="Next Work", value="<t:" + str(int((datetime.now() + timedelta(hours=3)).timestamp())) + ":R>", inline=False)
    
    embed.set_author(
        name=interaction.user.display_name,
        icon_url=interaction.user.display_avatar.url
    )
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="crime", description="Commit a crime for tokens (1h cooldown, risky!)")
async def crime(interaction: discord.Interaction):
    can_use, next_use = can_use_crime(interaction.user.id)
    
    if not can_use:
        time_remaining = format_time_remaining(next_use)
        await interaction.response.send_message(
            f"🚔 You need to lay low for **{time_remaining}** more before your next crime!",
            ephemeral=True
        )
        return
    
    # Random success/failure
    success = random.choice([True, False])
    crime_activity = random.choice(CRIME_ACTIVITIES)
    
    if success:
        tokens_earned = random.randint(15, 100)
        new_balance = update_user_balance(interaction.user.id, tokens_earned)
        
        embed = discord.Embed(
            title="🎭 Crime Successful!",
            color=0x00ff00,
            timestamp=datetime.now()
        )
        embed.add_field(name="Crime", value=f"You {crime_activity}", inline=False)
        embed.add_field(name="Tokens Gained", value=f"+{tokens_earned:,} 🪙", inline=True)
        embed.add_field(name="New Balance", value=f"{new_balance:,} 🪙", inline=True)
    else:
        tokens_lost = random.randint(3, 100)
        current_balance = get_user_balance(interaction.user.id)
        
        # Don't let balance go negative
        tokens_lost = min(tokens_lost, current_balance)
        new_balance = update_user_balance(interaction.user.id, -tokens_lost)
        
        embed = discord.Embed(
            title="🚔 Crime Failed!",
            color=0xff4444,
            timestamp=datetime.now()
        )
        embed.add_field(name="Crime", value=f"You tried to {crime_activity.replace('stole', 'steal').replace('took', 'take')}", inline=False)
        embed.add_field(name="Tokens Lost", value=f"-{tokens_lost:,} 🪙", inline=True)
        embed.add_field(name="New Balance", value=f"{new_balance:,} 🪙", inline=True)
    
    embed.add_field(name="Next Crime", value="<t:" + str(int((datetime.now() + timedelta(hours=1)).timestamp())) + ":R>", inline=False)
    
    embed.set_author(
        name=interaction.user.display_name,
        icon_url=interaction.user.display_avatar.url
    )
    
    # Update cooldown
    crime_cooldowns[str(interaction.user.id)] = datetime.now().isoformat()
    save_cache()
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="gift", description="Gift tokens to another user")
async def gift(interaction: discord.Interaction, user: discord.Member, amount: int):
    if amount <= 0:
        await interaction.response.send_message("❌ Amount must be greater than 0!", ephemeral=True)
        return
    
    if user.id == interaction.user.id:
        await interaction.response.send_message("❌ You can't gift tokens to yourself!", ephemeral=True)
        return
    
    if user.bot:
        await interaction.response.send_message("❌ You can't gift tokens to bots!", ephemeral=True)
        return
    
    giver_balance = get_user_balance(interaction.user.id)
    
    if giver_balance < amount:
        await interaction.response.send_message(
            f"❌ Insufficient funds! You need **{amount - giver_balance:,}** more tokens.",
            ephemeral=True
        )
        return
    
    # Transfer tokens
    giver_new_balance = update_user_balance(interaction.user.id, -amount)
    receiver_new_balance = update_user_balance(user.id, amount)
    save_cache()
    
    # Send public message with emojis (max 3 emojis)
    gift_message = f"🎁 {interaction.user.mention} gifted **{amount:,} tokens** 🪙 to {user.mention}! 🎉"
    await interaction.response.send_message(gift_message)
    
    # Log the gift action
    await log_action(
        "GIFT",
        "🎁 Token Gift",
        f"**{interaction.user.mention}** gifted tokens to **{user.mention}**",
        color=0xFFD700,
        user=interaction.user,
        fields=[
            {"name": "Recipient", "value": user.mention, "inline": True},
            {"name": "Amount", "value": f"{amount:,} 🪙", "inline": True},
            {"name": "Giver's New Balance", "value": f"{giver_new_balance:,} 🪙", "inline": True},
            {"name": "Receiver's New Balance", "value": f"{receiver_new_balance:,} 🪙", "inline": True}
        ]
    )

class PurchaseConfirmationView(discord.ui.View):
    def __init__(self, item, user_id):
        super().__init__(timeout=60)
        self.item = item
        self.user_id = user_id
    
    @discord.ui.button(label="✅ Confirm Purchase", style=discord.ButtonStyle.green)
    async def confirm_purchase(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ This is not your purchase!", ephemeral=True)
            return
        
        user_balance = get_user_balance(interaction.user.id)
        
        if user_balance < self.item['price']:
            await interaction.response.send_message(
                f"❌ Insufficient funds! You need **{self.item['price'] - user_balance:,}** more tokens.",
                ephemeral=True
            )
            return
        
        new_balance = update_user_balance(interaction.user.id, -self.item['price'])
        add_purchase_history(interaction.user.id, self.item['name'], self.item['price'])
        save_cache()
        
        embed = discord.Embed(
            title="✅ Purchase Successful!",
            color=0x00ff00,
            timestamp=datetime.now()
        )
        embed.add_field(name="Item", value=self.item['name'], inline=True)
        embed.add_field(name="Cost", value=f"{self.item['price']:,} 🪙", inline=True)
        embed.add_field(name="New Balance", value=f"{new_balance:,} 🪙", inline=True)
        
        if self.item.get('description'):
            embed.add_field(name="Description", value=self.item['description'], inline=False)
        
        embed.set_author(
            name=interaction.user.display_name,
            icon_url=interaction.user.display_avatar.url
        )
        
        await interaction.response.edit_message(embed=embed, view=None)
        
        await log_action(
            "PURCHASE",
            "💳 Item Purchased",
            f"**{interaction.user.mention}** bought **{self.item['name']}**",
            color=0x00ff00,
            user=interaction.user,
            fields=[
                {"name": "Item", "value": self.item['name'], "inline": True},
                {"name": "Price", "value": f"{self.item['price']:,} 🪙", "inline": True},
                {"name": "New Balance", "value": f"{new_balance:,} 🪙", "inline": True}
            ],
            channel_id=PURCHASE_LOG_CHANNEL_ID
        )
    
    @discord.ui.button(label="❌ Cancel", style=discord.ButtonStyle.red)
    async def cancel_purchase(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ This is not your purchase!", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="❌ Purchase Cancelled",
            description="Your purchase has been cancelled.",
            color=0xff4444
        )
        
        await interaction.response.edit_message(embed=embed, view=None)

class ShopView(discord.ui.View):
    def __init__(self, items, user_balance):
        super().__init__(timeout=300)
        self.items = items
        self.user_balance = user_balance
        
        for i, item in enumerate(items[:25]):
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
        if item_index >= len(self.items):
            await interaction.response.send_message("❌ Invalid item!", ephemeral=True)
            return
        
        item = self.items[item_index]
        user_balance = get_user_balance(interaction.user.id)
        
        if user_balance < item['price']:
            await interaction.response.send_message(
                f"❌ Insufficient funds! You need **{item['price'] - user_balance:,}** more tokens.",
                ephemeral=True
            )
            return
        
        embed = discord.Embed(
            title="🛒 Purchase Confirmation",
            color=0xFFD700,
            timestamp=datetime.now()
        )
        embed.add_field(name="Item", value=item['name'], inline=True)
        embed.add_field(name="Cost", value=f"{item['price']:,} 🪙", inline=True)
        embed.add_field(name="Your Balance", value=f"{user_balance:,} 🪙", inline=True)
        embed.add_field(name="Balance After", value=f"{user_balance - item['price']:,} 🪙", inline=True)
        
        if item.get('description'):
            embed.add_field(name="Description", value=item['description'], inline=False)
        
        embed.set_footer(text="Are you sure you want to buy this item?")
        
        view = PurchaseConfirmationView(item, interaction.user.id)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

@bot.tree.command(name="shop", description="Browse and buy items from the token shop")
async def shop(interaction: discord.Interaction):
    shop_items = get_shop_items()
    user_balance = get_user_balance(interaction.user.id)
    
    embed = discord.Embed(
        title="🛒 Token Shop",
        color=0x0099ff,
        timestamp=datetime.now()
    )
    
    embed.add_field(
        name="Your Balance",
        value=f"**{user_balance:,}** 🪙",
        inline=False
    )
