import discord
from discord.ext import commands
import random
import asyncio
import json
import os
from typing import Optional
import time
import shutil
from threading import Thread
from http.server import HTTPServer, BaseHTTPRequestHandler

# Bot configuration
GAME_CHANNEL_ID = 1410685631486628042  # Updated game channel
REDEEM_CHANNEL_ID = 1412142445327683687  # Updated redeem logs channel
LOG_CHANNEL_ID = 1412142500952408215     # New general logs channel
PING_ROLE_ID = 1412030131937083392

# Gift channels where /gift command works
GIFT_CHANNELS = [1410685631486628042, 1411246877781004359, 1410690717847785512]

# Initialize bot
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Game data
message_count = 0
active_games = {}
game_timeouts = {}  # Store timeout tasks so we can cancel them
user_balances = {}
last_games = []
gift_cooldowns = {}  # Track gift command cooldowns

# Word list for unscramble game
WORDS = [
    "cat", "dog", "car", "sun", "moon", "tree", "book", "water", "fire", "house",
    "phone", "table", "chair", "apple", "bread", "music", "happy", "friend", "game",
    "smile", "heart", "light", "night", "dream", "peace", "love", "hope", "time",
    "world", "school", "learn", "color", "sound", "voice", "money", "story", "party",
    "summer", "winter", "spring", "beach", "ocean", "mountain", "flower", "garden",
    "cookie", "pizza", "coffee", "dance", "laugh", "play", "work", "family", "magic",
    "star", "cloud", "river", "forest", "bird", "fish", "grass", "stone", "wind",
    "tiger", "eagle", "horse", "lion", "snake", "whale", "shark", "zebra", "panda",
    "butterfly", "spider", "rabbit", "turtle", "frog", "bear", "wolf", "fox", "deer",
    "guitar", "piano", "drums", "violin", "flute", "trumpet", "singer", "artist",
    "painter", "writer", "doctor", "teacher", "pilot", "chef", "farmer", "builder",
    "rocket", "planet", "galaxy", "alien", "robot", "future", "space", "earth",
    "castle", "prince", "queen", "knight", "dragon", "wizard", "fairy", "giant",
    "treasure", "adventure", "journey", "explore", "discover", "create", "imagine"
]

COLORS = ["red", "blue", "green", "yellow", "purple", "orange"]

def format_gems(amount):
    """Format gem amounts with M, B suffixes"""
    if amount >= 1000000000:
        return f"{amount / 1000000000:.1f}B".replace('.0B', 'B')
    elif amount >= 1000000:
        return f"{amount / 1000000:.1f}M".replace('.0M', 'M')
    else:
        return f"{amount:,}"

def parse_amount(amount_str):
    """Parse amount string with M, B suffixes and commas"""
    amount_str = amount_str.lower().strip().replace(',', '')
    
    if amount_str.endswith('m'):
        try:
            return int(float(amount_str[:-1]) * 1000000)
        except ValueError:
            return None
    elif amount_str.endswith('b'):
        try:
            return int(float(amount_str[:-1]) * 1000000000)
        except ValueError:
            return None
    else:
        try:
            return int(amount_str)
        except ValueError:
            return None

def load_balances():
    global user_balances
    try:
        with open('balances.json', 'r') as f:
            user_balances = json.load(f)
    except FileNotFoundError:
        user_balances = {}
    except json.JSONDecodeError:
        print("Warning: balances.json is corrupted. Starting with empty balances.")
        user_balances = {}

def save_balances():
    try:
        # Create backup first
        if os.path.exists('balances.json'):
            shutil.copy('balances.json', 'balances_backup.json')
        
        with open('balances.json', 'w') as f:
            json.dump(user_balances, f, indent=2)
    except Exception as e:
        print(f"Error saving balances: {e}")
        # Try to restore from backup if save failed
        if os.path.exists('balances_backup.json'):
            try:
                shutil.copy('balances_backup.json', 'balances.json')
                print("Restored balances from backup")
            except:
                print("Failed to restore from backup")

def get_balance(user_id):
    return user_balances.get(str(user_id), 0)

def add_gems(user_id, amount):
    user_balances[str(user_id)] = get_balance(user_id) + amount
    save_balances()

def remove_gems(user_id, amount):
    current = get_balance(user_id)
    if current >= amount:
        user_balances[str(user_id)] = current - amount
        save_balances()
        return True
    return False

def load_message_count():
    global message_count
    try:
        with open('message_count.json', 'r') as f:
            data = json.load(f)
            message_count = data.get('count', 0)
    except FileNotFoundError:
        message_count = 0
    except json.JSONDecodeError:
        print("Warning: message_count.json is corrupted. Starting with 0.")
        message_count = 0

