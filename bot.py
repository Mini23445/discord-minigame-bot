import discord
from discord.ext import commands
import json
import os
import random
import asyncio
from datetime import datetime, timedelta
import time
import sys

# Railway logging setup
import logging
logging.basicConfig(level=logging.INFO)

print("Starting Discord Bot...")

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
cooldowns = {"daily": {}, "work": {}, "crime": {}, "gift": {}, "buy": {}, "coinflip": {}, "duel": {}}
pending_duels = {}

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
        print("Data loaded successfully")
    except Exception as e:
        print(f"Error loading data: {e}")

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
        print(f"Error saving data: {e}")

async def log_action(action_type, title, description, color=0x0099ff, user=None, fields=None):
    """Send log message to the log channel"""
    try:
        log_channel = bot.get_channel(LOG_CHANNEL_ID)
        if not log_channel:
            print(f"Log channel {LOG_CHANNEL_ID} not found!")
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
        print(f"Error sending log: {e}")

async def log_purchase(user, item_name, price, quantity=1):
    """Log purchase to purchase log channel"""
    try:
        purchase_channel = bot.get_channel(PURCHASE_LOG_CHANNEL_ID)
        if not purchase_channel:
            print(f"Purchase log channel {PURCHASE_LOG_CHANNEL_ID} not found!")
            return
        
        embed = discord.Embed(
            title="Purchase Made",
            color=0x00ff00,
            timestamp=datetime.now()
        )
        
        embed.add_field(name="User", value=user.mention, inline=True)
        embed.add_field(name="Item", value=item_name, inline=True)
        embed.add_field(name="Quantity", value=str(quantity), inline=True)
        embed.add_field(name="Total Cost", value=f"{price * quantity:,} tokens", inline=True)
        embed.add_field(name="Unit Price", value=f"{price:,} tokens", inline=True)
        
        embed.set_author(name=user.display_name, icon_url=user.display_avatar.url)
        await purchase_channel.send(embed=embed)
        
    except Exception as e:
        print(f"Error sending purchase log: {e}")

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
    if balance >= 100000: return "Legendary"
    elif balance >= 50000: return "Elite"
    elif balance >= 20000: return "VIP"
    elif balance >= 10000: return "Premium"
    elif balance >= 5000: return "Gold"
    elif balance >= 1000: return "Silver"
    else: return "Starter"

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
    """Check short cooldowns"""
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

# Clean up expired duels
async def cleanup_expired_duels():
    """Clean up expired duel challenges"""
    while True:
        await asyncio.sleep(300)  # 5 minutes
        current_time = datetime.now()
        expired_duels = []
        
        for duel_key, duel_data in pending_duels.items():
            try:
                created_at = duel_data['created_at']
                if (current_time - created_at).total_seconds() > 300:
                    expired_duels.append(duel_key)
            except:
                expired_duels.append(duel_key)
        
        for expired_key in expired_duels:
            del pending_duels[expired_key]

@bot.event
async def on_ready():
    print(f'{bot.user} is online!')
    load_data()
    
    # Start background tasks
    asyncio.create_task(auto_save())
    asyncio.create_task(cleanup_expired_duels())
    
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} commands")
    except Exception as e:
        print(f"Failed to sync: {e}")

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
        title="Token Wallet",
        color=0x7B68EE,
        timestamp=datetime.now()
    )
    
    embed.add_field(name="Current Balance", value=f"**{balance:,}** tokens", inline=True)
    embed.add_field(name="Rank", value=rank, inline=True)
    embed.add_field(name="Total Spent", value=f"{spent:,} tokens", inline=True)
    embed.add_field(name="Total Earned", value=f"{earned:,} tokens", inline=True)
    
    embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
    embed.set_footer(text="Chat to earn 1-5 tokens per message")
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="daily", description="Claim daily tokens (24h cooldown)")
async def daily(interaction: discord.Interaction):
    can_use, next_use = can_use_command(interaction.user.id, "daily", 24)
    
    if not can_use:
        time_left = format_time(next_use)
        await interaction.response.send_message(f"Daily already claimed! Come back in **{time_left}**", ephemeral=True)
        return
    
    tokens = random.randint(50, 200)
    new_balance = update_balance(interaction.user.id, tokens)
    cooldowns["daily"][str(interaction.user.id)] = datetime.now().isoformat()
    save_data()
    
    embed = discord.Embed(title="Daily Reward!", color=0x00ff00)
    embed.add_field(name="Earned", value=f"{tokens:,} tokens", inline=True)
    embed.add_field(name="Balance", value=f"{new_balance:,} tokens", inline=True)
    embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="work", description="Work for tokens (3h cooldown)")
