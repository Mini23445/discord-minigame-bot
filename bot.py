import discord
from discord.ext import commands
import json
import os
import random
import asyncio
from datetime import datetime, timedelta
import time

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

# Configuration
ADMIN_ROLE_ID = 1410911675351306250
LOG_CHANNEL_ID = 1413818486404415590
PURCHASE_LOG_CHANNEL_ID = 1413885597826813972

# Data storage
user_data = {}
shop_data = []
cooldowns = {"daily": {}, "work": {}, "crime": {}, "gift": {}, "buy": {}}

# Work jobs and crimes
WORK_JOBS = [
    "delivered pizzas", "walked dogs", "cleaned houses", "tutored students",
    "fixed computers", "painted fences", "washed cars", "mowed lawns"
]

CRIME_ACTIVITIES = [
    "pickpocketed a stranger", "hacked a vending machine", "sneaked into a movie",
    "stole candy from a store", "jumped a subway turnstile", "copied homework"
]

def load_data():
    """Load all data from files"""
    global user_data, shop_data, cooldowns
    try:
        if os.path.exists('user_data.json'):
            with open('user_data.json', 'r') as f:
                user_data = json.load(f)
        if os.path.exists('shop_data.json'):
            with open('shop_data.json', 'r') as f:
                shop_data = json.load(f)
        if os.path.exists('cooldowns.json'):
            with open('cooldowns.json', 'r') as f:
                cooldowns = json.load(f)
        print("✅ Data loaded successfully")
    except Exception as e:
        print(f"⚠️ Error loading data: {e}")

def save_data():
    """Save all data to files"""
    try:
        with open('user_data.json', 'w') as f:
            json.dump(user_data, f, indent=2)
        with open('shop_data.json', 'w') as f:
            json.dump(shop_data, f, indent=2)
        with open('cooldowns.json', 'w') as f:
            json.dump(cooldowns, f, indent=2)
    except Exception as e:
        print(f"⚠️ Error saving data: {e}")

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
    """Check short cooldowns (3 seconds)"""
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
        save_data()

@bot.event
async def on_ready():
    print(f'🚀 {bot.user} is online!')
    load_data()
    bot.loop.create_task(auto_save())
    
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
    save_data()
    
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
    save_data()
    
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
        tokens = random.randint(15, 100)
        new_balance = update_balance(interaction.user.id, tokens)
        embed = discord.Embed(title="🎭 Crime Success!", color=0x00ff00)
        embed.add_field(name="Crime", value=f"You {activity}", inline=False)
        embed.add_field(name="Gained", value=f"+{tokens:,} 🪙", inline=True)
    else:
        tokens = random.randint(3, 100)
        current = get_user_balance(interaction.user.id)
        tokens = min(tokens, current)
        new_balance = update_balance(interaction.user.id, -tokens)
        embed = discord.Embed(title="🚔 Crime Failed!", color=0xff4444)
        embed.add_field(name="Crime", value=f"Tried to {activity}", inline=False)
        embed.add_field(name="Lost", value=f"-{tokens:,} 🪙", inline=True)
    
    embed.add_field(name="Balance", value=f"{new_balance:,} 🪙", inline=True)
    embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
    
    cooldowns["crime"][str(interaction.user.id)] = datetime.now().isoformat()
    save_data()
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="gift", description="Gift tokens to another user")
async def gift(interaction: discord.Interaction, user: discord.Member, amount: int):
    # Check 3 second cooldown
    if not can_use_short_cooldown(interaction.user.id, "gift", 3):
        await interaction.response.send_message("⏰ Please wait 3 seconds between gifts!", ephemeral=True)
        return
    
    if amount <= 0:
        await interaction.response.send_message("❌ Amount must be greater than 0!", ephemeral=True)
        return
    
    if user.id == interaction.user.id:
        await interaction.response.send_message("❌ Can't gift to yourself!", ephemeral=True)
        return
    
    if user.bot:
        await interaction.response.send_message("❌ Can't gift to bots!", ephemeral=True)
        return
    
    giver_balance = get_user_balance(interaction.user.id)
    if giver_balance < amount:
        await interaction.response.send_message(f"❌ Need **{amount - giver_balance:,}** more tokens!", ephemeral=True)
        return
    
    update_balance(interaction.user.id, -amount)
    update_balance(user.id, amount)
    set_short_cooldown(interaction.user.id, "gift")
    save_data()
    
    # Log the gift
    await log_action(
        "GIFT",
        "🎁 Token Gift",
        f"{interaction.user.mention} gifted **{amount:,} tokens** to {user.mention}",
        color=0xffb347,
        user=interaction.user,
        fields=[
            {"name": "Giver", "value": interaction.user.mention, "inline": True},
            {"name": "Receiver", "value": user.mention, "inline": True},
            {"name": "Amount", "value": f"{amount:,} 🪙", "inline": True}
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
        save_data()
        
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
    save_data()
    
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
    save_data()
    
    # Log the token addition
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

# Shop management modals and views
class AddItemModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="Add Shop Item")
    
    name = discord.ui.TextInput(label="Item Name")
    price = discord.ui.TextInput(label="Price")
    description = discord.ui.TextInput(label="Description", required=False, style=discord.TextStyle.long)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            price_val = int(self.price.value)
            if price_val <= 0:
                await interaction.response.send_message("❌ Price must be positive!", ephemeral=True)
                return