def save_message_count():
    try:
        with open('message_count.json', 'w') as f:
            json.dump({'count': message_count}, f)
    except Exception as e:
        print(f"Error saving message count: {e}")

def reset_message_count():
    global message_count
    message_count = 0
    save_message_count()
    print("Message counter reset to 0 and saved")

@bot.event
async def on_ready():
    print(f'{bot.user} has landed!')
    print(f'Connected to {len(bot.guilds)} servers')
    load_balances()
    load_message_count()
    print(f'Loaded message count: {message_count}')
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} slash commands!")
    except Exception as e:
        print(f"Failed to sync commands: {e}")

@bot.event
async def on_message(message):
    try:
        if message.author.bot:
            return

        global message_count

        if message.channel.id == GAME_CHANNEL_ID:
            message_count += 1
            
            await check_game_answer(message)
            
            if message_count >= 15 and message.channel.id not in active_games:
                message_count = 0
                await start_mini_game(message.channel)
        
        await bot.process_commands(message)
    except Exception as e:
        print(f"Error in on_message: {e}")

async def check_game_answer(message):
    try:
        global active_games
        
        if message.channel.id not in active_games:
            return
        
        game_data = active_games[message.channel.id]
        
        if game_data.get('winner'):
            return
        
        game_type = game_data['type']
        correct_answer = game_data['answer']
        
        user_answer = message.content.strip().lower()
        
        is_correct = False
        
        if game_type == "number" and user_answer.isdigit() and len(user_answer) <= 2:
            try:
                user_num = int(user_answer)
                is_correct = user_num == correct_answer
            except ValueError:
                return
        elif game_type == "unscramble" and len(user_answer.split()) == 1:
            is_correct = user_answer == correct_answer.lower()
        elif game_type == "color" and len(user_answer.split()) == 1:
            is_correct = user_answer == correct_answer.lower()
        
        if is_correct:
            # Double check game is still active and no winner yet
            if message.channel.id not in active_games or active_games[message.channel.id].get('winner'):
                return
            
            # Mark as winner IMMEDIATELY to prevent timeout from running
            active_games[message.channel.id]['winner'] = message.author
            
            try:
                gems_won = 15000000
                add_gems(message.author.id, gems_won)
                
                # Create winner embed
                embed = discord.Embed(color=0x00D26A)
                
                if game_type == "number":
                    embed.title = "🎊 Winner!"
                    embed.description = f"**{message.author.display_name}** won! The answer was **{correct_answer}** 🎉"
                elif game_type == "unscramble":
                    embed.title = "🎊 Winner!"
                    embed.description = f"**{message.author.display_name}** won! The answer was **{correct_answer.upper()}** 🎉"
                elif game_type == "color":
                    embed.title = "🎊 Winner!"
                    embed.description = f"**{message.author.display_name}** won! The answer was **{correct_answer}** 🎉"
                
                embed.add_field(name="💰 Earned", value="`+15M` 💎", inline=True)
                embed.add_field(name="Next Game", value="`15 messages`", inline=True)
                
                if message.author.avatar:
                    embed.set_thumbnail(url=message.author.avatar.url)
                
                await message.channel.send(embed=embed)
                
            except Exception as e:
                print(f"Error sending winner message: {e}")
                # Fallback message if embed fails
                await message.channel.send(f"{message.author.mention} won! +20M gems")
            
            # Remove the game IMMEDIATELY after winner is declared
            # This prevents the timeout function from running
            if message.channel.id in active_games:
                del active_games[message.channel.id]
                
                # Cancel the timeout task to prevent it from running
                if message.channel.id in game_timeouts:
                    timeout_task = game_timeouts[message.channel.id]
                    timeout_task.cancel()
                    del game_timeouts[message.channel.id]
                
                print(f"Game won by {message.author.display_name} - {game_type} game")
                
                print(f"Game ended early - {message.author.display_name} won {game_type} game")
                
                # Log the win to the log channel
                try:
                    log_channel = bot.get_channel(LOG_CHANNEL_ID)
                    if log_channel:
                        log_embed = discord.Embed(
                            title="🎉 Mini-Game Winner",
                            color=0x00D26A
                        )
                        log_embed.add_field(name="👤 Winner", value=f"{message.author.mention}\n`{message.author.id}`", inline=True)
                        log_embed.add_field(name="🎮 Game Type", value=f"**{game_type.title()}**", inline=True)
                        log_embed.add_field(name="💰 Gems Awarded", value="**15M** 💎", inline=True)
                        log_embed.add_field(name="🏆 Answer", value=f"**{correct_answer}**", inline=True)
                        log_embed.add_field(name="📍 Channel", value=f"<#{message.channel.id}>", inline=True)
                        log_embed.timestamp = discord.utils.utcnow()
                        await log_channel.send(embed=log_embed)
                except Exception as e:
                    print(f"Error logging winner: {e}")
                    
    except Exception as e:
        print(f"Error in check_game_answer: {e}")
        # If something goes wrong, try to clean up the game
        if message.channel.id in active_games:
            del active_games[message.channel.id]