async def work(interaction: discord.Interaction):
    can_use, next_use = can_use_command(interaction.user.id, "work", 3)
    
    if not can_use:
        time_left = format_time(next_use)
        await interaction.response.send_message(f"Still tired! Rest for **{time_left}** more", ephemeral=True)
        return
    
    tokens = random.randint(50, 300)
    job = random.choice(WORK_JOBS)
    new_balance = update_balance(interaction.user.id, tokens)
    cooldowns["work"][str(interaction.user.id)] = datetime.now().isoformat()
    save_data()
    
    embed = discord.Embed(title="Work Complete!", color=0x4CAF50)
    embed.add_field(name="Job", value=f"You {job}", inline=False)
    embed.add_field(name="Earned", value=f"{tokens:,} tokens", inline=True)
    embed.add_field(name="Balance", value=f"{new_balance:,} tokens", inline=True)
    embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="crime", description="Commit crime for tokens (1h cooldown, risky!)")
async def crime(interaction: discord.Interaction):
    can_use, next_use = can_use_command(interaction.user.id, "crime", 1)
    
    if not can_use:
        time_left = format_time(next_use)
        await interaction.response.send_message(f"Lay low for **{time_left}** more!", ephemeral=True)
        return
    
    success = random.choice([True, False])
    activity = random.choice(CRIME_ACTIVITIES)
    
    if success:
        tokens = random.randint(75, 400)
        new_balance = update_balance(interaction.user.id, tokens)
        embed = discord.Embed(title="Crime Success!", color=0x00ff00)
        embed.add_field(name="Crime", value=f"You {activity}", inline=False)
        embed.add_field(name="Gained", value=f"+{tokens:,} tokens", inline=True)
    else:
        tokens = random.randint(25, 200)
        current = get_user_balance(interaction.user.id)
        tokens = min(tokens, current)
        new_balance = update_balance(interaction.user.id, -tokens)
        embed = discord.Embed(title="Crime Failed!", color=0xff4444)
        embed.add_field(name="Crime", value=f"Tried to {activity}", inline=False)
        embed.add_field(name="Lost", value=f"-{tokens:,} tokens", inline=True)
    
    embed.add_field(name="Balance", value=f"{new_balance:,} tokens", inline=True)
    embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
    
    cooldowns["crime"][str(interaction.user.id)] = datetime.now().isoformat()
    save_data()
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="coinflip", description="Bet tokens on a coinflip")
async def coinflip(interaction: discord.Interaction, amount: int, choice: str):
    if not can_use_short_cooldown(interaction.user.id, "coinflip", 5):
        await interaction.response.send_message("Please wait 5 seconds between coinflips!", ephemeral=True)
        return
    
    if amount <= 0:
        await interaction.response.send_message("Bet amount must be greater than 0!", ephemeral=True)
        return
    
    choice = choice.lower()
    if choice not in ['heads', 'tails', 'h', 't']:
        await interaction.response.send_message("Choose 'heads' or 'tails' (or 'h'/'t')!", ephemeral=True)
        return
    
    if choice in ['h', 'heads']:
        choice = 'heads'
    else:
        choice = 'tails'
    
    balance = get_user_balance(interaction.user.id)
    if balance < amount:
        await interaction.response.send_message(f"Insufficient funds! You need **{amount - balance:,}** more tokens.", ephemeral=True)
        return
    
    result = random.choice(['heads', 'tails'])
    won = choice == result
    
    if won:
        winnings = amount
        new_balance = update_balance(interaction.user.id, winnings)
        embed = discord.Embed(title="Coinflip - YOU WON!", color=0x00ff00)
        embed.add_field(name="Your Choice", value=choice.title(), inline=True)
        embed.add_field(name="Result", value=result.title(), inline=True)
        embed.add_field(name="Winnings", value=f"+{winnings:,} tokens", inline=True)
    else:
        new_balance = update_balance(interaction.user.id, -amount)
        embed = discord.Embed(title="Coinflip - YOU LOST!", color=0xff4444)
        embed.add_field(name="Your Choice", value=choice.title(), inline=True)
        embed.add_field(name="Result", value=result.title(), inline=True)
        embed.add_field(name="Lost", value=f"-{amount:,} tokens", inline=True)
    
    embed.add_field(name="New Balance", value=f"{new_balance:,} tokens", inline=False)
    embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
    
    set_short_cooldown(interaction.user.id, "coinflip")
    save_data()
    
    await log_action(
        "COINFLIP",
        f"Coinflip {'Win' if won else 'Loss'}",
        f"{interaction.user.mention} {'won' if won else 'lost'} **{amount:,} tokens** on coinflip",
        color=0x00ff00 if won else 0xff4444,
        user=interaction.user
    )
    
    await interaction.response.send_message(embed=embed)

