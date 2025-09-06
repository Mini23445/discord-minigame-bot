import discord
from discord.ext import commands
import json
import os
import random
import asyncio
from datetime import datetime
import aiofiles

# Bot configuration
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

# Admin role ID
ADMIN_ROLE_ID = 1410911675351306250

# File paths for data storage
USER_DATA_FILE = 'user_data.json'
SHOP_DATA_FILE = 'shop_data.json'

# Data cache to prevent frequent file I/O
user_data_cache = {}
shop_data_cache = []
cache_dirty = False

async def load_data_async(filename, default_data=None):
    """Async load data from JSON file with error handling"""
    if default_data is None:
        default_data = {}
    try:
        if os.path.exists(filename):
            async with aiofiles.open(filename, 'r') as f:
                content = await f.read()
                return json.loads(content)
        else:
            await save_data_async(filename, default_data)
            return default_data
    except Exception as e:
        print(f"Error loading {filename}: {e}")
        return default_data

async def save_data_async(filename, data):
    """Async save data to JSON file with backup"""
    try:
        # Create backup first
        if os.path.exists(filename):
            backup_name = f"{filename}.backup"
            if os.path.exists(backup_name):
                os.remove(backup_name)
            os.rename(filename, backup_name)
        
        # Save new data
        async with aiofiles.open(filename, 'w') as f:
            await f.write(json.dumps(data, indent=4))
        
        # Remove backup if successful
        backup_name = f"{filename}.backup"
        if os.path.exists(backup_name):
            os.remove(backup_name)
            
    except Exception as e:
        print(f"Error saving {filename}: {e}")
        # Restore backup if save failed
        backup_name = f"{filename}.backup"
        if os.path.exists(backup_name):
            if os.path.exists(filename):
                os.remove(filename)
            os.rename(backup_name, filename)

def load_data(filename, default_data=None):
    """Sync load data from JSON file"""
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
    """Sync save data to JSON file with backup"""
    try:
        # Create backup first
        if os.path.exists(filename):
            backup_name = f"{filename}.backup"
            if os.path.exists(backup_name):
                os.remove(backup_name)
            os.rename(filename, backup_name)
        
        # Save new data
        with open(filename, 'w') as f:
            json.dump(data, f, indent=4)
        
        # Remove backup if successful
        backup_name = f"{filename}.backup"
        if os.path.exists(backup_name):
            os.remove(backup_name)
            
    except Exception as e:
        print(f"Error saving {filename}: {e}")
        # Restore backup if save failed
        backup_name = f"{filename}.backup"
        if os.path.exists(backup_name):
            if os.path.exists(filename):
                os.remove(filename)
            os.rename(backup_name, filename)

async def init_cache():
    """Initialize data cache"""
    global user_data_cache, shop_data_cache
    user_data_cache = await load_data_async(USER_DATA_FILE, {})
    shop_data_cache = await load_data_async(SHOP_DATA_FILE, [])

async def save_cache():
    """Save cache to files"""
    global cache_dirty
    if cache_dirty:
        await save_data_async(USER_DATA_FILE, user_data_cache)
        await save_data_async(SHOP_DATA_FILE, shop_data_cache)
        cache_dirty = False

def get_user_balance(user_id):
    """Get user's token balance from cache"""
    global user_data_cache
    return user_data_cache.get(str(user_id), {}).get('balance', 0)

def update_user_balance(user_id, amount):
    """Update user's token balance in cache"""
    global user_data_cache, cache_dirty
    user_id_str = str(user_id)
    
    if user_id_str not in user_data_cache:
        user_data_cache[user_id_str] = {'balance': 0, 'total_earned': 0}
    
    user_data_cache[user_id_str]['balance'] += amount
    if amount > 0:
        user_data_cache[user_id_str]['total_earned'] = user_data_cache[user_id_str].get('total_earned', 0) + amount
    
    cache_dirty = True
    return user_data_cache[user_id_str]['balance']

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

# Auto-save task
async def auto_save_task():
    """Automatically save cache every 30 seconds"""
    while True:
        await asyncio.sleep(30)
        await save_cache()

@bot.event
async def on_ready():
    print(f'{bot.user} has landed! 🚀')
    await init_cache()
    # Start auto-save task
    bot.loop.create_task(auto_save_task())
    
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s)")
    except Exception as e:
        print(f"Failed to sync commands: {e}")

