import discord
import requests
import re
import os

# Discord token from environment variable
TOKEN = os.getenv("DISCORD_TOKEN")
if TOKEN is None:
    raise ValueError("DISCORD_TOKEN environment variable is not set!")

# Discord intents
intents = discord.Intents.default()
intents.messages = True
intents.dm_messages = True

client = discord.Client(intents=intents)

# Get real-time LTC price from CoinGecko
def get_ltc_price():
    url = "https://api.coingecko.com/api/v3/simple/price"
    params = {
        "ids": "litecoin",
        "vs_currencies": "usd"
    }

    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()

    data = response.json()
    print("CoinGecko response:", data)

    return float(data["litecoin"]["usd"])

@client.event
async def on_ready():
    print(f"Bot logged in as {client.user}")

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if isinstance(message.channel, discord.DMChannel):
        content = message.content.strip()

        # Accept: 10, 10$, 300, 300$
        match = re.fullmatch(r"(\d+(\.\d+)?)(\$)?", content)

        if not match:
            await message.channel.send(
                "❌ Send amount like:\n`10` `10$` `300` `300$`"
            )
            return

        usd = float(match.group(1))

        try:
            ltc_price = get_ltc_price()
            ltc_amount = usd / ltc_price

            await message.channel.send(
                f"USD Amount: ${usd:.2f}\n"
                f"LTC Amount: {ltc_amount:.6f} LTC\n"
                f"Live LTC Price: ${ltc_price:.2f}"
            )

        except Exception as e:
            print("API ERROR:", e)
            await message.channel.send(
                "⚠️ Unable to fetch live LTC price right now."
            )

client.run(TOKEN)
