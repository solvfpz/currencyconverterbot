import discord
import requests
import re
import os
import qrcode

# ---------- BOT TOKEN ----------
TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    raise ValueError("DISCORD_TOKEN environment variable is not set!")

# ---------- DISCORD INTENTS ----------
intents = discord.Intents.default()
intents.messages = True
intents.dm_messages = True

client = discord.Client(intents=intents)

# ---------- UPI → QR FUNCTION ----------
def generate_upi_qr(upi_id, amount=None, note=None):
    upi_url = f"upi://pay?pa={upi_id}"

    if amount:
        upi_url += f"&am={amount}"
    if note:
        upi_url += f"&tn={note}"

    img = qrcode.make(upi_url)
    img.save("upi_qr.png")


# ---------- GET LTC PRICE ----------
def get_ltc_price():
    url = "https://api.coinbase.com/v2/prices/LTC-USD/spot"
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    data = response.json()
    return float(data["data"]["amount"])


# ---------- BOT READY ----------
@client.event
async def on_ready():
    print(f"✅ Bot logged in as {client.user}")


# ---------- MESSAGE HANDLER ----------
@client.event
async def on_message(message):
    if message.author == client.user:
        return

    # Only DM allowed
    if not isinstance(message.channel, discord.DMChannel):
        return

    content = message.content.strip()

    # ---------- UPI → QR COMMAND ----------
    if content.lower().startswith("upi "):
        parts = content.split(maxsplit=3)

        if len(parts) < 2:
            await message.channel.send(
                "❌ Usage:\n`upi upi_id amount(optional) note(optional)`"
            )
            return

        upi_id = parts[1]
        amount = None
        note = None

        if len(parts) >= 3:
            try:
                amount = float(parts[2])
            except ValueError:
                note = parts[2]

        if len(parts) == 4:
            note = parts[3]

        generate_upi_qr(upi_id, amount, note)

        await message.channel.send(
            content="✅ Here is your UPI QR code:",
            file=discord.File("upi_qr.png")
        )
        return

    # ---------- USD → LTC CONVERTER ----------
    match = re.fullmatch(r"(\d+(\.\d+)?)(\$)?", content)

    if not match:
        await message.channel.send(
            "❌ Invalid input\n\n"
            "**Examples:**\n"
            "`10`\n`10$`\n`300`\n\n"
            "**UPI QR:**\n"
            "`upi blaze@upi 500 Payment`"
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
            "⚠️ Price API error. Try again later."
        )


# ---------- RUN BOT ----------
client.run(TOKEN)
