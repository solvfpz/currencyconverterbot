import discord
import requests
import re
import os

# Get token from environment variable
TOKEN = os.getenv("DISCORD_TOKEN")
if TOKEN is None:
    raise ValueError("DISCORD_TOKEN environment variable is not set!")

# Discord intents
intents = discord.Intents.default()
intents.messages = True
intents.dm_messages = True

client = discord.Client(intents=intents)

# Get live LTC price from Binance
def get_ltc_price():
    url = "https://api.binance.com/api/v3/ticker/price?symbol=LTCUSDT"
    try:
        data = requests.get(url, timeout=5).json()
        return float(data["price"])
    except Exception as e:
        print(f"Error fetching LTC price: {e}")
        return None

# Bot ready event
@client.event
async def on_ready():
    print(f"Bot logged in as {client.user}")

# DM message handler
@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if isinstance(message.channel, discord.DMChannel):
        content = message.content.strip()
        # Accept numbers with or without $ sign
        match = re.fullmatch(r"(\d+(\.\d+)?)(\$)?", content)

        if match:
            usd = float(match.group(1))
            ltc_price = get_ltc_price()
            if ltc_price is None:
                await message.channel.send("⚠️ Could not fetch LTC price, try again later.")
                return

            ltc = usd / ltc_price
            await message.channel.send(
                f"**USD Amount:** ${usd:.2f}\n"
                f"**Equivalent LTC:** {ltc:.6f} LTC\n"
                f"**Live LTC Price:** ${ltc_price:.2f}"
            )
        else:
            await message.channel.send(
                "❌ Please send an amount like:\n`10`  `10$`  `300`  `300$`"
            )

# Run the bot
client.run(TOKEN)
