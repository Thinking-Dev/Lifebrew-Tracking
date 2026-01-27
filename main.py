import discord
from discord.ext import commands, tasks
from mcstatus import JavaServer
import json
import asyncio

# Load configuration
with open('config.json', 'r') as f:
    config = json.load(f)

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Track online players
online_players = set()

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    check_minecraft_server.start()

@tasks.loop(seconds=config['check_interval'])
async def check_minecraft_server():
    global online_players
    
    try:
        # Connect to Minecraft server
        server = JavaServer.lookup(config['minecraft_server'])
        status = await asyncio.to_thread(server.status)
        
        # Get current players
        current_players = set()
        if status.players.sample:
            current_players = {player.name for player in status.players.sample}
        
        # Find new logins
        new_logins = current_players - online_players
        
        # Find logoffs
        logoffs = online_players - current_players
        
        # Update tracked players
        online_players = current_players
        
        # Send notifications
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
        status = await asyncio.to_thread(server.status)
        
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
