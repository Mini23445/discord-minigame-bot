import discord
from discord.ext import commands
import json
import os
import random
import asyncio
from datetime import datetime, timedelta

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
cooldowns = {"daily": {}, "work": {}, "crime": {}}

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
    """Check if user can use command"""
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
    """Auto save every 60 seconds"""
    while True:
        await asyncio.sleep(60)
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
        tokens = min(tokens, current)  # Don't go negative
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
    save_data()
    
    message = f"🎁 {interaction.user.mention} gifted **{amount:,} tokens** 🪙 to {user.mention}! 🎉"
    await interaction.response.send_message(message)

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
    
    embed = discord.Embed(title="✅ Tokens Added", color=0x00ff00)
    embed.add_field(name="User", value=user.mention, inline=True)
    embed.add_field(name="Added", value=f"{amount:,} 🪙", inline=True)
    embed.add_field(name="New Balance", value=f"{new_balance:,} 🪙", inline=True)
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

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
    
    embed.add_field(name="Items", value=items_text, inline=False)
    await interaction.response.send_message(embed=embed, ephemeral=True)

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
        
        # Check for duplicates
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
        
        embed = discord.Embed(title="✅ Item Added!", color=0x00ff00)
        embed.add_field(name="Name", value=new_item['name'], inline=False)
        embed.add_field(name="Price", value=f"{new_item['price']:,} 🪙", inline=False)
        
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

@bot.tree.command(name="addshop", description="Manage shop (Admin only)")
async def addshop(interaction: discord.Interaction):
    if not is_admin(interaction.user):
        await interaction.response.send_message("❌ Admin only!", ephemeral=True)
        return
    
    embed = discord.Embed(title="🛍️ Shop Management", color=0xff9900)
    embed.add_field(name="Items", value=f"{len(shop_data)} items", inline=True)
    
    if shop_data:
        items_list = "\n".join([f"{i+1}. {item['name']} - {item['price']:,} 🪙" for i, item in enumerate(shop_data[:5])])
        if len(shop_data) > 5:
            items_list += f"\n... and {len(shop_data) - 5} more"
        embed.add_field(name="Current Items", value=items_list, inline=False)
    
    view = ShopManageView()
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

# Run the bot
if __name__ == "__main__":
    TOKEN = os.getenv('DISCORD_BOT_TOKEN')
    if not TOKEN:
        print("❌ No DISCORD_BOT_TOKEN found!")
    else:
        try:
            bot.run(TOKEN)
        except Exception as e:
            print(f"❌ Error: {e}")
        finally:
            save_data()
