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

# Configuration
ADMIN_ROLE_ID = 1410911675351306250
LOG_CHANNEL_ID = 1413818486404415590

# File paths for data storage
USER_DATA_FILE = 'user_data.json'
SHOP_DATA_FILE = 'shop_data.json'

# Data cache to prevent frequent file I/O
user_data_cache = {}
shop_data_cache = []
cache_dirty = False

async def log_action(action_type, title, description, color=0x0099ff, user=None, fields=None):
    """Log actions to the specified channel"""
    try:
        channel = bot.get_channel(LOG_CHANNEL_ID)
        if not channel:
            print(f"⚠️ Log channel {LOG_CHANNEL_ID} not found!")
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
    
    @discord.ui.button(label="📊 Shop Stats", style=discord.ButtonStyle.secondary)
    async def shop_stats(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_admin(interaction.user):
            await interaction.response.send_message("❌ You don't have permission to use this!", ephemeral=True)
            return
        
        # Calculate shop statistics
        total_purchases = 0
        total_revenue = 0
        item_sales = {}
        
        for user_data in user_data_cache.values():
            purchases = user_data.get('purchases', [])
            total_purchases += len(purchases)
            
            for purchase in purchases:
                total_revenue += purchase.get('total_cost', 0)
                item_name = purchase.get('item', 'Unknown')
                item_sales[item_name] = item_sales.get(item_name, 0) + purchase.get('quantity', 1)
        
        embed = discord.Embed(
            title="📊 Shop Statistics",
            color=0x9932cc,
            timestamp=datetime.now()
        )
        
        embed.add_field(
            name="💰 Total Revenue",
            value=f"{total_revenue:,} 🪙",
            inline=True
        )
        embed.add_field(
            name="🛒 Total Purchases",
            value=f"{total_purchases:,}",
            inline=True
        )
        embed.add_field(
            name="📦 Items in Shop",
            value=f"{len(get_shop_items())}",
            inline=True
        )
        
        if item_sales:
            # Top selling items
            top_items = sorted(item_sales.items(), key=lambda x: x[1], reverse=True)[:5]
            top_items_text = ""
            for item, sales in top_items:
                top_items_text += f"**{item}** - {sales} sold\n"
            
            embed.add_field(
                name="🔥 Top Selling Items",
                value=top_items_text or "No sales yet",
                inline=False
            )
        
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
        embed.add_field(name="Price", value=f"{new_item['price']:,} 🪙", inline=False)
        if new_item['description']:
            embed.add_field(name="Description", value=new_item['description'], inline=False)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
        # Log the action
        await log_action(
            "ADMIN_ADD_ITEM",
            "➕ Shop Item Added",
            f"**{interaction.user.mention}** added a new item to the shop",
            color=0x00ff00,
            user=interaction.user,
            fields=[
                {"name": "Item Name", "value": new_item['name'], "inline": True},
                {"name": "Price", "value": f"{new_item['price']:,} 🪙", "inline": True},
                {"name": "Description", "value": new_item['description'][:100] + "..." if len(new_item['description']) > 100 else new_item['description'], "inline": False}
            ]
        )

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
        embed.add_field(name="Old Item", value=f"{old_item['name']} - {old_item['price']:,} 🪙", inline=False)
        embed.add_field(name="New Item", value=f"{shop_items[item_index]['name']} - {shop_items[item_index]['price']:,} 🪙", inline=False)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
        # Log the action
        await log_action(
            "ADMIN_UPDATE_ITEM",
            "✏️ Shop Item Updated",
            f"**{interaction.user.mention}** updated a shop item",
            color=0x0099ff,
            user=interaction.user,
            fields=[
                {"name": "Old Item", "value": f"{old_item['name']} - {old_item['price']:,} 🪙", "inline": True},
                {"name": "New Item", "value": f"{shop_items[item_index]['name']} - {shop_items[item_index]['price']:,} 🪙", "inline": True}
            ]
        )

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
        embed.add_field(name="Deleted Item", value=f"{deleted_item['name']} - {deleted_item['price']:,} 🪙", inline=False)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
        # Log the action
        await log_action(
            "ADMIN_DELETE_ITEM",
            "🗑️ Shop Item Deleted",
            f"**{interaction.user.mention}** deleted an item from the shop",
            color=0xff0000,
            user=interaction.user,
            fields=[
                {"name": "Deleted Item", "value": f"{deleted_item['name']} - {deleted_item['price']:,} 🪙", "inline": True}
            ]
        )

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
            shop_text += f"**{i}.** {item['name']} - {item['price']:,} 🪙\n"
        embed.add_field(name="Current Shop Items", value=shop_text, inline=False)
    else:
        embed.add_field(name="Current Shop Items", value="No items in shop", inline=False)
    
    embed.set_footer(text="Use the buttons below to manage the shop")
    
    view = ShopManagementView()
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

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
        await interaction.response.send_message(
            f"❌ Insufficient funds! You have {sender_balance:,} 🪙 but need {amount:,} 🪙",
            ephemeral=True
        )
        return
    
    # Process the gift
    sender_new_balance = update_user_balance(interaction.user.id, -amount)
    receiver_new_balance = update_user_balance(user.id, amount)
    await save_cache()
    
    embed = discord.Embed(
        title="🎁 Gift Sent Successfully!",
        color=0x9932cc,
        timestamp=datetime.now()
    )
    embed.add_field(name="From", value=interaction.user.mention, inline=True)
    embed.add_field(name="To", value=user.mention, inline=True)
    embed.add_field(name="Amount", value=f"{amount:,} 🪙", inline=True)
    embed.add_field(name="Your New Balance", value=f"{sender_new_balance:,} 🪙", inline=True)
    embed.add_field(name="Recipient's New Balance", value=f"{receiver_new_balance:,} 🪙", inline=True)
    
    embed.set_author(
        name="Token Gift",
        icon_url="https://cdn.discordapp.com/emojis/741690892862291979.png"
    )
    
    await interaction.response.send_message(embed=embed, ephemeral=True)
    
    # Try to notify the recipient
    try:
        notify_embed = discord.Embed(
            title="🎁 You received a gift!",
            description=f"**{interaction.user.display_name}** sent you **{amount:,} 🪙**!",
            color=0x9932cc,
            timestamp=datetime.now()
        )
        notify_embed.add_field(name="Your New Balance", value=f"{receiver_new_balance:,} 🪙", inline=True)
        await user.send(embed=notify_embed)
    except:
        pass  # User might have DMs disabled
    
    # Log the gift
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

# Graceful shutdown
@bot.event
async def on_disconnect():
    print("Bot disconnected, saving data...")
    await save_cache()
    await log_action(
        "BOT_DISCONNECT",
        "🔴 Bot Disconnected",
        f"**{bot.user.name}** has gone offline",
        color=0xff0000
    )

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
            asyncio.run(save_cache())d = discord.Embed(
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
    total_spent = user_data.get('total_spent', 0)
    rank = get_user_rank(user_balance)
    
    embed = discord.Embed(
        title="💰 Token Wallet",
        color=0x2f3136,
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
        name="‎",  # Invisible character for spacing
        value="‎",
        inline=True
    )
    embed.add_field(
        name="Total Earned",
        value=f"{total_earned:,} 🪙",
        inline=True
    )
    embed.add_field(
        name="Total Spent",
        value=f"{total_spent:,} 🪙",
        inline=True
    )
    
    embed.set_author(
        name=interaction.user.display_name,
        icon_url=interaction.user.display_avatar.url
    )
    embed.set_footer(text="💬 Chat to earn 1-5 tokens per message")
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

class ShopView(discord.ui.View):
    def __init__(self, items, user_balance):
        super().__init__(timeout=300)
        self.items = items
        self.user_balance = user_balance
        
        # Add buy buttons for each item (max 25 components)
        for i, item in enumerate(items[:25]):  # Discord limit
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
            await self.buy_item(interaction, item_index)
        return buy_callback
    
    async def buy_item(self, interaction, item_index):
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
        
        # Process purchase
        new_balance = update_user_balance(interaction.user.id, -item['price'])
        add_purchase_history(interaction.user.id, item['name'], item['price'])
        await save_cache()
        
        # Success embed
        embed = discord.Embed(
            title="✅ Purchase Successful!",
            color=0x00ff00,
            timestamp=datetime.now()
        )
        embed.add_field(name="Item", value=item['name'], inline=True)
        embed.add_field(name="Cost", value=f"{item['price']:,} 🪙", inline=True)
        embed.add_field(name="New Balance", value=f"{new_balance:,} 🪙", inline=True)
        
        if item.get('description'):
            embed.add_field(name="Description", value=item['description'], inline=False)
        
        embed.set_author(
            name=interaction.user.display_name,
            icon_url=interaction.user.display_avatar.url
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
        # Log the purchase
        await log_action(
            "PURCHASE",
            "💳 Item Purchased",
            f"**{interaction.user.mention}** bought **{item['name']}**",
            color=0x00ff00,
            user=interaction.user,
            fields=[
                {"name": "Item", "value": item['name'], "inline": True},
                {"name": "Price", "value": f"{item['price']:,} 🪙", "inline": True},
                {"name": "New Balance", "value": f"{new_balance:,} 🪙", "inline": True}
            ]
        )

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
    
    # Show items in description
    items_text = ""
    for i, item in enumerate(shop_items[:10]):  # Show max 10 items
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

@bot.tree.command(name="buy", description="Buy an item by name and quantity")
async def buy(interaction: discord.Interaction, item_name: str, quantity: int = 1):
    if quantity <= 0:
        await interaction.response.send_message("❌ Quantity must be at least 1!", ephemeral=True)
        return
    
    shop_items = get_shop_items()
    item = None
    
    # Find item by name (case insensitive)
    for shop_item in shop_items:
        if shop_item['name'].lower() == item_name.lower():
            item = shop_item
            break
    
    if not item:
        # Show similar items
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
            f"❌ Insufficient funds!\n"
            f"**Cost:** {total_cost:,} 🪙 ({item['price']:,} × {quantity})\n"
            f"**Your Balance:** {user_balance:,} 🪙\n"
            f"**Need:** {total_cost - user_balance:,} more tokens",
            ephemeral=True
        )
        return
    
    # Process purchase
    new_balance = update_user_balance(interaction.user.id, -total_cost)
    add_purchase_history(interaction.user.id, item['name'], item['price'], quantity)
    await save_cache()
    
    # Success embed
    embed = discord.Embed(
        title="✅ Purchase Successful!",
        color=0x00ff00,
        timestamp=datetime.now()
    )
    embed.add_field(name="Item", value=item['name'], inline=True)
    embed.add_field(name="Quantity", value=str(quantity), inline=True)
    embed.add_field(name="Total Cost", value=f"{total_cost:,} 🪙", inline=True)
    embed.add_field(name="New Balance", value=f"{new_balance:,} 🪙", inline=False)
    
    if item.get('description'):
        embed.add_field(name="Description", value=item['description'], inline=False)
    
    embed.set_author(
        name=interaction.user.display_name,
        icon_url=interaction.user.display_avatar.url
    )
    
    await interaction.response.send_message(embed=embed, ephemeral=True)
    
    # Log the purchase
    await log_action(
        "PURCHASE",
        "💳 Item Purchased",
        f"**{interaction.user.mention}** bought **{quantity}x {item['name']}**",
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
    
    embed = discord.Embed(
        title="📋 Purchase History",
        color=0x9932cc,
        timestamp=datetime.now()
    )
    
    if not purchases:
        embed.description = "No purchases yet! Visit `/shop` to buy items."
    else:
        # Show last 10 purchases
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
    
    embed.set_author(
        name=interaction.user.display_name,
        icon_url=interaction.user.display_avatar.url
    )
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="leaderboard", description="View the top token holders")
async def leaderboard(interaction: discord.Interaction):
    # Sort users by balance
    sorted_users = sorted(
        user_data_cache.items(),
        key=lambda x: x[1].get('balance', 0),
        reverse=True
    )[:10]
    
    embed = discord.Embed(
        title="🏆 Token Leaderboard",
        color=0xffd700,
        timestamp=datetime.now()
    )
    
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
    await save_cache()
    
    embed = discord.Embed(
        title="✅ Tokens Added",
        color=0x00ff00,
        timestamp=datetime.now()
    )
    embed.add_field(name="User", value=user.mention, inline=True)
    embed.add_field(name="Amount Added", value=f"{amount:,} 🪙", inline=True)
    embed.add_field(name="New Balance", value=f"{new_balance:,} 🪙", inline=True)
    
    await interaction.response.send_message(embed=embed, ephemeral=True)
    
    # Log the action
    await log_action(
        "ADMIN_ADD_TOKENS",
        "➕ Tokens Added",
        f"**{interaction.user.mention}** added tokens to **{user.mention}**",
        color=0x00ff00,
        user=user,
        fields=[
            {"name": "Admin", "value": interaction.user.mention, "inline": True},
            {"name": "Amount Added", "value": f"{amount:,} 🪙", "inline": True},
            {"name": "Old Balance", "value": f"{old_balance:,} 🪙", "inline": True},
            {"name": "New Balance", "value": f"{new_balance:,} 🪙", "inline": True}
        ]
    )

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
    await save_cache()
    
    embed = discord.Embed(
        title="✅ Tokens Removed",
        color=0xff6600,
        timestamp=datetime.now()
    )
    embed.add_field(name="User", value=user.mention, inline=True)
    embed.add_field(name="Amount Removed", value=f"{amount:,} 🪙", inline=True)
    embed.add_field(name="New Balance", value=f"{new_balance:,} 🪙", inline=True)
    
    await interaction.response.send_message(embed=embed, ephemeral=True)
    
    # Log the action
    await log_action(
        "ADMIN_REMOVE_TOKENS",
        "➖ Tokens Removed",
        f"**{interaction.user.mention}** removed tokens from **{user.mention}**",
        color=0xff6600,
        user=user,
        fields=[
            {"name": "Admin", "value": interaction.user.mention, "inline": True},
            {"name": "Amount Removed", "value": f"{amount:,} 🪙", "inline": True},
            {"name": "Old Balance", "value": f"{current_balance:,} 🪙", "inline": True},
            {"name": "New Balance", "value": f"{new_balance:,} 🪙", "inline": True}
        ]
    )

@bot.tree.command(name="resetdata", description="Reset all user data (Admin only)")
async def resetdata(interaction: discord.Interaction):
    if not is_admin(interaction.user):
        await interaction.response.send_message("❌ You don't have permission to use this command!", ephemeral=True)
        return
    
    # Confirmation view
    view = ConfirmResetView(interaction.user)
    embed = discord.Embed(
        title="⚠️ DANGER ZONE",
        description="**This will permanently delete ALL user token data!**\n\n❌ This action cannot be undone!\n❌ All balances will be reset to 0!\n❌ All purchase history will be lost!",
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
        
        # Log the reset
        await log_action(
            "ADMIN_RESET_DATA",
            "🗑️ Data Reset",
            f"**{self.admin_user.mention}** reset all user data",
            color=0xff0000,
            user=self.admin_user,
            fields=[
                {"name": "Users Affected", "value": str(user_count), "inline": True},
                {"name": "Action", "value": "Complete data wipe", "inline": True}
            ]
        )
    
    @discord.ui.button(label="❌ Cancel", style=discord.ButtonStyle.grey)
    async def cancel_reset(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.admin_user:
            await interaction.response.send_message("❌ Only the admin who initiated this can cancel!", ephemeral=True)
            return
        
        embe
