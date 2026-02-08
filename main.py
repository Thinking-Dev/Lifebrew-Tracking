import discord
from discord.ext import commands, tasks
from mcstatus import JavaServer
import json
import asyncio
import os

# Load configuration from environment variables or config.json
def load_config():
    # Try to load from environment variables first (for Railway)
    if os.getenv('DISCORD_TOKEN'):
        return {
            'discord_token': os.getenv('DISCORD_TOKEN'),
            'channel_id': int(os.getenv('CHANNEL_ID')),
            'minecraft_server': os.getenv('MINECRAFT_SERVER'),
            'check_interval': int(os.getenv('CHECK_INTERVAL', '30'))
        }
    # Fall back to config.json for local development
    else:
        with open('config.json', 'r') as f:
            return json.load(f)

config = load_config()

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Track online players
online_players = set()
initial_check_done = False  # ✅ NEW: Flag to skip first check

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    check_minecraft_server.start()

@tasks.loop(seconds=config['check_interval'])
async def check_minecraft_server():
    global online_players, initial_check_done
    
    try:
        # Connect to Minecraft server
        server = JavaServer.lookup(config['minecraft_server'])
        status = await server.async_status()
        
        # Get current players
        current_players = set()
        if status.players.sample:
            current_players = {player.name for player in status.players.sample}
        
        # ✅ FIX: On first check, just initialize the player list without announcing
        if not initial_check_done:
            online_players = current_players
            initial_check_done = True
            print(f'Initial check complete. Currently online: {online_players}')
            return
        
        # Find new logins
        new_logins = current_players - online_players
        
        # Find logoffs
        logoffs = online_players - current_players
        
        # Update tracked players
        online_players = current_players
        
        # Send notifications only if there are actual changes
        channel = bot.get_channel(config['channel_id'])
        if channel:
            for player in new_logins:
                await channel.send(f'✅ **{player}** logged into the server!')
            
            for player in logoffs:
                await channel.send(f'❌ **{player}** logged off the server.')
                
    except Exception as e:
        print(f'Error checking server: {e}')

@check_minecraft_server.before_loop
async def before_check():
    await bot.wait_until_ready()

@bot.command(name='status')
async def server_status(ctx):
    """Check current server status"""
    try:
        server = JavaServer.lookup(config['minecraft_server'])
        status = await server.async_status()
        
        embed = discord.Embed(title="Minecraft Server Status", color=0x00ff00)
        embed.add_field(name="Players Online", value=f"{status.players.online}/{status.players.max}")
        embed.add_field(name="Version", value=status.version.name)
        embed.add_field(name="Latency", value=f"{status.latency:.2f}ms")
        
        if status.players.sample:
            players_list = '\n'.join([p.name for p in status.players.sample])
            embed.add_field(name="Online Players", value=players_list, inline=False)
        
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f'❌ Could not connect to server: {e}')

# Run the bot
bot.run(config['discord_token'])
