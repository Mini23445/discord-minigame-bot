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
        save_data()
        
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
        try:
            item_idx = int(self.item_number.value) - 1
            if item_idx < 0 or item_idx >= len(shop_data):
                await interaction.response.send_message(f"❌ Invalid item number! Must be 1-{len(shop_data)}", ephemeral=True)
                return
        except:
            await interaction.response.send_message("❌ Item number must be a valid number!", ephemeral=True)
            return
        
        old_item = shop_data[item_idx].copy()
        
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
        
        save_data()
        
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
        save_data()
        
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
    
    class ResetConfirmView(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=30)
        
        @discord.ui.button(label="🗑️ YES, RESET ALL DATA", style=discord.ButtonStyle.danger)
        async def confirm_reset(self, button_interaction: discord.Interaction, button: discord.ui.Button):
            if button_interaction.user.id != interaction.user.id:
                await button_interaction.response.send_message("❌ Only the command user can confirm!", ephemeral=True)
                return
            
            # Reset all data
            global user_data, cooldowns
            user_data.clear()
            cooldowns = {"daily": {}, "work": {}, "crime": {}, "gift": {}, "buy": {}}
            save_data()
            
            success_embed = discord.Embed(
                title="✅ Data Reset Complete",
                description="All user data has been permanently deleted.\n"
                           "Users will start fresh with 0 tokens.",
                color=0x00ff00
            )
            success_embed.set_footer(text=f"Reset by {interaction.user.display_name}")
            
            await button_interaction.response.edit_message(embed=success_embed, view=None)
            
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
        async def cancel_reset(self, button_interaction: discord.Interaction, button: discord.ui.Button):
            if button_interaction.user.id != interaction.user.id:
                await button_interaction.response.send_message("❌ Only the command user can cancel!", ephemeral=True)
                return
            
            cancel_embed = discord.Embed(
                title="❌ Reset Cancelled",
                description="Data reset has been cancelled. All user data remains intact.",
                color=0x808080
            )
            
            await button_interaction.response.edit_message(embed=cancel_embed, view=None)
    
    view = ResetConfirmView()
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
    
    # Sort users by balance
    sorted_users = []
    for user_id, data in user_data.items():
        balance = data.get('balance', 0)
        if balance > 0:  # Only show users with tokens
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
    
    # Pagination
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
        
        # Add medal emojis for top 3
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
    
    # Add user's position if they're not on current page
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

@bot.command(name="about")
async def about(ctx):
    """Traditional text command for bot info"""
    embed = discord.Embed(
        title="🤖 Bot Commands Guide",
        description="Here are all the commands you can use to earn and spend tokens!",
        color=0x7B68EE,
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
            "`/gift <user> <amount>` - Gift tokens to another user"
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
    
    # Tips
    embed.add_field(
        name="💡 Tips",
        value=(
            "• Use `/daily` every 24 hours for free tokens\n"
            "• `/work` is safe but has a 3-hour cooldown\n"
            "• `/crime` is risky but can give more tokens\n"
            "• Chat regularly to earn passive tokens\n"
            "• Check `/leaderboard` to see your ranking"
        ),
        inline=False
    )
    
    embed.set_footer(text="Need help? Ask an admin!")
    embed.set_thumbnail(url=bot.user.display_avatar.url)
    
    await ctx.send(embed=embed)

# Run the bot with enhanced error handling
if __name__ == "__main__":
    TOKEN = os.getenv('DISCORD_BOT_TOKEN')
    if not TOKEN:
        print("❌ No DISCORD_BOT_TOKEN found!")
    else:
        try:
            print("🚀 Starting bot...")
            bot.run(TOKEN)
        except KeyboardInterrupt:
            print("\n🛑 Bot stopped by user")
        except Exception as e:
            print(f"❌ Bot error: {e}")
        finally:
            print("🔄 Bot shutting down...")
            force_save_on_exit()