class DuelAcceptView(discord.ui.View):
    def __init__(self, challenger_id, challenged_id, amount):
        super().__init__(timeout=60)
        self.challenger_id = challenger_id
        self.challenged_id = challenged_id
        self.amount = amount
    
    @discord.ui.button(label="Accept Duel", style=discord.ButtonStyle.green)
    async def accept_duel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.challenged_id:
            await interaction.response.send_message("This duel is not for you!", ephemeral=True)
            return
        
        challenger_balance = get_user_balance(self.challenger_id)
        challenged_balance = get_user_balance(self.challenged_id)
        
        if challenger_balance < self.amount:
            await interaction.response.send_message("The challenger no longer has enough tokens!", ephemeral=True)
            return
        
        if challenged_balance < self.amount:
            await interaction.response.send_message(f"You don't have enough tokens! Need {self.amount - challenged_balance:,} more.", ephemeral=True)
            return
        
        duel_key = f"{self.challenger_id}_{self.challenged_id}"
        if duel_key in pending_duels:
            del pending_duels[duel_key]
        
        winner_id = random.choice([self.challenger_id, self.challenged_id])
        loser_id = self.challenged_id if winner_id == self.challenger_id else self.challenger_id
        
        update_balance(winner_id, self.amount)
        update_balance(loser_id, -self.amount)
        save_data()
        
        winner = bot.get_user(winner_id)
        loser = bot.get_user(loser_id)
        
        embed = discord.Embed(title="Duel Complete!", color=0xFFD700)
        embed.add_field(name="Winner", value=winner.mention, inline=True)
        embed.add_field(name="Loser", value=loser.mention, inline=True)
        embed.add_field(name="Amount", value=f"{self.amount:,} tokens", inline=True)
        embed.add_field(name="Winner's Balance", value=f"{get_user_balance(winner_id):,} tokens", inline=True)
        embed.add_field(name="Loser's Balance", value=f"{get_user_balance(loser_id):,} tokens", inline=True)
        
        embed.set_footer(text="The coin has decided!")
        
        await log_action(
            "DUEL",
            "Duel Completed",
            f"Duel between {bot.get_user(self.challenger_id).mention} and {bot.get_user(self.challenged_id).mention}",
            color=0xFFD700,
            user=winner
        )
        
        await interaction.response.edit_message(embed=embed, view=None)
    
    @discord.ui.button(label="Decline Duel", style=discord.ButtonStyle.red)
    async def decline_duel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.challenged_id:
            await interaction.response.send_message("This duel is not for you!", ephemeral=True)
            return
        
        duel_key = f"{self.challenger_id}_{self.challenged_id}"
        if duel_key in pending_duels:
            del pending_duels[duel_key]
        
        challenger = bot.get_user(self.challenger_id)
        embed = discord.Embed(
            title="Duel Declined", 
            description=f"{interaction.user.mention} declined the duel challenge from {challenger.mention}.",
            color=0xff4444
        )
        
        await interaction.response.edit_message(embed=embed, view=None)