@bot.event
async def on_message(message):
    # Don't respond to bot messages
    if message.author.bot:
        return
    
    # Award random tokens (1-5) for each message
    if message.guild:  # Only in servers, not DMs
        tokens_earned = random.randint(1, 5)
        new_balance = update_user_balance(message.author.id, tokens_earned)
        
    await bot.process_commands(message)

@bot.tree.command(name="balance", description="Check your token balance")
async def balance(interaction: discord.Interaction):
    user_balance = get_user_balance(interaction.user.id)
    user_data = user_data_cache.get(str(interaction.user.id), {})
    total_earned = user_data.get('total_earned', 0)
    
    embed = discord.Embed(
        title="💰 Your Token Wallet",
        color=0xffd700,
        timestamp=datetime.now()
    )
    embed.set_author(
        name=interaction.user.display_name,
        icon_url=interaction.user.display_avatar.url
    )
    
    # Add a nice gradient-like effect with emojis
    embed.add_field(
        name="🪙 Current Balance",
        value=f"```yaml\n{user_balance:,} Tokens```",
        inline=True
    )
    embed.add_field(
        name="📊 Total Earned",
        value=f"```yaml\n{total_earned:,} Tokens```",
        inline=True
    )
    embed.add_field(
        name="💎 Rank",
        value=f"```yaml\n{'Wealthy' if user_balance > 1000 else 'Growing' if user_balance > 500 else 'Starter'}```",
        inline=True
    )
    
    embed.add_field(
        name="💬 Keep Chatting!",
        value="Each message earns you **1-5 tokens** 🎲",
        inline=False
    )
    
    embed.set_footer(
        text="💡 Tip: Visit /shop to spend your tokens!",
        icon_url="https://cdn.discordapp.com/emojis/741690892862291979.png"
    )
    embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/868087971687448648.png")
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="shop", description="Browse the token shop")
async def shop(interaction: discord.Interaction):
    shop_items = get_shop_items()
    
    embed = discord.Embed(
        title="🏪 ✨ Token Marketplace ✨",
        color=0x00d4ff,
        timestamp=datetime.now()
    )
    
    embed.set_author(
        name="Premium Shop",
        icon_url="https://cdn.discordapp.com/emojis/894678037803618334.png"
    )
    
    if not shop_items:
        embed.description = "```\n🚫 The shop is temporarily closed!\n   New items coming soon...\n```"
        embed.set_image(url="https://cdn.discordapp.com/emojis/692028527239962626.png")
    else:
        user_balance = get_user_balance(interaction.user.id)
        embed.add_field(
            name="💰 Your Balance",
            value=f"```yaml\n{user_balance:,} Tokens```",
            inline=False
        )
        
        # Create sections for different price ranges
        premium_items = []
        regular_items = []
        budget_items = []
        
        for i, item in enumerate(shop_items, 1):
            item_text = f"**{i}.** 🎁 **{item['name']}**\n"
            
            # Add price with affordability indicator
            if user_balance >= item['price']:
                item_text += f"💰 ~~{item['price']:,}~~ ✅ **AFFORDABLE**\n"
            else:
                item_text += f"💰 **{item['price']:,} Tokens**\n"
            
            if item.get('description'):
                item_text += f"📝 *{item['description']}*\n"
            item_text += "━━━━━━━━━━━━━━━━━━━━\n"
            
            # Categorize by price
            if item['price'] >= 10000:
                premium_items.append(item_text)
            elif item['price'] >= 1000:
                regular_items.append(item_text)
            else:
                budget_items.append(item_text)
        
        # Add categorized items
        if budget_items:
            embed.add_field(
                name="🟢 Budget Items (Under 1,000 tokens)",
                value="".join(budget_items),
                inline=False
            )
        
        if regular_items:
            embed.add_field(
                name="🟡 Premium Items (1,000-9,999 tokens)",
                value="".join(regular_items),
                inline=False
            )
        
        if premium_items:
            embed.add_field(
                name="🔴 Exclusive Items (10,000+ tokens)",
                value="".join(premium_items),
                inline=False
            )
    
    embed.set_footer(
        text="💡 Purchase system coming soon! | Keep earning tokens by chatting 💬",
        icon_url="https://cdn.discordapp.com/emojis/741690892862291979.png"
    )
    embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/868087971687448648.png")
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="addtoken", description="Add tokens to a user (Admin only)")
async def addtoken(interaction: discord.Interaction, user: discord.Member, amount: int):
    if not is_admin(interaction.user):
        await interaction.response.send_message("❌ You don't have permission to use this command!", ephemeral=True)
        return
    
    if amount <= 0:
        await interaction.response.send_message("❌ Amount must be greater than 0!", ephemeral=True)
        return
    
    new_balance = update_user_balance(user.id, amount)
    
    embed = discord.Embed(
        title="✅ Tokens Added Successfully!",
        color=0x00ff00,
        timestamp=datetime.now()
    )
    embed.add_field(name="👤 User", value=user.mention, inline=True)
    embed.add_field(name="➕ Tokens Added", value=f"{amount:,}", inline=True)
    embed.add_field(name="💰 New Balance", value=f"{new_balance:,}", inline=True)
    embed.set_footer(text=f"Action performed by {interaction.user.display_name}")
    
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
    
    embed = discord.Embed(
        title="✅ Tokens Removed Successfully!",
        color=0xff6600,
        timestamp=datetime.now()
    )
    embed.add_field(name="👤 User", value=user.mention, inline=True)
    embed.add_field(name="➖ Tokens Removed", value=f"{amount:,}", inline=True)
    embed.add_field(name="💰 New Balance", value=f"{new_balance:,}", inline=True)
    embed.set_footer(text=f"Action performed by {interaction.user.display_name}")
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="resetdata", description="Reset all user data (Admin only)")
async def resetdata(interaction: discord.Interaction):
    if not is_admin(interaction.user):
        await interaction.response.send_message("❌ You don't have permission to use this command!", ephemeral=True)
        return
    
    # Confirmation view
    view = ConfirmResetView(interaction.user)
    embed = discord.Embed(
        title="⚠️ DANGER ZONE",
        description="**This will permanently delete ALL user token data!**\n\n❌ This action cannot be undone!\n❌ All balances will be reset to 0!\n❌ All earning history will be lost!",
        color=0xff0000
    )
    embed.set_footer(text="Are you absolutely sure you want to proceed?")
    
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

