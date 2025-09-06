import discord
from discord.ext import commands
import json
import os
import random
import asyncio
from datetime import datetime

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Config
ADMIN_ROLE_ID = 1410911675351306250
LOG_CHANNEL_ID = 1413818486404415590
USER_DATA_FILE = 'user_data.json'
SHOP_DATA_FILE = 'shop_data.json'

# Data
user_data_cache = {}
shop_data_cache = []
cache_dirty = False

async def log_action(action_type, title, description, color=0x0099ff, user=None, fields=None):
    try:
        channel = bot.get_channel(LOG_CHANNEL_ID)
        if not channel:
            print(f"Log channel {LOG_CHANNEL_ID} not found!")
            return
        
        embed = discord.Embed(title=f"🔷 {title}", description=description, color=color, timestamp=datetime.now())
        
        if user:
            embed.set_author(name=f"{user.display_name} ({user.name})", icon_url=user.display_avatar.url)
            embed.add_field(name="User ID", value=f"`{user.id}`", inline=True)
        
        if fields:
            for field in fields:
                embed.add_field(name=field.get('name', ''), value=field.get('value', ''), inline=field.get('inline', True))
        
        embed.set_footer(text=f"Action: {action_type}")
        await channel.send(embed=embed)
    except Exception as e:
        print(f"Failed to log: {e}")

def load_data(filename, default_data=None):
    if default_data is None:
        default_data = {}
    try:
        if os.path.exists(filename):
            with open(filename, 'r') as f:
                return json.load(f)
        return default_data
    except:
        return default_data

def save_data(filename, data):
    try:
        with open(filename, 'w') as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print(f"Error saving {filename}: {e}")

def init_cache():
    global user_data_cache, shop_data_cache
    user_data_cache = load_data(USER_DATA_FILE, {})
    shop_data_cache = load_data(SHOP_DATA_FILE, [])

def save_cache():
    global cache_dirty
    if cache_dirty:
        save_data(USER_DATA_FILE, user_data_cache)
        save_data(SHOP_DATA_FILE, shop_data_cache)
        cache_dirty = False

def get_user_balance(user_id):
    return user_data_cache.get(str(user_id), {}).get('balance', 0)

def update_user_balance(user_id, amount):
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
    return shop_data_cache

def save_shop_items(items):
    global shop_data_cache, cache_dirty
    shop_data_cache = items
    cache_dirty = True

def is_admin(user):
    return any(role.id == ADMIN_ROLE_ID for role in user.roles)

def get_user_rank(balance):
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

async def auto_save_task():
    while True:
        await asyncio.sleep(30)
        save_cache()