@bot.tree.command(name="duel", description="Challenge another user to a coinflip duel")
async def duel(interaction: discord.Interaction, user: discord.Member, amount: int):
    if not can_use_short_cooldown(interaction.user.id, "duel", 10):
        await interaction.response.send_message("Please wait 10 seconds between duel challenges!", ephemeral=True)
        return
    
    if amount <= 0:
        await interaction.response.send_message("Duel amount must be greater than 0!", ephemeral=True)
        return
    
    if user.id == interaction.user.id:
        await interaction.response.send_message("You can't duel yourself!", ephemeral=True)
        return
    
    if user.bot:
        await interaction.response.send_message("You can't duel bots!", ephemeral=True)
        return
    
    challenger_balance = get_user_balance(interaction.user.id)
    if challenger_balance < amount:
        await interaction.response.send_message(f"You need **{amount - challenger_balance:,}** more tokens to make this challenge!", ephemeral=True)
        return
    
    challenged_balance = get_user_balance(user.id)
    if challenged_balance < amount:
        await interaction.response.send_message(f"{user.mention} doesn't have enough tokens for this duel! They need {amount - challenged_balance:,} more.", ephemeral=True)
        return
    
    duel_key = f"{interaction.user.id}_{user.id}"
    reverse_duel_key = f"{user.id}_{interaction.user.id}"
    
    if duel_key in pending_duels or reverse_duel_key in pending_duels:
        await interaction.response.send_message("There's already a pending duel between you two!", ephemeral=True)
        return
    
    pending_duels[duel_key] = {
        'challenger': interaction.user.id,
        'challenged': user.id,
        'amount': amount,
        'created_at': datetime.now()
    }
    
    set_short_cooldown(interaction.user.id, "duel")
    
    embed = discord.Embed(
        title="Duel Challenge!",
        description=f"{interaction.user.mention} challenges {user.mention} to a duel!",
        color=0xFFD700
    )
    
    embed.add_field(name="Stakes", value=f"{amount:,} tokens", inline=True)
    embed.add_field(name="Rules", value="Winner takes all!\nCoinflip decides the victor", inline=True)
    embed.add_field(name="Expires", value="60 seconds", inline=True)
    
    embed.add_field(name="Challenger Balance", value=f"{challenger_balance:,} tokens", inline=True)
    embed.add_field(name="Challenged Balance", value=f"{challenged_balance:,} tokens", inline=True)
    
    embed.set_footer(text=f"{user.display_name}, will you accept this challenge?")
    
    view = DuelAcceptView(interaction.user.id, user.id, amount)
    await interaction.response.send_message(embed=embed, view=view)

@bot.tree.command(name="gift", description="Gift tokens to another user")
async def gift(interaction: discord.Interaction, user: discord.Member, amount: int):
    if not can_use_short_cooldown(interaction.user.id, "gift", 3):
        await interaction.response.send_message("Please wait 3 seconds between gifts!", ephemeral=True)
        return
    
    if amount <= 0:
        await interaction.response.send_message("Amount must be greater than 0!", ephemeral=True)
        return
    
    if user.id == interaction.user.id:
        await interaction.response.send_message("Can't gift to yourself!", ephemeral=True)
        return
    
    if user.bot:
        await interaction.response.send_message("Can't gift to bots!", ephemeral=True)
        return
    
    giver_balance = get_user_balance(interaction.user.id)
    if giver_balance < amount:
        await interaction.response.send_message(f"Need **{amount - giver_balance:,}** more tokens!", ephemeral=True)
        return
    
    update_balance(interaction.user.id, -amount)
    update_balance(user.id, amount)
    set_short_cooldown(interaction.user.id, "gift")
    save_data()
    
    await log_action(
        "GIFT",
        "Token Gift",
        f"{interaction.user.mention} gifted **{amount:,} tokens** to {user.mention}",
        color=0xffb347,
        user=interaction.user
    )
    
    message = f"{interaction.user.mention} gifted **{amount:,} tokens** to {user.mention}!"
    await interaction.response.send_message(message)

@bot.tree.command(name="leaderboard", description="View the top token holders")
async def leaderboard(interaction: discord.Interaction, page: int = 1):
    if not user_data:
        embed = discord.Embed(
            title="Token Leaderboard",
            description="No users have earned tokens yet!",
            color=0x0099ff
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    sorted_users = []
    for user_id, data in user_data.items():
        balance = data.get('balance', 0)
        if balance > 0:
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
            title="Token Leaderboard",
            description="No users with tokens found!",
            color=0x0099ff
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    per_page = 10
    max_pages = (len(sorted_users) + per_page - 1) // per_page
    page = max(1, min(page, max_pages))
    
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    page_users = sorted_users[start_idx:end_idx]
    
    embed = discord.Embed(
        title="Token Leaderboard",
        color=0xFFD700,
        timestamp=datetime.now()
    )
    
    leaderboard_text = ""
    for i, user_data_item in enumerate(page_users, start=start_idx + 1):
        user = user_data_item['user']
        balance = user_data_item['balance']
        rank = user_data_item['rank']
        
        if i == 1:
            medal = "🥇"
        elif i == 2:
            medal = "🥈"
        elif i == 3:
            medal = "🥉"
        else:
            medal = f"**{i}.**"
        
        leaderboard_text += f"{medal} **{user.display_name}** - {balance:,} tokens ({rank})\n"
    
    embed.add_field(name="Rankings", value=leaderboard_text, inline=False)
    
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
            value=f"**#{user_position}** - {user_balance:,} tokens ({user_rank})",
            inline=False
        )
    
    embed.set_footer(text=f"Page {page}/{max_pages} • {len(sorted_users)} total users")
    
    await interaction.response.send_message(embed=embed, ephemeral=False)