class ConfirmResetView(discord.ui.View):
    def __init__(self, admin_user):
        super().__init__(timeout=60)
        self.admin_user = admin_user
    
    @discord.ui.button(label="✅ YES, RESET ALL DATA", style=discord.ButtonStyle.red)
    async def confirm_reset(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.admin_user:
            await interaction.response.send_message("❌ Only the admin who initiated this can confirm!", ephemeral=True)
            return
        
        global user_data_cache, cache_dirty
        user_count = len(user_data_cache)
        user_data_cache = {}
        cache_dirty = True
        await save_cache()
        
        embed = discord.Embed(
            title="✅ Data Reset Complete!",
            description=f"🗑️ Reset data for **{user_count}** users\n💫 All balances are now 0\n🔄 Token earning is ready to restart!",
            color=0x00ff00,
            timestamp=datetime.now()
        )
        embed.set_footer(text=f"Reset performed by {self.admin_user.display_name}")
        
        await interaction.response.edit_message(embed=embed, view=None)
    
    @discord.ui.button(label="❌ Cancel", style=discord.ButtonStyle.grey)
    async def cancel_reset(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.admin_user:
            await interaction.response.send_message("❌ Only the admin who initiated this can cancel!", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="✅ Reset Cancelled",
            description="No data was modified. All user balances remain intact.",
            color=0x00ff00
        )
        
        await interaction.response.edit_message(embed=embed, view=None)

class ShopManagementView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)
    
    @discord.ui.button(label="➕ Add Item", style=discord.ButtonStyle.green)
    async def add_item(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_admin(interaction.user):
            await interaction.response.send_message("❌ You don't have permission to use this!", ephemeral=True)
            return
        
        await interaction.response.send_modal(AddItemModal())
    
    @discord.ui.button(label="✏️ Update Item", style=discord.ButtonStyle.blurple)
    async def update_item(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_admin(interaction.user):
            await interaction.response.send_message("❌ You don't have permission to use this!", ephemeral=True)
            return
        
        shop_items = get_shop_items()
        if not shop_items:
            await interaction.response.send_message("❌ No items in shop to update!", ephemeral=True)
            return
        
        await interaction.response.send_modal(UpdateItemModal())
    
    @discord.ui.button(label="🗑️ Delete Item", style=discord.ButtonStyle.red)
    async def delete_item(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_admin(interaction.user):
            await interaction.response.send_message("❌ You don't have permission to use this!", ephemeral=True)
            return
        
        shop_items = get_shop_items()
        if not shop_items:
            await interaction.response.send_message("❌ No items in shop to delete!", ephemeral=True)
            return
        
        await interaction.response.send_modal(DeleteItemModal())

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
        new_item = {
            'name': self.name.value,
            'price': price_value,
            'description': self.description.value if self.description.value else ""
        }
        
        shop_items.append(new_item)
        save_shop_items(shop_items)
        await save_cache()
        
        embed = discord.Embed(
            title="✅ Item Added Successfully!",
            color=0x00ff00
        )
        embed.add_field(name="Item Name", value=new_item['name'], inline=False)
        embed.add_field(name="Price", value=f"{new_item['price']:,} Tokens", inline=False)
        if new_item['description']:
            embed.add_field(name="Description", value=new_item['description'], inline=False)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

class UpdateItemModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="Update Shop Item")
    
    item_number = discord.ui.TextInput(label="Item Number to Update", placeholder="Enter item number (1, 2, 3...)...")
    name = discord.ui.TextInput(label="New Item Name", placeholder="Enter new item name...")
    price = discord.ui.TextInput(label="New Price (tokens)", placeholder="Enter new price in tokens...")
    description = discord.ui.TextInput(
        label="New Description (optional)", 
        placeholder="Enter new item description...", 
        required=False,
        style=discord.TextStyle.long
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            item_index = int(self.item_number.value) - 1
            price_value = int(self.price.value)
            
            if price_value <= 0:
                await interaction.response.send_message("❌ Price must be greater than 0!", ephemeral=True)
                return
                
        except ValueError:
            await interaction.response.send_message("❌ Please enter valid numbers!", ephemeral=True)
            return
        
        shop_items = get_shop_items()
        
        if item_index < 0 or item_index >= len(shop_items):
            await interaction.response.send_message("❌ Invalid item number!", ephemeral=True)
            return
        
        old_item = shop_items[item_index].copy()
        shop_items[item_index] = {
            'name': self.name.value,
            'price': price_value,
            'description': self.description.value if self.description.value else ""
        }
        
        save_shop_items(shop_items)
        await save_cache()
        
        embed = discord.Embed(
            title="✅ Item Updated Successfully!",
            color=0x00ff00
        )
        embed.add_field(name="Old Item", value=f"{old_item['name']} - {old_item['price']:,} Tokens", inline=False)
        embed.add_field(name="New Item", value=f"{shop_items[item_index]['name']} - {shop_items[item_index]['price']:,} Tokens", inline=False)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

class DeleteItemModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="Delete Shop Item")
    
    item_number = discord.ui.TextInput(label="Item Number to Delete", placeholder="Enter item number (1, 2, 3...)...")
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            item_index = int(self.item_number.value) - 1
        except ValueError:
            await interaction.response.send_message("❌ Please enter a valid number!", ephemeral=True)
            return
        
        shop_items = get_shop_items()
        
        if item_index < 0 or item_index >= len(shop_items):
            await interaction.response.send_message("❌ Invalid item number!", ephemeral=True)
            return
        
        deleted_item = shop_items.pop(item_index)
        save_shop_items(shop_items)
        await save_cache()
        
        embed = discord.Embed(
            title="✅ Item Deleted Successfully!",
            color=0xff0000
        )
        embed.add_field(name="Deleted Item", value=f"{deleted_item['name']} - {deleted_item['price']:,} Tokens", inline=False)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="adminshop", description="Admin shop management (Admin only)")
async def adminshop(interaction: discord.Interaction):
    if not is_admin(interaction.user):
        await interaction.response.send_message("❌ You don't have permission to use this command!", ephemeral=True)
        return
    
    shop_items = get_shop_items()
    
    embed = discord.Embed(
        title="🔧 Shop Management Panel",
        color=0xff9900,
        timestamp=datetime.now()
    )
    
    if shop_items:
        shop_text = ""
        for i, item in enumerate(shop_items, 1):
            shop_text += f"**{i}.** {item['name']} - **{item['price']:,}** Tokens\n"
        embed.add_field(name="Current Shop Items", value=shop_text, inline=False)
    else:
        embed.add_field(name="Current Shop Items", value="No items in shop", inline=False)
    
    embed.set_footer(text="Use the buttons below to manage the shop")
    
    view = ShopManagementView()
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

# Graceful shutdown
@bot.event
async def on_disconnect():
    print("Bot disconnected, saving data...")
    await save_cache()

# Error handling
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    print(f"Error: {error}")

# Run the bot
if __name__ == "__main__":
    # Get bot token from environment variable
    TOKEN = os.getenv('DISCORD_BOT_TOKEN')
    if not TOKEN:
        print("❌ Please set the DISCORD_BOT_TOKEN environment variable!")
    else:
        try:
            bot.run(TOKEN)
        finally:
            # Save data on shutdown
            asyncio.run(save_cache())