@bot.event
async def on_ready():
    print(f'{bot.user} has landed!')
    init_cache()
    bot.loop.create_task(auto_save_task())
    
    await log_action("BOT_START", "🤖 Bot Started", f"**{bot.user.name}** is now online!", color=0x00ff00)
    
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} commands")
        for cmd in synced:
            print(f"✅ /{cmd.name}")
    except Exception as e:
        print(f"Failed to sync: {e}")

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
    
    embed = discord.Embed(title="💰 Token Wallet", color=0x2f3136, timestamp=datetime.now())
    embed.add_field(name="Current Balance", value=f"**{user_balance:,}** 🪙", inline=True)
    embed.add_field(name="Rank", value=rank, inline=True)
    embed.add_field(name="‎", value="‎", inline=True)
    embed.add_field(name="Total Earned", value=f"{total_earned:,} 🪙", inline=True)
    embed.add_field(name="Total Spent", value=f"{total_spent:,} 🪙", inline=True)
    embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
    embed.set_footer(text="💬 Chat to earn 1-5 tokens per message")
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="shop", description="Browse the token shop")
async def shop(interaction: discord.Interaction):
    shop_items = get_shop_items()
    user_balance = get_user_balance(interaction.user.id)
    
    embed = discord.Embed(title="🛒 Token Shop", color=0x0099ff, timestamp=datetime.now())
    embed.add_field(name="Your Balance", value=f"**{user_balance:,}** 🪙", inline=False)
    
    if not shop_items:
        embed.description = "🚫 No items available!"
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    items_text = ""
    for i, item in enumerate(shop_items[:10]):
        affordable = "✅" if user_balance >= item['price'] else "❌"
        items_text += f"{affordable} **{item['name']}** - {item['price']:,} 🪙\n"
        if item.get('description'):
            items_text += f"    *{item['description'][:50]}{'...' if len(item['description']) > 50 else ''}*\n"
        items_text += "\n"
    
    embed.add_field(name="Available Items", value=items_text, inline=False)
    embed.set_footer(text="Use /buy item_name to purchase!")
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="buy", description="Buy an item")
async def buy(interaction: discord.Interaction, item_name: str, quantity: int = 1):
    if quantity <= 0:
        await interaction.response.send_message("❌ Quantity must be at least 1!", ephemeral=True)
        return
    
    shop_items = get_shop_items()
    item = None
    
    for shop_item in shop_items:
        if shop_item['name'].lower() == item_name.lower():
            item = shop_item
            break
    
    if not item:
        similar_items = [i['name'] for i in shop_items if item_name.lower() in i['name'].lower()]
        error_msg = f"❌ Item **{item_name}** not found!"
        if similar_items:
            error_msg += f"\n\nDid you mean: {', '.join(similar_items[:3])}"
        await interaction.response.send_message(error_msg, ephemeral=True)
        return
    
    user_balance = get_user_balance(interaction.user.id)
    total_cost = item['price'] * quantity
    
    if user_balance < total_cost:
        await interaction.response.send_message(
            f"❌ Insufficient funds!\n**Cost:** {total_cost:,} 🪙\n**Your Balance:** {user_balance:,} 🪙\n**Need:** {total_cost - user_balance:,} more tokens",
            ephemeral=True
        )
        return
    
    new_balance = update_user_balance(interaction.user.id, -total_cost)
    add_purchase_history(interaction.user.id, item['name'], item['price'], quantity)
    save_cache()
    
    embed = discord.Embed(title="✅ Purchase Successful!", color=0x00ff00, timestamp=datetime.now())
    embed.add_field(name="Item", value=item['name'], inline=True)
    if quantity > 1:
        embed.add_field(name="Quantity", value=str(quantity), inline=True)
    embed.add_field(name="Total Cost", value=f"{total_cost:,} 🪙", inline=True)
    embed.add_field(name="New Balance", value=f"{new_balance:,} 🪙", inline=False)
    
    if item.get('description'):
        embed.add_field(name="Description", value=item['description'], inline=False)
    
    embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
    
    await interaction.response.send_message(embed=embed, ephemeral=True)
    
    await log_action(
        "PURCHASE",
        "💳 Item Purchased",
        f"**{interaction.user.mention}** bought **{quantity}x {item['name']}**" if quantity > 1 else f"**{interaction.user.mention}** bought **{item['name']}**",
        color=0x00ff00,
        user=interaction.user,
        fields=[
            {"name": "Item", "value": item['name'], "inline": True},
            {"name": "Quantity", "value": str(quantity), "inline": True},
            {"name": "Total Cost", "value": f"{total_cost:,} 🪙", "inline": True},
            {"name": "New Balance", "value": f"{new_balance:,} 🪙", "inline": True}
        ]
    )

@bot.tree.command(name="history", description="View your purchase history")
async def history(interaction: discord.Interaction):
    user_data = user_data_cache.get(str(interaction.user.id), {})
    purchases = user_data.get('purchases', [])
    
    embed = discord.Embed(title="📋 Purchase History", color=0x9932cc, timestamp=datetime.now())
    
    if not purchases:
        embed.description = "No purchases yet! Visit `/shop` to buy items."
    else:
        recent_purchases = purchases[-10:]
        history_text = ""
        
        for purchase in reversed(recent_purchases):
            date = datetime.fromisoformat(purchase['timestamp']).strftime("%m/%d %H:%M")
            qty_text = f"{purchase['quantity']}x " if purchase['quantity'] > 1 else ""
            history_text += f"**{date}** - {qty_text}{purchase['item']} ({purchase['total_cost']:,} 🪙)\n"
        
        embed.add_field(name="Recent Purchases", value=history_text, inline=False)
        
        total_spent = user_data.get('total_spent', 0)
        embed.add_field(name="Total Spent", value=f"{total_spent:,} 🪙", inline=True)
        embed.add_field(name="Total Purchases", value=str(len(purchases)), inline=True)
    
    embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="leaderboard", description="View top token holders")
async def leaderboard(interaction: discord.Interaction):
    sorted_users = sorted(user_data_cache.items(), key=lambda x: x[1].get('balance', 0), reverse=True)[:10]
    
    embed = discord.Embed(title="🏆 Token Leaderboard", color=0xffd700, timestamp=datetime.now())
    
    if not sorted_users:
        embed.description = "No users with tokens yet!"
    else:
        leaderboard_text = ""
        medals = ["🥇", "🥈", "🥉"] + ["🏅"] * 7
        
        for i, (user_id, data) in enumerate(sorted_users):
            try:
                user = bot.get_user(int(user_id))
                username = user.display_name if user else f"User {user_id}"
                balance = data.get('balance', 0)
                rank = get_user_rank(balance)
                leaderboard_text += f"{medals[i]} **{username}** - {balance:,} 🪙 {rank}\n"
            except:
                continue
        
        embed.description = leaderboard_text
    
    embed.set_footer(text="Keep chatting to climb the leaderboard!")
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
    
    sender_balance = get_user_balance(interaction.user.id)
    if sender_balance < amount:
        await interaction.response.send_message(f"❌ Insufficient funds! You have {sender_balance:,} 🪙 but need {amount:,} 🪙", ephemeral=True)
        return
    
    sender_new_balance = update_user_balance(interaction.user.id, -amount)
    receiver_new_balance = update_user_balance(user.id, amount)
    save_cache()
    
    gift_message = f"🎁 {interaction.user.mention} gifted **{amount:,} Tokens** 🪙 to {user.mention}!"
    await interaction.response.send_message(gift_message)
    
    try:
        notify_message = f"🎁 **{interaction.user.display_name}** sent you **{amount:,} Tokens** 🪙! Your new balance: **{receiver_new_balance:,}** 🪙"
        await user.send(notify_message)
    except:
        pass
    
    await log_action(
        "GIFT",
        "🎁 Token Gift",
        f"**{interaction.user.mention}** gifted tokens to **{user.mention}**",
        color=0x9932cc,
        user=interaction.user,
        fields=[
            {"name": "Sender", "value": interaction.user.mention, "inline": True},
            {"name": "Recipient", "value": user.mention, "inline": True},
            {"name": "Amount", "value": f"{amount:,} 🪙", "inline": True},
            {"name": "Sender New Balance", "value": f"{sender_new_balance:,} 🪙", "inline": True},
            {"name": "Recipient New Balance", "value": f"{receiver_new_balance:,} 🪙", "inline": True}
        ]
    )