async def start_mini_game(channel):
    global active_games, last_games, message_count
    
    try:
        # Reset message counter when starting any game
        message_count = 0
        print(f"Starting mini-game - message counter reset to 0")
        
        await channel.send(f"<@&{PING_ROLE_ID}>")
        
        all_games = ["number", "unscramble", "color"]
        
        if len(last_games) < 2:
            available_games = all_games
        else:
            available_games = [game for game in all_games if game != last_games[-1]]
        
        game_type = random.choice(available_games)
        
        last_games.append(game_type)
        if len(last_games) > 2:
            last_games.pop(0)
        
        if game_type == "number":
            await start_number_game(channel)
        elif game_type == "unscramble":
            await start_unscramble_game(channel)
        elif game_type == "color":
            await start_color_game(channel)
    except Exception as e:
        print(f"Error starting mini game: {e}")

async def start_number_game(channel):
    try:
        number = random.randint(1, 10)
        active_games[channel.id] = {"type": "number", "answer": number, "winner": None, "start_time": asyncio.get_event_loop().time()}
        
        end_time = int(time.time() + 18)
        
        embed = discord.Embed(
            title="🎲 Number Challenge",
            description="**Guess the correct number** 🎯",
            color=0x00FFFF
        )
        embed.add_field(name="🎯 Range", value="`1` - `10`", inline=True)
        embed.add_field(name="💰 Reward", value="`15M` 💎", inline=True)
        embed.add_field(name="⏰ Ends", value=f"<t:{end_time}:R>", inline=True)
        
        await channel.send(embed=embed)
        
        # Store the timeout task so we can cancel it if someone wins
        timeout_task = asyncio.create_task(game_timeout(channel.id, number, "number"))
        game_timeouts[channel.id] = timeout_task
        
        # Log game start
        try:
            log_channel = bot.get_channel(LOG_CHANNEL_ID)
            if log_channel:
                log_embed = discord.Embed(
                    title="🎲 Number Game Started",
                    color=0x00FFFF
                )
                log_embed.add_field(name="📍 Channel", value=f"<#{channel.id}>", inline=True)
                log_embed.add_field(name="🎯 Answer", value=f"**{number}**", inline=True)
                log_embed.add_field(name="⏰ Duration", value="18 seconds", inline=True)
                log_embed.timestamp = discord.utils.utcnow()
                await log_channel.send(embed=log_embed)
        except Exception as e:
            print(f"Error logging game start: {e}")
    except Exception as e:
        print(f"Error starting number game: {e}")

async def game_timeout(channel_id, answer, game_type):
    """Handle game timeout independently"""
    try:
        await asyncio.sleep(18)
        
        # Check if game is still active and no winner
        if channel_id in active_games:
            game_data = active_games[channel_id]
            if not game_data.get('winner'):
                channel = bot.get_channel(channel_id)
                if channel:
                    embed = discord.Embed(
                        title="Time's Up!",
                        color=0xFF0000
                    )
                    
                    if game_type == "number":
                        embed.add_field(name="🎲 Answer", value=f"The number was **{answer}**", inline=False)
                    elif game_type == "unscramble":
                        embed.add_field(name="🔤 Answer", value=f"The word was **{answer.upper()}**", inline=False)
                    elif game_type == "color":
                        embed.add_field(name="🎨 Answer", value=f"The color was **{answer}**", inline=False)
                    
                    embed.set_footer(text="Next Mini-Game in 100 messages")
                    await channel.send(embed=embed)
                
                # Always remove the game after timeout
                del active_games[channel_id]
                print(f"Game timeout: {game_type} game ended, answer was {answer}")
    except Exception as e:
        print(f"Error in game timeout: {e}")
        # Force remove the game even if there's an error
        if channel_id in active_games:
            del active_games[channel_id]

