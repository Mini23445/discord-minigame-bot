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
import socketserver

class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'Bot is running!')

def run_health_server():
    port = int(os.environ.get('PORT', 8000))
    with HTTPServer(('', port), HealthCheckHandler) as server:
        server.serve_forever()

# Start health check server in background
Thread(target=run_health_server, daemon=True).start()

# Bot configuration
GAME_CHANNEL_ID = 1410690717847785512  # Updated game channel
REDEEM_CHANNEL_ID = 1412142445327683687  # Updated redeem logs channel
LOG_CHANNEL_ID = 1412142500952408215     # New general logs channel
PING_ROLE_ID = 1412030131937083392

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

@bot.event
async def on_ready():
    print(f'{bot.user} has landed!')
    print(f'Connected to {len(bot.guilds)} servers')
    load_balances()
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
                        log_embed.add_field(name="💰 Gems Awarded", value="**20M** 💎", inline=True)
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
    global active_games, last_games
    
    try:
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
                    
                    embed.set_footer(text="Next Mini-Game in 15 messages")
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
        embed.add_field(name="💰 Reward", value="`20M` 💎", inline=True)
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

# Run the bot - Get token from environment variable
if __name__ == "__main__":
    token = os.getenv('DISCORD_BOT_TOKEN')
    if token:
        bot.run(token)
    else:
        print("❌ DISCORD_BOT_TOKEN environment variable not found!")
        print("Please set it in your Railway dashboard.")