@bot.tree.command(name="adminbalance", description="Check user balance (Admin only)")
async def adminbalance(interaction: discord.Interaction, user: discord.Member):
    if not is_admin(interaction.user):
        await interaction.response.send_message("Admin only!", ephemeral=True)
        return
    
    user_id = str(user.id)
    balance = get_user_balance(user.id)
    data = user_data.get(user_id, {})
    earned = data.get('total_earned', 0)
    spent = data.get('total_spent', 0)
    rank = get_rank(balance)
    
    embed = discord.Embed(title=f"{user.display_name}'s Wallet", color=0xFF6B6B)
    embed.add_field(name="Balance", value=f"**{balance:,}** tokens", inline=True)
    embed.add_field(name="Rank", value=rank, inline=True)
    embed.add_field(name="Spent", value=f"{spent:,} tokens", inline=True)
    embed.add_field(name="Earned", value=f"{earned:,} tokens", inline=True)
    embed.set_author(name=user.display_name, icon_url=user.display_avatar.url)
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="addtoken", description="Add tokens (Admin only)")
async def addtoken(interaction: discord.Interaction, user: discord.Member, amount: int):
    if not is_admin(interaction.user):
        await interaction.response.send_message("Admin only!", ephemeral=True)
        return
    
    if amount <= 0:
        await interaction.response.send_message("Amount must be positive!", ephemeral=True)
        return
    
    new_balance = update_balance(user.id, amount)
    save_data()
    
    await log_action(
        "ADD_TOKENS",
        "Tokens Added",
        f"**{interaction.user.mention}** added **{amount:,} tokens** to {user.mention}",
        color=0x00ff00,
        user=interaction.user
    )
    
    embed = discord.Embed(title="Tokens Added", color=0x00ff00)
    embed.add_field(name="User", value=user.mention, inline=True)
    embed.add_field(name="Added", value=f"{amount:,} tokens", inline=True)
    embed.add_field(name="New Balance", value=f"{new_balance:,} tokens", inline=True)
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.command(name="about")
async def about(ctx):
    """Traditional text command for bot info"""
    embed = discord.Embed(
        title="Bot Commands Guide",
        description="Here are all the commands you can use to earn and spend tokens!",
        color=0x7B68EE,
        timestamp=datetime.now()
    )
    
    embed.add_field(
        name="Economy Commands",
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
    
    embed.add_field(
        name="Information Commands",
        value=(
            "`/leaderboard [page]` - View top token holders\n"
            "`!about` - Show this help message"
        ),
        inline=False
    )
    
    embed.add_field(
        name="Passive Earning",
        value="You earn **1-5 tokens** automatically for each message you send in the server!",
        inline=False
    )
    
    embed.add_field(
        name="Rank System",
        value=(
            "**Starter** - 0+ tokens\n"
            "**Silver** - 1,000+ tokens\n"
            "**Gold** - 5,000+ tokens\n"
            "**Premium** - 10,000+ tokens\n"
            "**VIP** - 20,000+ tokens\n"
            "**Elite** - 50,000+ tokens\n"
            "**Legendary** - 100,000+ tokens"
        ),
        inline=False
    )
    
    embed.add_field(
        name="Tips",
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

# Run the bot
if __name__ == "__main__":
    TOKEN = os.getenv('DISCORD_BOT_TOKEN')
    
    if not TOKEN:
        print("ERROR: DISCORD_BOT_TOKEN environment variable not found!")
        print("Set it in Railway dashboard under Variables tab")
        sys.exit(1)
    
    try:
        print("Token found, connecting to Discord...")
        bot.run(TOKEN, log_handler=None)
    except discord.LoginFailure:
        print("Invalid bot token!")
        sys.exit(1)
    except Exception as e:
        print(f"Error starting bot: {e}")
        sys.exit(1)
