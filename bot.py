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

# Configuration
ADMIN_ROLE_ID = 1410911675351306250
LOG_CHANNEL_ID = 1413818486404415590
USER_DATA_FILE = 'user_data.json'
SHOP_DATA_FILE = 'shop_data.json'

# Global variables
user_data_cache = {}
shop_data_cache = []
cache_dirty = False

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

def is_admin(user):
    return any(role.id == ADMIN_ROLE_ID for role in user.roles)

async def auto_save_task():
    while True:
        await asyncio.sleep(30)
        save_cache()

@bot.event
async def on_ready():
    print(f'{bot.user} has started!')
    init_cache()
    bot.loop.create_task(auto_save_task())
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} commands")
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
    
    embed = discord.Embed(title="Token Balance", color=0x00d4ff)
    embed.add_field(name="Current Balance", value=f"{user_balance:,} tokens", inline=True)
    embed.add_field(name="Total Earned", value=f"{total_earned:,} tokens", inline=True)
    embed.add_field(name="Total Spent", value=f"{total_spent:,} tokens", inline=True)
    embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="shop", description="View the token shop")
async def shop(interaction: discord.Interaction):
    shop_items = shop_data_cache
    user_balance = get_user_balance(interaction.user.id)
    
    embed = discord.Embed(title="Token Shop", color=0x0099ff)
    embed.add_field(name="Your Balance", value=f"{user_balance:,} tokens", inline=False)
    
    if not shop_items:
        embed.description = "No items available!"
    else:
        items_text = ""
        for item in shop_items:
            affordable = "Available" if user_balance >= item['price'] else "Cannot afford"
            items_text += f"{affordable} - {item['name']} - {item['price']:,} tokens\n"
        embed.add_field(name="Items", value=items_text, inline=False)
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="buy", description="Buy an item from the shop")
async def buy(interaction: discord.Interaction, item_name: str):
    shop_items = shop_data_cache
    item = None
    
    for shop_item in shop_items:
        if shop_item['name'].lower() == item_name.lower():
            item = shop_item
            break
    
    if not item:
        await interaction.response.send_message(f"Item '{item_name}' not found!", ephemeral=True)
        return
    
    user_balance = get_user_balance(interaction.user.id)
    
    if user_balance < item['price']:
        await interaction.response.send_message(f"Insufficient funds! You need {item['price'] - user_balance:,} more tokens.", ephemeral=True)
        return
    
    new_balance = update_user_balance(interaction.user.id, -item['price'])
    save_cache()
    
    embed = discord.Embed(title="Purchase Successful!", color=0x00ff00)
    embed.add_field(name="Item", value=item['name'], inline=True)
    embed.add_field(name="Cost", value=f"{item['price']:,} tokens", inline=True)
    embed.add_field(name="New Balance", value=f"{new_balance:,} tokens", inline=True)
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="gift", description="Gift tokens to another user")
async def gift(interaction: discord.Interaction, user: discord.Member, amount: int):
    if amount <= 0:
        await interaction.response.send_message("Amount must be greater than 0!", ephemeral=True)
        return
    
    if user.id == interaction.user.id:
        await interaction.response.send_message("You cannot gift tokens to yourself!", ephemeral=True)
        return
    
    sender_balance = get_user_balance(interaction.user.id)
    if sender_balance < amount:
        await interaction.response.send_message(f"Insufficient funds! You have {sender_balance:,} tokens.", ephemeral=True)
        return
    
    update_user_balance(interaction.user.id, -amount)
    update_user_balance(user.id, amount)
    save_cache()
    
    await interaction.response.send_message(f"{interaction.user.mention} gifted {amount:,} tokens to {user.mention}!")

@bot.tree.command(name="leaderboard", description="View the token leaderboard")
async def leaderboard(interaction: discord.Interaction):
    sorted_users = sorted(user_data_cache.items(), key=lambda x: x[1].get('balance', 0), reverse=True)[:10]
    
    embed = discord.Embed(title="Token Leaderboard", color=0xffd700)
    
    if not sorted_users:
        embed.description = "No users with tokens yet!"
    else:
        leaderboard_text = ""
        for i, (user_id, data) in enumerate(sorted_users, 1):
            try:
                user = bot.get_user(int(user_id))
                username = user.display_name if user else f"User {user_id}"
                balance = data.get('balance', 0)
                leaderboard_text += f"{i}. {username} - {balance:,} tokens\n"
            except:
                continue
        
        embed.description = leaderboard_text
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="addtokens", description="Add tokens to a user (Admin only)")
async def addtokens(interaction: discord.Interaction, user: discord.Member, amount: int):
    if not is_admin(interaction.user):
        await interaction.response.send_message("You don't have permission!", ephemeral=True)
        return
    
    if amount <= 0:
        await interaction.response.send_message("Amount must be greater than 0!", ephemeral=True)
        return
    
    new_balance = update_user_balance(user.id, amount)
    save_cache()
    
    embed = discord.Embed(title="Tokens Added!", color=0x00ff00)
    embed.add_field(name="User", value=user.mention, inline=True)
    embed.add_field(name="Amount Added", value=f"{amount:,} tokens", inline=True)
    embed.add_field(name="New Balance", value=f"{new_balance:,} tokens", inline=True)
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="additem", description="Add an item to the shop (Admin only)")
async def additem(interaction: discord.Interaction, name: str, price: int, description: str = ""):
    if not is_admin(interaction.user):
        await interaction.response.send_message("You don't have permission!", ephemeral=True)
        return
    
    if price <= 0:
        await interaction.response.send_message("Price must be greater than 0!", ephemeral=True)
        return
    
    new_item = {
        'name': name,
        'price': price,
        'description': description
    }
    
    shop_data_cache.append(new_item)
    save_data(SHOP_DATA_FILE, shop_data_cache)
    
    embed = discord.Embed(title="Item Added!", color=0x00ff00)
    embed.add_field(name="Name", value=name, inline=True)
    embed.add_field(name="Price", value=f"{price:,} tokens", inline=True)
    if description:
        embed.add_field(name="Description", value=description, inline=False)
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="resetdata", description="Reset all user data (Admin only)")
async def resetdata(interaction: discord.Interaction):
    if not is_admin(interaction.user):
        await interaction.response.send_message("You don't have permission!", ephemeral=True)
        return
    
    global user_data_cache, cache_dirty
    user_count = len(user_data_cache)
    user_data_cache = {}
    cache_dirty = True
    save_cache()
    
    embed = discord.Embed(title="Data Reset Complete!", description=f"Reset data for {user_count} users", color=0xff0000)
    await interaction.response.send_message(embed=embed, ephemeral=True)

if __name__ == "__main__":
    TOKEN = os.getenv("DISCORD_BOT_TOKEN")
    if not TOKEN:
        print("Please set the DISCORD_BOT_TOKEN environment variable!")
    else:
        print("Starting bot...")
        bot.run(TOKEN)