async def start_unscramble_game(channel):
    try:
        word = random.choice(WORDS)
        scrambled = list(word)
        
        # Better scrambling algorithm to ensure it's actually scrambled
        max_attempts = 50
        attempts = 0
        while ''.join(scrambled) == word and attempts < max_attempts:
            random.shuffle(scrambled)
            attempts += 1
        
        scrambled_word = ''.join(scrambled)
        
        active_games[channel.id] = {"type": "unscramble", "answer": word, "winner": None, "start_time": asyncio.get_event_loop().time()}
        
        end_time = int(time.time() + 18)
        
        embed = discord.Embed(
            title="🧩 Word Scramble",
            description=f"**Unscramble the word** 🔤\n```{scrambled_word.upper()}```",
            color=0x00FFFF
        )
        embed.add_field(name="📝 Letters", value=f"`{len(word)}`", inline=True)
        embed.add_field(name="💰 Reward", value="`15M` 💎", inline=True)
        embed.add_field(name="⏰ Ends", value=f"<t:{end_time}:R>", inline=True)
        
        await channel.send(embed=embed)
        
        # Store the timeout task so we can cancel it if someone wins
        timeout_task = asyncio.create_task(game_timeout(channel.id, word, "unscramble"))
        game_timeouts[channel.id] = timeout_task
        
        # Log game start
        try:
            log_channel = bot.get_channel(LOG_CHANNEL_ID)
            if log_channel:
                log_embed = discord.Embed(
                    title="🧩 Word Scramble Started",
                    color=0x00FFFF
                )
                log_embed.add_field(name="📍 Channel", value=f"<#{channel.id}>", inline=True)
                log_embed.add_field(name="🔤 Answer", value=f"**{word.upper()}**", inline=True)
                log_embed.add_field(name="🔀 Scrambled", value=f"`{scrambled_word.upper()}`", inline=True)
                log_embed.timestamp = discord.utils.utcnow()
                await log_channel.send(embed=log_embed)
        except Exception as e:
            print(f"Error logging game start: {e}")
    except Exception as e:
        print(f"Error starting unscramble game: {e}")

async def start_color_game(channel):
    try:
        color = random.choice(COLORS)
        active_games[channel.id] = {"type": "color", "answer": color, "winner": None, "start_time": asyncio.get_event_loop().time()}
        
        end_time = int(time.time() + 18)
        
        embed = discord.Embed(
            title="🎨 Color Challenge",
            description="**Choose the correct color** 🌈",
            color=0x00FFFF
        )
        embed.add_field(name="🌈 Options", value="`red` `blue` `green` `yellow` `purple` `orange`", inline=False)
        embed.add_field(name="💰 Reward", value="`15M` 💎", inline=True)
        embed.add_field(name="⏰ Ends", value=f"<t:{end_time}:R>", inline=True)
        
        await channel.send(embed=embed)
        
        # Store the timeout task so we can cancel it if someone wins
        timeout_task = asyncio.create_task(game_timeout(channel.id, color, "color"))
        game_timeouts[channel.id] = timeout_task
        
        # Log game start
        try:
            log_channel = bot.get_channel(LOG_CHANNEL_ID)
            if log_channel:
                log_embed = discord.Embed(
                    title="🎨 Color Game Started",
                    color=0x00FFFF
                )
                log_embed.add_field(name="📍 Channel", value=f"<#{channel.id}>", inline=True)
                log_embed.add_field(name="🌈 Answer", value=f"**{color}**", inline=True)
                log_embed.add_field(name="⏰ Duration", value="18 seconds", inline=True)
                log_embed.timestamp = discord.utils.utcnow()
                await log_channel.send(embed=log_embed)
        except Exception as e:
            print(f"Error logging game start: {e}")
    except Exception as e:
        print(f"Error starting color game: {e}")

@bot.tree.command(name="balance", description="Check your gem balance")
async def balance(interaction: discord.Interaction):
    try:
        user_gems = get_balance(interaction.user.id)
        
        embed = discord.Embed(
            title="💎 Your Gem Balance",
            color=0x5865F2
        )
        embed.add_field(
            name="💰 Current Balance",
            value=f"{format_gems(user_gems)} Gems",
            inline=False
        )
        embed.set_footer(text="Keep playing mini-games to earn more! 🎮")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    except Exception as e:
        print(f"Error in balance command: {e}")
        await interaction.response.send_message("An error occurred while checking your balance.", ephemeral=True)

