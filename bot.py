import discord
import requests
import re
import os

TOKEN = os.getenv("DISCORD_TOKEN")
if TOKEN is None:
    raise ValueError("DISCORD_TOKEN environment variable is not set!")

intents = discord.Intents.default()
intents.messages = True
intents.dm_messages = True

client = discord.Client(intents=intents)

def get_ltc_price():
    url = "https://api.binance.com/api/v3/ticker/price?symbol=LTCUSDT"
    try:
        response = requests.get(url, timeout=10)
        print("HTTP status:", response.status_code)

        text = response.text
        print("RAW RESPONSE:", text)  # 🔥 THIS IS IMPORTANT

        data = response.json()
        print("JSON RESPONSE:", data)

        return float(data["price"])

    except Exception as e:
        print("API ERROR:", e)
        raise  # re-raise so you SEE the real error

@client.event
async def on_ready():
    print(f"Bot logged in as {client.user}")

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if isinstance(message.channel, discord.DMChannel):
        content = message.content.strip()
        match = re.fullmatch(r"(\d+(\.\d+)?)(\$)?", content)

        if not match:
            await message.channel.send(
                "❌ Send amount like:\n`10` `10$` `300`"
            )
            return

        usd = float(match.group(1))

        try:
            ltc_price = get_ltc_price()
            ltc = usd / ltc_price

            await message.channel.send(
                f"USD: ${usd:.2f}\n"
                f"LTC: {ltc:.6f}\n"
                f"LTC Price: ${ltc_price:.2f}"
            )

        except Exception:
            await message.channel.send(
                "⚠️ Failed to fetch live LTC price. Check logs."
            )

client.run(TOKEN)
