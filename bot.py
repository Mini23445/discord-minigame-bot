import discord
from discord.ext import commands
import json
import os
import random
import asyncio
from datetime import datetime

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
        print(f"Error saving data: {e}")

def get_user_balance(user_id):
    """Get user's token balance"""
    user_data = load_data(USER_DATA_FILE)
    return user_data.get(str(user_id), {}).get('balance', 0)

def update_user_balance(user_id, amount):
    """Update user's token balance"""
    user_data = load_data(USER_DATA_FILE)
    user_id_str = str(user_id)
    
    if user_id_str not in user_data:
        user_data[user_id_str] = {'balance': 0, 'total_earned': 0}
    
    user_data[user_id_str]['balance'] += amount
    if amount > 0:
        user_data[user_id_str]['total_earned'] = user_data[user_id_str].get('total_earned', 0) + amount
    
    save_data(USER_DATA_FILE, user_data)
    return user_data[user_id_str]['balance']

def get_shop_items():
    """Get all shop items"""
    return load_data(SHOP_DATA_FILE, [])

def save_shop_items(items):
    """Save shop items"""
    save_data(SHOP_DATA_FILE, items)

def is_admin(user):
    """Check if user has admin role"""
    return any(role.id == ADMIN_ROLE_ID for role in user.roles)

@bot.event
async def on_ready():
    print(f'{bot.user} has landed! 🚀')
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
    user_data = load_data(USER_DATA_FILE)
    total_earned = user_data.get(str(interaction.user.id), {}).get('total_earned', 0)
    
    embed = discord.Embed(
        title="💰 Token Balance",
        color=0x00ff00,
        timestamp=datetime.now()
    )
    embed.set_author(
        name=interaction.user.display_name,
        icon_url=interaction.user.display_avatar.url
    )
    embed.add_field(
        name="🪙 Current Balance",
        value=f"**{user_balance:,}** Tokens",
        inline=False
    )
    embed.add_field(
        name="📈 Total Earned",
        value=f"**{total_earned:,}** Tokens",
        inline=False
    )
    embed.set_footer(text="Keep chatting to earn more tokens! 💬")
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="shop", description="View the shop")
async def shop(interaction: discord.Interaction):
    shop_items = get_shop_items()
    
    embed = discord.Embed(
        title="🛒 Token Shop",
        color=0x0099ff,
        timestamp=datetime.now()
    )
    
    if not shop_items:
        embed.description = "🚫 The shop is currently empty!"
    else:
        shop_text = ""
        for i, item in enumerate(shop_items, 1):
            shop_text += f"**{i}.** {item['name']}\n"
            shop_text += f"💰 **{item['price']:,}** Tokens\n"
            if item.get('description'):
                shop_text += f"📝 *{item['description']}*\n"
            shop_text += "\n"
        
        embed.description = shop_text
    
    embed.set_footer(text="Use tokens to purchase items! 💳")
    await interaction.response.send_message(embed=embed)

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
        bot.run(TOKEN)