@bot.tree.command(name="redeem", description="Redeem your gems (minimum 10M)")
async def redeem(interaction: discord.Interaction, amount: str):
    try:
        parsed_amount = parse_amount(amount)
        
        if parsed_amount is None:
            embed = discord.Embed(
                title="❌ Invalid Format",
                description="Please use formats like: `10m`, `1.5b`, `5,000,000`, or `50000000`\n\n**Examples:**\n• `10m` = 10 million\n• `1b` = 1 billion\n• `5,000,000` = 5 million\n• `2.5m` = 2.5 million",
                color=0xE74C3C
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        if parsed_amount < 10000000:
            embed = discord.Embed(
                title="❌ Minimum Amount Required",
                description=f"The minimum redemption amount is **10M gems**! 💎\n\nYou tried to redeem: **{format_gems(parsed_amount)} gems**",
                color=0xE74C3C
            )
            embed.set_footer(text="Play more mini-games to earn gems! 🎮")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        user_balance = get_balance(interaction.user.id)
        
        if user_balance < parsed_amount:
            embed = discord.Embed(
                title="💸 Insufficient Gems",
                description=f"You only have **{format_gems(user_balance)} gems** but tried to redeem **{format_gems(parsed_amount)} gems**! 😅",
                color=0xE74C3C
            )
            embed.set_footer(text="Play more mini-games to earn gems! 🎮")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        remove_gems(interaction.user.id, parsed_amount)
        
        embed = discord.Embed(
            title="✅ Redemption Successful!",
            color=0x00FF00
        )
        embed.add_field(
            name="💎 Gems Redeemed", 
            value=f"**{format_gems(parsed_amount)} Gems**", 
            inline=True
        )
        embed.add_field(
            name="💰 Remaining Balance", 
            value=f"**{format_gems(get_balance(interaction.user.id))} Gems**", 
            inline=True
        )
        embed.set_footer(text="Thank you for redeeming! 🎉")
        if interaction.user.avatar:
            embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.avatar.url)
        else:
            embed.set_author(name=interaction.user.display_name)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
        # Send notification to redeem channel
        redeem_channel = bot.get_channel(REDEEM_CHANNEL_ID)
        if redeem_channel:
            notification_embed = discord.Embed(
                title="💎 Gem Redemption",
                color=0xF1C40F
            )
            notification_embed.add_field(
                name="👤 User", 
                value=f"{interaction.user.mention}\n`{interaction.user.id}`", 
                inline=True
            )
            notification_embed.add_field(
                name="💰 Amount", 
                value=f"**{format_gems(parsed_amount)} Gems**", 
                inline=True
            )
            notification_embed.add_field(
                name="💳 Remaining Balance", 
                value=f"**{format_gems(get_balance(interaction.user.id))} Gems**", 
                inline=True
            )
            notification_embed.timestamp = discord.utils.utcnow()
            
            await redeem_channel.send(embed=notification_embed)
            
        # Also log to general log channel
        try:
            log_channel = bot.get_channel(LOG_CHANNEL_ID)
            if log_channel:
                log_embed = discord.Embed(
                    title="💎 Gem Redemption Log",
                    color=0xF39C12
                )
                log_embed.add_field(name="👤 User", value=f"{interaction.user.mention}\n`{interaction.user.id}`", inline=True)
                log_embed.add_field(name="💰 Redeemed", value=f"**{format_gems(parsed_amount)}** 💎", inline=True)
                log_embed.add_field(name="💳 Balance After", value=f"**{format_gems(get_balance(interaction.user.id))}** 💎", inline=True)
                log_embed.add_field(name="📍 Channel", value=f"<#{interaction.channel.id}>", inline=True)
                log_embed.timestamp = discord.utils.utcnow()
                await log_channel.send(embed=log_embed)
        except Exception as e:
            print(f"Error logging redemption: {e}")
    except Exception as e:
        print(f"Error in redeem command: {e}")
        await interaction.response.send_message("An error occurred during redemption.", ephemeral=True)

@bot.tree.command(name="forcestop", description="Force stop current mini-game (admin only)")
async def forcestop(interaction: discord.Interaction):
    try:
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("You need admin permissions to use this command.", ephemeral=True)
            return
        
        channel_id = interaction.channel.id
        if channel_id in active_games:
            del active_games[channel_id]
            
            # Also cancel and clean up any timeout tasks
            if channel_id in game_timeouts:
                timeout_task = game_timeouts[channel_id]
                timeout_task.cancel()
                del game_timeouts[channel_id]
            
            # Reset message counter when admin force stops
            reset_message_count()
            
            await interaction.response.send_message("✅ Current mini-game has been stopped.", ephemeral=True)
        else:
            await interaction.response.send_message("ℹ️ No active mini-game to stop.", ephemeral=True)
    except Exception as e:
        print(f"Error in forcestop command: {e}")
        await interaction.response.send_message("An error occurred.", ephemeral=True)

