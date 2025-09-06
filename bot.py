import discord
from discord.ext import commands
import json
import os
import random
import asyncio
from datetime import datetime, timedelta
import atexit

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
COOLDOWNS_FILE = 'cooldowns.json'

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
    except Exception as e:
        print(f"Error loading {filename}: {e}")
        return default_data

def save_data(filename, data):
    """Save data to JSON file"""
    try:
        with open(filename, 'w') as f:
            json.dump(data, f, indent=4)
        return True
    except Exception as e:
        print(f"Error saving {filename}: {e}")
        return False

def init_cache():
    """Initialize data cache"""
    global user_data_cache, shop_data_cache, daily_cooldowns, work_cooldowns, crime_cooldowns
    
    print("Loading data files...")
    user_data_cache = load_data(USER_DATA_FILE, {})
    shop_data_cache = load_data(SHOP_DATA_FILE, [])
    
    # Load cooldowns
    cooldown_data = load_data(COOLDOWNS_FILE, {})
    daily_cooldowns = cooldown_data.get('daily', {})
    work_cooldowns = cooldown_data.get('work', {})
    crime_cooldowns = cooldown_data.get('crime', {})
    
    print(f"Loaded {len(user_data_cache)} users, {len(shop_data_cache)} shop items")

def save_cache():
    """Save cache to files"""
    global cache_dirty
    try:
        if cache_dirty:
            print("Saving data...")
            save_data(USER_DATA_FILE, user_data_cache)
            save_data(SHOP_DATA_FILE, shop_data_cache)
            
            # Save cooldowns
            cooldown_data = {
                'daily': daily_cooldowns,
                'work': work_cooldowns,
                'crime': crime_cooldowns
            }
            save_data(COOLDOWNS_FILE, cooldown_data)
            cache_dirty = False
            print("Data saved successfully!")
    except Exception as e:
        print(f"Error saving cache: {e}")

# Register cleanup function
atexit.register(save_cache)

def get_user_balance(user_id):
    """Get user's token balance from cache"""
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

def can_use_command(user_id, cooldown_dict, hours):
    """Check if user can use a command with cooldown"""
    user_id_str = str(user_id)
    if user_id_str not in cooldown_dict:
        return True, None
    
    try:
        last_used = datetime.fromisoformat(cooldown_dict[user_id_str])
        next_use = last_used + timedelta(hours=hours)
        
        if datetime.now() >= next_use:
            return True, None
        else:
            return False, next_use
    except:
        return True, None

def format_time_remaining(next_use):
    """Format remaining time until next use"""
    try:
        remaining = next_use - datetime.now()
        hours, remainder = divmod(int(remaining.total_seconds()), 3600)
        minutes, _ = divmod(remainder, 60)
        
        if hours > 0:
            return f"{hours}h {minutes}m"
        else:
            return f"{minutes}m"
    except:
        return "unknown"

# Auto-save task
async def auto_save_task():
    """Automatically save cache every 60 seconds"""
    while True:
        await asyncio.sleep(60)
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
        update_user_balance(message.author.id, tokens_earned)
        
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
        name="‎",
        value="‎",
        inline=True
    )
    embed.add_field(
        name="‎",
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
    can_use, next_use = can_use_command(interaction.user.id, daily_cooldowns, 24)
    
    if not can_use:
        time_remaining = format_time_remaining(next_use)
        await interaction.response.send_message(
            f"⏰ You've already claimed your daily reward! Come back in **{time_remaining}**.",
            ephemeral=True
        )
        return
    
    tokens_earned = random.randint(1, 50)
    new_balance = update_user_balance(interaction.user.id, tokens_earned)
    
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
    can_use, next_use = can_use_command(interaction.user.id, work_cooldowns, 3)
    
    if not can_use:
        time_remaining = format_time_remaining(next_use)
        await interaction.response.send_message(
            f"💼 You're still tired from your last job! Rest for **{time_remaining}** more.",
            ephemeral=True
        )
        return
    
    tokens_earned = random.randint(1, 100)
    job = random.choice(WORK_JOBS)
    new_balance = update_user_balance(interaction.user.id, tokens_earned)
    
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
    can_use, next_use = can_use_command(interaction.user.id, crime_cooldowns, 1)
    
    if not can_use:
        time_remaining = format_time_remaining(next_use)
        await interaction.response.send_message(
            f"🚔 You need to lay low for **{time_remaining}** more before your next crime!",
            ephemeral=True
        )
        return
    
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
    
    giver_new_balance = update_user_balance(interaction.user.id, -amount)
    receiver_new_balance = update_user_balance(user.id, amount)
    save_cache()
    
    gift_message = f"🎁 {interaction.user.mention} gifted **{amount:,} tokens** 🪙 to {user.mention}! 🎉"
    await interaction.response.send_message(gift_message)
    
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
    
    if not shop_items:
        embed.description = "🚫 No items available right now!"
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    items_text = ""
    for i, item in enumerate(shop_items[:10]):
        affordable = "✅" if user_balance >= item['price'] else "❌"
        items_text += f"{affordable} **{item['name']}** - {item['price']:,} 🪙\n"
        if item.get('description'):
            items_text += f"    *{item['description'][:50]}{'...' if len(item['description']) > 50 else ''}*\n"
        items_text += "\n"
    
    embed.add_field(
        name="Available Items",
        value=items_text,
        inline=False
    )
    
    embed.set_footer(text="Click the buttons below to purchase items!")
    
    view = ShopView(shop_items, user_balance)
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

@bot.tree.command(name="addtoken", description="Add tokens to a user (Admin only)")
async def addtoken(interaction: discord.Interaction, user: discord.Member, amount: int):
    if not is_admin(interaction.user):
        await interaction.response.send_message("❌ You don't have permission to use this command!", ephemeral=True)
        return
    
    if amount <= 0:
        await interaction.response.send_message("❌ Amount must be greater than 0!", ephemeral=True)
        return
    
    old_balance = get_user_balance(user.id)
    new_balance = update_user_balance(user.id, amount)
    save_cache()
    
    embed = discord.Embed(
        title="✅ Tokens Added",
        color=0x00ff00,
        timestamp=datetime.now()
    )
    embed.add_field(name="User", value=user.mention, inline=True)
    embed.add_field(name="Amount Added", value=f"{amount:,} 🪙", inline=True)
    embed.add_field(name="New Balance", value=f"{new_balance:,} 🪙", inline=True)
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="removetoken", description="Remove tokens from a user (Admin only)")
async def removetoken(interaction: discord.Interaction, user: discord.Member, amount: int):
    if not is_admin(interaction.user):
        await interaction.response.send_message("❌ You don't have permission to use this command!", ephemeral=True)
        return
    
    if amount <= 0:
        await interaction.response.send_message("❌ Amount must be greater than 0!", ephemeral=True)
        return
    
    current_balance = get_user_balance(user.id)
    if current_balance < amount:
        await interaction.response.send_message(f"❌ User only has {current_balance:,} tokens! Cannot remove {amount:,}.", ephemeral=True)
        return
    
    new_balance = update_user_balance(user.id, -amount)
    save_cache()
    
    embed = discord.Embed(
        title="✅ Tokens Removed",
        color=0xff6600,
        timestamp=datetime.now()
    )
    embed.add_field(name="User", value=user.mention, inline=True)
    embed.add_field(name="Amount Removed", value=f"{amount:,} 🪙", inline=True)
    embed.add_field(name="New Balance", value=f"{new_balance:,} 🪙", inline=True)
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

class AddItemModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="Add Shop Item")
    
    name = discord.ui.TextInput(label="Item Name", placeholder="Enter item name...")
    price = discord.ui.TextInput(label="Price (tokens)", placeholder="Enter price in tokens...")
    description = discord.ui.TextInput(
        label="Description (optional)", 
        placeholder="Enter item description...", 
        required=False,
        style=discord.TextStyle.long
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            price_value = int(self.price.value)
            if price_value <= 0:
                await interaction.response.send_message("❌ Price must be greater than 0!", ephemeral=True)
                return
        except ValueError:
            await interaction.response.send_message("❌ Price must be a valid number!", ephemeral=True)
            return
        
        shop_items = get_shop_items()
        
        for item in shop_items:
            if item['name'].lower() == self.name.value.lower():
                await interaction.response.send_message("❌ An item with this name already exists!", ephemeral=True)
                return
        
        new_item = {
            'name': self.name.value,
            'price': price_value,
            'description': self.description.value if self.description.value else ""
        }
        
        shop_items.append(new_item)
        save_shop_items(shop_items)
        save_cache()
        
        embed = discord.Embed(
            title="✅ Item Added Successfully!",
            color=0x00ff00
        )
        embed.add_field(name="Item Name", value=new_item['name'], inline=False)
        embed.add_field(name="Price", value=f"{new_item['price']:,} 🪙", inline=False)
        if new_item['description']:
            embed.add_field(name="Description", value=new_item['description'], inline=False)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

class ShopManagementView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)
    
    @discord.ui.button(label="➕ Add Item", style=discord.ButtonStyle.green)
    async def add_item(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_admin(interaction.user):
            await interaction.response.send_message("❌ You don't have permission to use this!", ephemeral=True)
            return
        
        await interaction.response.send_modal(AddItemModal())

@bot.tree.command(name="addshop", description="Add items to shop (Admin only)")
async def addshop(interaction: discord.Interaction):
    if not is_admin(interaction.user):
        await interaction.response.send_message("❌ You don't have permission to use this command!", ephemeral=True)
        return
    
    shop_items = get_shop_items()
    
    embed = discord.Embed(
        title="🛍️ Shop Management",
        color=0xff9900,
        timestamp=datetime.now()
    )
    
    embed.add_field(
        name="📊 Shop Stats",
        value=f"**Items:** {len(shop_items)}\n**Status:** {'Active' if shop_items else 'Empty'}",
        inline=True
    )
    
    if shop_items:
        shop_text = ""
        for i, item in enumerate(shop_items[:5], 1):
            shop_text += f"**{i}.** {item['name']} - {item['price']:,} 🪙\n"
        
        if len(shop_items) > 5:
            shop_text += f"*... and {len(shop_items) - 5} more*"
        
        embed.add_field(name="🛒 Items", value=shop_text, inline=False)
    else:
        embed.add_field(name="🛒 Items", value="*No items*", inline=False)
    
    view = ShopManagementView()
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

if __name__ == "__main__":
    TOKEN = os.getenv('DISCORD_BOT_TOKEN')
    if not TOKEN:
        print("❌ Please set the DISCORD_BOT_TOKEN environment variable!")
    else:
        try:
            bot.run(TOKEN)
        except Exception as e:
            print(f"❌ Bot error: {e}")
            save_cache()  # Save data on error
