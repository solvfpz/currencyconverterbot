import discord
import requests
import re
import os
import cv2

from urllib.parse import urlparse, parse_qs

# ---------------- CONFIG ----------------
TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    raise ValueError("DISCORD_TOKEN not set")

# ---------------- DISCORD ----------------
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

# ---------------- LTC PRICE ----------------
def get_ltc_price():
    url = "https://api.coingecko.com/api/v3/simple/price?ids=litecoin&vs_currencies=usd"
    return requests.get(url, timeout=10).json()["litecoin"]["usd"]

# ---------------- QR → UPI ----------------
def extract_upi_from_qr(path):
    img = cv2.imread(path)
    if img is None:
        return None

    detector = cv2.QRCodeDetector()
    data, _, _ = detector.detectAndDecode(img)

    if not data or "upi://" not in data.lower():
        return None

    parsed = urlparse(data)
    params = parse_qs(parsed.query)
    return params.get("pa", [None])[0]

async def download_image(url, path):
    r = requests.get(url, timeout=10)
    with open(path, "wb") as f:
        f.write(r.content)

# ---------------- EVENTS ----------------
@client.event
async def on_ready():
    print(f"✅ Logged in as {client.user}")

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if not isinstance(message.channel, discord.DMChannel):
        return

    content = message.content.lower().strip()

    # ============ ,nqr (REPLY MODE) ============
    if content == ",nqr" and message.reference:
        ref = message.reference.resolved
        path = "qr.png"

        # 1️⃣ Attachment
        if ref.attachments:
            await ref.attachments[0].save(path)

        # 2️⃣ Embed (FORWARDED IMAGE FIX)
        elif ref.embeds and ref.embeds[0].image:
            await download_image(ref.embeds[0].image.url, path)

        else:
            await message.channel.send("❌ Reply to a QR image")
            return

        upi = extract_upi_from_qr(path)
        await message.channel.send(upi if upi else "❌ UPI not found")
        return

    # ============ DIRECT IMAGE ============
    if message.attachments:
        path = "qr.png"
        await message.attachments[0].save(path)
        upi = extract_upi_from_qr(path)
        await message.channel.send(upi if upi else "❌ UPI not found")
        return

    if message.embeds and message.embeds[0].image:
        path = "qr.png"
        await download_image(message.embeds[0].image.url, path)
        upi = extract_upi_from_qr(path)
        await message.channel.send(upi if upi else "❌ UPI not found")
        return

    # ============ USD → LTC ============
    m = re.fullmatch(r"(\d+(\.\d+)?)(\$)?", content)
    if m:
        usd = float(m.group(1))
        price = get_ltc_price()
        await message.channel.send(f"{usd / price:.6f} LTC")
        return

    # ============ HELP ============
    await message.channel.send(
        "Reply `,nqr` to a QR image\n"
        "Or just send QR image\n"
        "`10$` → USD to LTC"
    )

# ---------------- RUN ----------------
client.run(TOKEN)