# Add /begin command
@bot.tree.command(name="begin", description="Start a specific mini-game (admin only)")
async def begin(interaction: discord.Interaction, game: str):
    try:
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("You need admin permissions to use this command.", ephemeral=True)
            return
        
        channel_id = interaction.channel.id
        
        # Check if game is already active
        if channel_id in active_games:
            await interaction.response.send_message("A mini-game is already active in this channel. Use `/forcestop` first.", ephemeral=True)
            return
        
        game_type = game.lower().strip()
        
        # Reset message counter
        global message_count
        message_count = 0
        
        if game_type in ["number", "num", "n"]:
            await interaction.response.send_message("Starting Number Challenge...", ephemeral=True)
            await start_number_game(interaction.channel)
        elif game_type in ["unscramble", "word", "scramble", "w", "u"]:
            await interaction.response.send_message("Starting Word Scramble...", ephemeral=True)
            await start_unscramble_game(interaction.channel)
        elif game_type in ["color", "colour", "c"]:
            await interaction.response.send_message("Starting Color Challenge...", ephemeral=True)
            await start_color_game(interaction.channel)
        else:
            await interaction.response.send_message("Invalid game type. Use: `number`, `unscramble`, or `color`", ephemeral=True)
            
    except Exception as e:
        print(f"Error in begin command: {e}")
        await interaction.response.send_message("An error occurred.", ephemeral=True)

@bot.tree.command(name="gift", description="Gift gems to another user")
async def gift(interaction: discord.Interaction, user: discord.Member, amount: str):
    try:
        # Check if command is used in allowed channels
        if interaction.channel.id not in GIFT_CHANNELS:
            await interaction.response.send_message("You **cannot** gift here! ❌", ephemeral=True)
            return
        
        # Check cooldown
        user_id = interaction.user.id
        current_time = time.time()
        
        if user_id in gift_cooldowns:
            time_left = gift_cooldowns[user_id] - current_time
            if time_left > 0:
                await interaction.response.send_message(f"Wait **{int(time_left)} seconds** to use this command. ❌", ephemeral=True)
                return
        
        # Check if user is trying to gift to themselves
        if user.id == interaction.user.id:
            await interaction.response.send_message("You cannot gift gems to yourself! ❌", ephemeral=True)
            return
        
        # Parse the amount
        parsed_amount = parse_amount(amount)
        
        if parsed_amount is None or parsed_amount <= 0:
            await interaction.response.send_message("❌ Invalid amount. Use formats like: `10m`, `1.5b`, `5000000`", ephemeral=True)
            return
        
        # Check if user has enough gems
        sender_balance = get_balance(interaction.user.id)
        
        if sender_balance < parsed_amount:
            await interaction.response.send_message(f"You only have **{format_gems(sender_balance)} gems** but tried to gift **{format_gems(parsed_amount)} gems**! ❌", ephemeral=True)
            return
        
        # Transfer gems
        remove_gems(interaction.user.id, parsed_amount)
        add_gems(user.id, parsed_amount)
        
        # Set cooldown
        gift_cooldowns[user_id] = current_time + 3  # 3 second cooldown
        
        # Send public gift message
        await interaction.response.send_message(f"{interaction.user.mention} gifted **{format_gems(parsed_amount)}** 💎 gems to {user.mention}")
        
        # Log the gift
        try:
            log_channel = bot.get_channel(LOG_CHANNEL_ID)
            if log_channel:
                log_embed = discord.Embed(
                    title="🎁 Gem Gift",
                    color=0xF1C40F
                )
                log_embed.add_field(name="👤 From", value=f"{interaction.user.mention}\n`{interaction.user.id}`", inline=True)
                log_embed.add_field(name="👤 To", value=f"{user.mention}\n`{user.id}`", inline=True)
                log_embed.add_field(name="💰 Amount", value=f"**{format_gems(parsed_amount)}** 💎", inline=True)
                log_embed.add_field(name="📍 Channel", value=f"<#{interaction.channel.id}>", inline=True)
                log_embed.add_field(name="💳 Sender Balance After", value=f"**{format_gems(get_balance(interaction.user.id))}** 💎", inline=True)
                log_embed.add_field(name="💳 Receiver Balance After", value=f"**{format_gems(get_balance(user.id))}** 💎", inline=True)
                log_embed.timestamp = discord.utils.utcnow()
                await log_channel.send(embed=log_embed)
        except Exception as e:
            print(f"Error logging gift: {e}")
            
    except Exception as e:
        print(f"Error in gift command: {e}")
        await interaction.response.send_message("❌ An error occurred while processing the gift.", ephemeral=True)

