import discord
import requests
import re
import os

# Discord bot token from environment variable
TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    raise ValueError("DISCORD_TOKEN environment variable is not set!")

# Discord intents
intents = discord.Intents.default()
intents.messages = True
intents.dm_messages = True

client = discord.Client(intents=intents)

# Get real-time LTC price from Coinbase (PUBLIC API)
def get_ltc_price():
    url = "https://api.coinbase.com/v2/prices/LTC-USD/spot"
    response = requests.get(url, timeout=10)
    response.raise_for_status()  # will throw error if API fails
    data = response.json()
    return float(data["data"]["amount"])

@client.event
async def on_ready():
    print(f"Bot logged in as {client.user}")

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    # Only respond in DMs
    if isinstance(message.channel, discord.DMChannel):
        content = message.content.strip()

        # Accept: 10, 10$, 10.5, 10.5$
        match = re.fullmatch(r"(\d+(\.\d+)?)(\$)?", content)

        if not match:
            await message.channel.send(
                "❌ Send amount like:\n`10`  `10$`  `300`  `300$`"
            )
            return

        usd = float(match.group(1))

        try:
            ltc_price = get_ltc_price()
            ltc = usd / ltc_price

            await message.channel.send(
                f"USD: ${usd:.2f}\n"
                f"LTC: {ltc:.6f}\n"
                f"LTC Price:** ${ltc_price:.2f}"
            )

        except Exception as e:
            print(f"API ERROR: {e}")
            await message.channel.send(
                "⚠️ Coinbase API error. Try again in a moment."
            )

# Run the bot
client.run(TOKEN)
