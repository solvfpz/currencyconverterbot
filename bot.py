import discord
import requests
import re
import os
import qrcode

# Discord bot token from environment variable
TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    raise ValueError("DISCORD_TOKEN environment variable is not set!")

# Discord intents
intents = discord.Intents.default()
intents.messages = True
intents.dm_messages = True

client = discord.Client(intents=intents)

# ---------- STEP 4: UPI → QR FUNCTION ----------
def generate_upi_qr(upi_id, amount=None, note=None):
    upi_url = f"upi://pay?pa={upi_id}"

    if amount:
        upi_url += f"&am={amount}"
    if note:
        upi_url += f"&tn={note}"

    img = qrcode.make(upi_url)
    img.save("upi_qr.png")


# Get real-time LTC price from Coinbase (PUBLIC API)
def get_ltc_price():
    url = "https://api.coinbase.com/v2/prices/LTC-USD/spot"
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    data = response.json()
    return float(data["data"]["amount"])


@client.event
async def on_ready():
    print(f"Bot logged in as {client.user}")


@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if isinstance(message.channel, discord.DMChannel):
        content = message.content.strip()

        parts = content.split()

        # ---------- SIMPLE UPI QR ----------
        # blaze@upi
        # blaze@upi 500
        if "@" in parts[0]:
            upi_id = parts[0]
            amount = None

            if len(parts) == 2:
                try:
                    amount = float(parts[1])
                except ValueError:
                    pass

            generate_upi_qr(upi_id, amount)

            await message.channel.send(
                content="Here is your UPI QR code:",
                file=discord.File("upi_qr.png")
            )
            return

        # ---------- USD → LTC ----------
        match = re.fullmatch(r"(\d+(\.\d+)?)(\$)?", content)

        if not match:
            await message.channel.send(
                "❌ Invalid input\n\n"
                "Examples:\n"
                "`10$` → USD to LTC\n"
                "`blaze@upi` → UPI QR\n"
                "`blaze@upi 500` → UPI QR with amount"
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

        except Exception as e:
            print(f"API ERROR: {e}")
            await message.channel.send(
                "⚠️ Coinbase API error. Try again later."
            )


# Run the bot
client.run(TOKEN)

