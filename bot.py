import discord
import requests
import re
import os
import qrcode
import cv2

from urllib.parse import urlparse, parse_qs

# ------------------- CONFIG -------------------
TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    raise ValueError("DISCORD_TOKEN environment variable is not set!")

# ------------------- DISCORD SETUP -------------------
intents = discord.Intents.default()
intents.message_content = True
intents.dm_messages = True
client = discord.Client(intents=intents)

# ------------------- LTC PRICE -------------------
def get_ltc_price():
    url = "https://api.coingecko.com/api/v3/simple/price?ids=litecoin&vs_currencies=usd"
    r = requests.get(url, timeout=10)
    r.raise_for_status()
    return float(r.json()["litecoin"]["usd"])

# ------------------- QR → UPI -------------------
def extract_upi_from_qr(image_path):
    img = cv2.imread(image_path)
    if img is None:
        return None

    detector = cv2.QRCodeDetector()
    data, _, _ = detector.detectAndDecode(img)

    if not data:
        return None

    if "upi://" not in data.lower():
        return None

    parsed = urlparse(data)
    params = parse_qs(parsed.query)
    return params.get("pa", [None])[0]

# ------------------- EVENTS -------------------
@client.event
async def on_ready():
    print(f"✅ Logged in as {client.user}")

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if not isinstance(message.channel, discord.DMChannel):
        return

    content = message.content.strip().lower()

    # ================= ,nqr (REPLY MODE) =================
    if content == ",nqr" and message.reference:
        ref = message.reference.resolved

        if ref and ref.attachments:
            attachment = ref.attachments[0]

            if attachment.filename.lower().endswith((".png", ".jpg", ".jpeg")):
                path = "qr.png"
                await attachment.save(path)

                upi = extract_upi_from_qr(path)
                if upi:
                    await message.channel.send(upi)
                else:
                    await message.channel.send("❌ UPI not found")
                return

        await message.channel.send("❌ Reply to a QR image")
        return

    # ================= IMAGE UPLOAD / FORWARD =================
    if message.attachments:
        attachment = message.attachments[0]

        if attachment.filename.lower().endswith((".png", ".jpg", ".jpeg")):
            path = "qr.png"
            await attachment.save(path)

            upi = extract_upi_from_qr(path)
            if upi:
                await message.channel.send(upi)
            else:
                await message.channel.send("❌ UPI not found")
            return

    # ================= USD → LTC =================
    match = re.fullmatch(r"(\d+(\.\d+)?)(\$)?", content)
    if match:
        usd = float(match.group(1))
        try:
            price = get_ltc_price()
            await message.channel.send(f"{usd / price:.6f} LTC")
        except Exception:
            await message.channel.send("❌ LTC price error")
        return

    # ================= HELP =================
    await message.channel.send(
        "Reply `,nqr` to a QR image → get UPI ID\n"
        "OR just send QR image\n"
        "`10$` → USD to LTC"
    )

# ------------------- RUN -------------------
client.run(TOKEN)
