import discord
import requests
import re

import os
TOKEN = os.getenv("DISCORD_TOKEN")


intents = discord.Intents.default()
intents.messages = True
intents.dm_messages = True

client = discord.Client(intents=intents)

def get_ltc_price():
    url = "https://api.binance.com/api/v3/ticker/price?symbol=LTCUSDT"
    data = requests.get(url).json()
    return float(data["price"])

@client.event
async def on_ready():
    print(f"Bot logged in as {client.user}")

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if isinstance(message.channel, discord.DMChannel):
        content = message.content.strip()

        # extract number (with or without $)
        match = re.fullmatch(r"(\d+(\.\d+)?)(\$)?", content)

        if match:
            usd = float(match.group(1))
            ltc_price = get_ltc_price()
            ltc = usd / ltc_price

            await message.channel.send(
                f"💵 {usd} USD ≈ **{ltc:.6f} LTC**\n"
                f"📈 LTC Price: ${ltc_price}"
            )
        else:
            await message.channel.send(
                "❌ Send amount like:\n`10`  `10$`  `300`  `300$`"
            )


client.run(TOKEN)