@bot.tree.command(name="adminbalance", description="View and manage user balance (Admin only)")
async def adminbalance(interaction: discord.Interaction, user: discord.Member):
    if not is_admin(interaction.user):
        await interaction.response.send_message("❌ You don't have permission to use this command!", ephemeral=True)
        return
    
    user_balance = get_user_balance(user.id)
    user_data = user_data_cache.get(str(user.id), {})
    total_earned = user_data.get('total_earned', 0)
    total_spent = user_data.get('total_spent', 0)
    rank = get_user_rank(user_balance)
    
    embed = discord.Embed(title=f"👤 {user.display_name}'s Token Wallet", color=0xff9900, timestamp=datetime.now())
    embed.add_field(name="Current Balance", value=f"**{user_balance:,}** 🪙", inline=True)
    embed.add_field(name="Rank", value=rank, inline=True)
    embed.add_field(name="‎", value="‎", inline=True)
    embed.add_field(name="Total Earned", value=f"{total_earned:,} 🪙", inline=True)
    embed.add_field(name="Total Spent", value=f"{total_spent:,} 🪙", inline=True)
    embed.set_author(name=user.display_name, icon_url=user.display_avatar.url)
    embed.set_footer(text="Admin view of user balance")
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="adminshop", description="Admin shop management (Admin only)")
async def adminshop(interaction: discord.Interaction):
    if not is_admin(interaction.user):
        await interaction.response.send_message("❌ You don't have permission to use this command!", ephemeral=True)
        return
    
    shop_items = get_shop_items()
    
    embed = discord.Embed(title="🔧 Shop Management Panel", color=0xff9900, timestamp=datetime.now())
    
    if shop_items:
        shop_text = ""
        for i, item in enumerate(shop_items, 1):
            shop_text += f"**{i}.** {item['name']} - {item['price']:,} 🪙\n"
        embed.add_field(name="Current Shop Items", value=shop_text, inline=False)
    else:
        embed.add_field(name="Current Shop Items", value="No items in shop", inline=False)
    
    embed.set_footer(text="Use other admin commands to manage items")
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="resetdata", description="Reset all user data (Admin only)")
async def resetdata(interaction: discord.Interaction):
    if not is_admin(interaction.user):
        await interaction.response.send_message("❌ You don't have permission to use this command!", ephemeral=True)
        return
    
    global user_data_cache, cache_dirty
    user_count = len(user_data_cache)
    user_data_cache = {}
    cache_dirty = True
    save_cache()
    
    embed = discord.Embed(
        title="✅ Data Reset Complete!",
        description=f"🗑️ Reset data for **{user_count}** users\n💫 All balances are now 0\n🔄 Token earning is ready to restart!",
        color=0x00ff00,
        timestamp=datetime.now()
    )
    embed.set_footer(text=f"Reset performed by {interaction.user.display_name}")
    
    await interaction.response.send_message(embed=embed, ephemeral=True)
    
    await log_action(
        "ADMIN_RESET_DATA",
        "🗑️ Data Reset",
        f"**{interaction.user.mention}** reset all user data",
        color=0xff0000,
        user=interaction.user,
        fields=[
            {"name": "Users Affected", "value": str(user_count), "inline": True},
            {"name": "Action", "value": "Complete data wipe", "inline": True}
        ]
    )

@bot.event
async def on_disconnect():
    print("Bot disconnected, saving data...")
    save_cache()

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    print(f"Error: {error}")

if __name__ == "__main__":
    TOKEN = os.getenv('DISCORD_BOT_TOKEN')
    if not TOKEN:
        print("❌ Please set the DISCORD_BOT_TOKEN environment variable!")
    else:
        print("🚀 Starting bot with 9 commands...")
        bot.run(TOKEN)