@bot.tree.command(name="balances", description="View all user balances (admin only)")
async def balances(interaction: discord.Interaction):
    try:
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ You need admin permissions to use this command.", ephemeral=True)
            return
        
        if not user_balances:
            await interaction.response.send_message("📊 No user balances found.", ephemeral=True)
            return
        
        # Sort balances from highest to lowest
        sorted_balances = sorted(user_balances.items(), key=lambda x: x[1], reverse=True)
        
        # Create pages of balances (Discord has character limits)
        balances_per_page = 15
        total_pages = (len(sorted_balances) + balances_per_page - 1) // balances_per_page
        
        # First page
        embed = discord.Embed(
            title="💰 All User Balances",
            color=0x5865F2
        )
        
        balance_list = []
        for i, (user_id, balance) in enumerate(sorted_balances[:balances_per_page]):
            try:
                user = await bot.fetch_user(int(user_id))
                username = user.display_name
            except:
                username = f"Unknown User ({user_id})"
            
            balance_list.append(f"`#{i+1}` **{username}** - {format_gems(balance)} 💎")
        
        if balance_list:
            embed.description = "\n".join(balance_list)
        else:
            embed.description = "No balances to display."
        
        embed.set_footer(text=f"Page 1 of {total_pages} • Total Users: {len(user_balances)}")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
    except Exception as e:
        print(f"Error in balances command: {e}")
        await interaction.response.send_message("❌ An error occurred while fetching balances.", ephemeral=True)

@bot.tree.command(name="addbal", description="Add gems to a user's balance (admin only)")
async def addbal(interaction: discord.Interaction, user: discord.Member, amount: str):
    try:
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ You need admin permissions to use this command.", ephemeral=True)
            return
        
        # Parse the amount
        parsed_amount = parse_amount(amount)
        
        if parsed_amount is None or parsed_amount <= 0:
            await interaction.response.send_message("❌ Invalid amount. Use formats like: `10m`, `1.5b`, `5000000`", ephemeral=True)
            return
        
        # Add gems to user
        old_balance = get_balance(user.id)
        add_gems(user.id, parsed_amount)
        new_balance = get_balance(user.id)
        
        # Success message
        embed = discord.Embed(
            title="✅ Gems Added",
            color=0x00FF00
        )
        embed.add_field(name="👤 User", value=f"{user.mention}\n`{user.id}`", inline=True)
        embed.add_field(name="➕ Added", value=f"**{format_gems(parsed_amount)}** 💎", inline=True)
        embed.add_field(name="💰 New Balance", value=f"**{format_gems(new_balance)}** 💎", inline=True)
        embed.set_footer(text=f"Added by {interaction.user.display_name}")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
        # Log to log channel
        try:
            log_channel = bot.get_channel(LOG_CHANNEL_ID)
            if log_channel:
                log_embed = discord.Embed(
                    title="💎 Gems Added (Admin)",
                    color=0x00FF00
                )
                log_embed.add_field(name="👤 Target User", value=f"{user.mention}\n`{user.id}`", inline=True)
                log_embed.add_field(name="👨‍💼 Admin", value=f"{interaction.user.mention}\n`{interaction.user.id}`", inline=True)
                log_embed.add_field(name="➕ Amount Added", value=f"**{format_gems(parsed_amount)}** 💎", inline=True)
                log_embed.add_field(name="📊 Old Balance", value=f"**{format_gems(old_balance)}** 💎", inline=True)
                log_embed.add_field(name="💰 New Balance", value=f"**{format_gems(new_balance)}** 💎", inline=True)
                log_embed.timestamp = discord.utils.utcnow()
                await log_channel.send(embed=log_embed)
        except Exception as e:
            print(f"Error logging balance addition: {e}")
            
    except Exception as e:
        print(f"Error in addbal command: {e}")
        await interaction.response.send_message("❌ An error occurred.", ephemeral=True)

