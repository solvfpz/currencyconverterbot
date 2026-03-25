# Import libraries
import discord
from discord.ext import commands
import requests
import os
import re
import asyncio

# Intents for message content
intents = discord.Intents.default()
intents.message_content = True

# Bot setup
bot = commands.Bot(command_prefix=',', intents=intents, help_command=None)

# API URLs
BLOCKCYPHER_LTC = "https://api.blockcypher.com/v1/ltc/main"

# Event: Bot ready
@bot.event
async def on_ready():
    print(f'✅ {bot.user} is online!')
    print(f'📊 Bot is ready to check LTC balances and calculate math!')
    print(f'🔗 Connected to {len(bot.guilds)} server(s)')

# API URLs
BLOCKCYPHER_LTC = "https://api.blockcypher.com/v1/ltc/main"
BLOCKCHAIR_LTC = "https://api.blockchair.com/litecoin/dashboards/address/"

# CoinGecko API for LTC price
COINGECKO_LTC = "https://api.coingecko.com/api/v3/simple/price?ids=litecoin&vs_currencies=usd"

# Helper: Get LTC price
async def get_ltc_price():
    try:
        loop = asyncio.get_event_loop()
        resp = await loop.run_in_executor(None, lambda: requests.get(COINGECKO_LTC, timeout=10))
        resp.raise_for_status()
        return resp.json()['litecoin']['usd']
    except:
        return 70.0  # Fallback price

# Helper: Get LTC balance using multiple APIs (fallback system)
async def get_ltc_balance(address):
    # Try BlockCypher first
    try:
        url = f"{BLOCKCYPHER_LTC}/addrs/{address}/balance"
        print(f"📡 Trying BlockCypher: {url}")
        
        loop = asyncio.get_event_loop()
        resp = await loop.run_in_executor(None, lambda: requests.get(url, timeout=10))
        resp.raise_for_status()
        data = resp.json()
        
        print(f"✅ BlockCypher success: {data}")
        
        # Convert satoshis to LTC
        final_balance_ltc = data.get('final_balance', 0) / 100000000
        
        return {
            'final_balance': final_balance_ltc,
            'source': 'BlockCypher'
        }
    except Exception as e:
        print(f"⚠️ BlockCypher failed: {e}")
    
    # Fallback to Blockchair
    try:
        url = f"{BLOCKCHAIR_LTC}{address}"
        print(f"📡 Trying Blockchair: {url}")
        
        loop = asyncio.get_event_loop()
        resp = await loop.run_in_executor(None, lambda: requests.get(url, timeout=10))
        resp.raise_for_status()
        data = resp.json()
        
        print(f"✅ Blockchair success")
        
        # Blockchair returns balance directly in LTC
        balance = data['data'][address]['address']['balance'] / 100000000
        
        return {
            'final_balance': balance,
            'source': 'Blockchair'
        }
    except Exception as e:
        print(f"⚠️ Blockchair failed: {e}")
    
    return None

# Helper: Safe math evaluator
def safe_eval_math(expression):
    try:
        expression = expression.replace(' ', '')
        
        # Only allow numbers, operators, parentheses, decimal points
        if not re.match(r'^[\d+\-*/().]+$', expression):
            return None
        
        # Check if it has at least one operator
        if not any(op in expression for op in ['+', '-', '*', '/']):
            return None
        
        # Evaluate safely
        result = eval(expression, {"__builtins__": {}}, {})
        return result
    except:
        return None

# Event: Handle messages for auto-calculator
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    content = message.content.strip()
    
    # Auto math calculator
    math_pattern = r'^[\d+\-*/().\s]+$'
    if re.match(math_pattern, content) and any(op in content for op in ['+', '-', '*', '/']):
        result = safe_eval_math(content)
        if result is not None:
            # Format result
            if isinstance(result, float):
                if result.is_integer():
                    result = int(result)
                else:
                    result = round(result, 8)
            
            await message.reply(f"{result}", mention_author=False)
            return
    
    # Process commands
    await bot.process_commands(message)

# Command: ,bal <ltc_address>
@bot.command(name='bal')
async def balance(ctx, address: str = None):
    if not address:
        await ctx.send("❌ Please provide an LTC address!\nUsage: `,bal <ltc_address>`")
        return
    
    # Validate LTC address
    if not (address.startswith('L') or address.startswith('M') or address.startswith('ltc1') or address.startswith('3')):
        await ctx.send("❌ Invalid LTC address format!")
        return
    
    # Send loading message
    loading_msg = await ctx.send(f"🔍 Checking balance for `{address}`...")
    
    # Fetch balance and price of address
    balance_data = await get_ltc_balance(address)
    
    if balance_data is None:
        await loading_msg.edit(content="❌ Failed to fetch balance from all APIs. Please try again in a few seconds.")
        return
    
    # Get LTC price
    ltc_price = await get_ltc_price()
    usd_balance = balance_data['final_balance'] * ltc_price
    
    # Format response with line breaks
    response = (
        f"Your LTC address is: {address}\n"
        f"Your LTC balance is: {balance_data['final_balance']:.4f} LTC\n"
        f"Your USD balance is: ${usd_balance:.2f} USD"
    )
    
    await loading_msg.edit(content=response)

# Command: ,help
@bot.command()
async def help(ctx):
    help_text = """```
🤖 LTC Balance & Calculator Bot

Commands:
━━━━━━━━━━━━━━━━━━━━━━
,bal <address>  - Check LTC balance
,help           - Show this help message

📊 Auto Calculator:
━━━━━━━━━━━━━━━━━━━━━━
Just type any math expression!

Examples:
  10*11
  5+5/2
  (100-50)*2
  15.5*3+10
```"""
    await ctx.send(help_text)

# Run the bot
if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        print("❌ DISCORD_TOKEN not found!")
        exit(1)
    
    print("🚀 Starting Discord bot...")
    print("📌 Python version: 3.12.0")
    print("🔧 Environment: Render")
    
    try:
        bot.run(token)
    except Exception as e:
        print(f"❌ Bot failed to start: {e}")