@bot.tree.command(name="removebal", description="Remove gems from a user's balance (admin only)")
async def removebal(interaction: discord.Interaction, user: discord.Member, amount: str):
    try:
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ You need admin permissions to use this command.", ephemeral=True)
            return
        
        # Parse the amount
        parsed_amount = parse_amount(amount)
        
        if parsed_amount is None or parsed_amount <= 0:
            await interaction.response.send_message("❌ Invalid amount. Use formats like: `10m`, `1.5b`, `5000000`", ephemeral=True)
            return
        
        # Check current balance
        old_balance = get_balance(user.id)
        
        if old_balance < parsed_amount:
            embed = discord.Embed(
                title="❌ Insufficient Balance",
                description=f"{user.mention} only has **{format_gems(old_balance)} gems** but you tried to remove **{format_gems(parsed_amount)} gems**!",
                color=0xFF0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Remove gems from user
        success = remove_gems(user.id, parsed_amount)
        new_balance = get_balance(user.id)
        
        if success:
            # Success message
            embed = discord.Embed(
                title="✅ Gems Removed",
                color=0xFF6B6B
            )
            embed.add_field(name="👤 User", value=f"{user.mention}\n`{user.id}`", inline=True)
            embed.add_field(name="➖ Removed", value=f"**{format_gems(parsed_amount)}** 💎", inline=True)
            embed.add_field(name="💰 New Balance", value=f"**{format_gems(new_balance)}** 💎", inline=True)
            embed.set_footer(text=f"Removed by {interaction.user.display_name}")
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
            # Log to log channel
            try:
                log_channel = bot.get_channel(LOG_CHANNEL_ID)
                if log_channel:
                    log_embed = discord.Embed(
                        title="💎 Gems Removed (Admin)",
                        color=0xFF6B6B
                    )
                    log_embed.add_field(name="👤 Target User", value=f"{user.mention}\n`{user.id}`", inline=True)
                    log_embed.add_field(name="👨‍💼 Admin", value=f"{interaction.user.mention}\n`{interaction.user.id}`", inline=True)
                    log_embed.add_field(name="➖ Amount Removed", value=f"**{format_gems(parsed_amount)}** 💎", inline=True)
                    log_embed.add_field(name="📊 Old Balance", value=f"**{format_gems(old_balance)}** 💎", inline=True)
                    log_embed.add_field(name="💰 New Balance", value=f"**{format_gems(new_balance)}** 💎", inline=True)
                    log_embed.timestamp = discord.utils.utcnow()
                    await log_channel.send(embed=log_embed)
            except Exception as e:
                print(f"Error logging balance removal: {e}")
        else:
            await interaction.response.send_message("❌ Failed to remove gems.", ephemeral=True)
            
    except Exception as e:
        print(f"Error in removebal command: {e}")
        await interaction.response.send_message("❌ An error occurred.", ephemeral=True)

@bot.tree.command(name="messages", description="View message count progress (admin only)")
async def messages(interaction: discord.Interaction):
    try:
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ You need admin permissions to use this command.", ephemeral=True)
            return
        
        current_count = message_count
        messages_needed = 100 - current_count
        
        embed = discord.Embed(
            title="📊 Message Counter Status",
            color=0x3498DB
        )
        embed.add_field(
            name="📈 Current Messages", 
            value=f"**{current_count}**/100", 
            inline=True
        )
        embed.add_field(
            name="⏳ Messages Until Next Game", 
            value=f"**{messages_needed}** more", 
            inline=True
        )
        
        # Add progress bar
        progress = int((current_count / 100) * 20)  # 20-character progress bar
        progress_bar = "█" * progress + "░" * (20 - progress)
        embed.add_field(
            name="📊 Progress", 
            value=f"`{progress_bar}` {current_count}%", 
            inline=False
        )
        
        # Check if game is currently active
        if GAME_CHANNEL_ID in active_games:
            embed.add_field(
                name="🎮 Current Status", 
                value="**Game Active** - Counter paused", 
                inline=False
            )
        else:
            embed.add_field(
                name="🎮 Current Status", 
                value="**Counting messages** - Ready for next game", 
                inline=False
            )
        
        embed.set_footer(text="Counter resets to 0 when games start")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
    except Exception as e:
        print(f"Error in messages command: {e}")
        await interaction.response.send_message("❌ An error occurred while checking message count.", ephemeral=True)

@bot.tree.command(name="debug", description="Check active games (admin only)")
async def debug(interaction: discord.Interaction):
    try:
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("Admin only command.", ephemeral=True)
            return
        
        if active_games:
            game_info = []
            for channel_id, game_data in active_games.items():
                channel = bot.get_channel(channel_id)
                channel_name = channel.name if channel else "Unknown"
                game_info.append(f"#{channel_name}: {game_data['type']} (Answer: {game_data['answer']})")
            
            await interaction.response.send_message(f"**Active Games:**\n" + "\n".join(game_info), ephemeral=True)
        else:
            await interaction.response.send_message("No active games.", ephemeral=True)
    except Exception as e:
        print(f"Error in debug command: {e}")
        await interaction.response.send_message("An error occurred.", ephemeral=True)

@bot.event
async def on_command_error(ctx, error):
    print(f"Command error: {error}")

@bot.event
async def on_error(event, *args, **kwargs):
    print(f"Bot error in {event}: {args}")

# Health check server for UptimeRobot
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'Bot is running!')
    
    def log_message(self, format, *args):
        pass  # Disable logging

def start_health_server():
    port = int(os.environ.get('PORT', 8000))
    server = HTTPServer(('0.0.0.0', port), HealthHandler)
    server.serve_forever()

# Start health server in background
Thread(target=start_health_server, daemon=True).start()

# Run the bot - Get token from environment variable
if __name__ == "__main__":
    token = os.getenv('DISCORD_BOT_TOKEN')
    if token:
        bot.run(token)
    else:
        print("❌ DISCORD_BOT_TOKEN environment variable not found!")
        print("Please set it in your Railway dashboard.")
