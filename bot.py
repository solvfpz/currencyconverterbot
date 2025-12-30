import discord
import requests
import re
import os
import qrcode
import cv2

from urllib.parse import urlparse, parse_qs

# ------------------- CONFIG -------------------
TOKEN = os.getenv("DISCORD_TOKEN")
ETHERSCAN_API_KEY = os.getenv("ETHERSCAN_API_KEY")

if not TOKEN:
    raise ValueError("DISCORD_TOKEN environment variable is not set!")
if not ETHERSCAN_API_KEY:
    raise ValueError("ETHERSCAN_API_KEY environment variable is not set!")

# ------------------- DISCORD SETUP -------------------
intents = discord.Intents.default()
intents.message_content = True
intents.dm_messages = True

client = discord.Client(intents=intents)

# ------------------- LTC PRICE -------------------
def get_ltc_price():
    r = requests.get(
        "https://api.coinbase.com/v2/prices/LTC-USD/spot",
        timeout=10
    )
    r.raise_for_status()
    return float(r.json()["data"]["amount"])

# ------------------- UPI → QR -------------------
def generate_upi_qr(upi_id, amount=None, note=None):
    upi_url = f"upi://pay?pa={upi_id}"
    if amount:
        upi_url += f"&am={amount}"
    if note:
        upi_url += f"&tn={note}"

    img = qrcode.make(upi_url)
    img.save("upi_qr.png")

# ------------------- QR → UPI (ONLY UPI ID) -------------------
def extract_upi_from_qr(image_path):
    img = cv2.imread(image_path)
    detector = cv2.QRCodeDetector()
    data, _, _ = detector.detectAndDecode(img)

    if not data or not data.startswith("upi://"):
        return None

    parsed = urlparse(data)
    params = parse_qs(parsed.query)

    return params.get("pa", [None])[0]

# ------------------- USDT BALANCE -------------------
chain_urls = {
    "ERC20": "https://api.etherscan.io/api",
    "BEP20": "https://api.bscscan.com/api",
    "POLY": "https://api.polygonscan.com/api"
}

token_contracts = {
    "ERC20": "0xdAC17F958D2ee523a2206206994597C13D831ec7",
    "BEP20": "0x55d398326f99059ff775485246999027b3197955",
    "POLY": "0xc2132D05D31c914a87C6611C10748AEb04B58e8F"
}

def get_usdt_balances(address):
    balances = {}

    for chain in chain_urls:
        url = (
            f"{chain_urls[chain]}"
            f"?module=account&action=tokenbalance"
            f"&contractaddress={token_contracts[chain]}"
            f"&address={address}"
            f"&tag=latest&apikey={ETHERSCAN_API_KEY}"
        )

        try:
            res = requests.get(url, timeout=10).json()
            balances[chain] = int(res["result"]) / 1_000_000 if res.get("status") == "1" else 0.0
        except:
            balances[chain] = 0.0

    return balances

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

    content = message.content.strip()

    # ---- QR IMAGE → ONLY UPI ID ----
    if message.attachments:
        att = message.attachments[0]
        if att.filename.lower().endswith(("png", "jpg", "jpeg")):
            path = "qr.png"
            await att.save(path)

            upi_id = extract_upi_from_qr(path)
            if not upi_id:
                await message.channel.send("❌ No valid UPI found")
                return

            await message.channel.send(upi_id)
            return

    # ---- UPI → QR ----
    if content.lower().startswith("upi "):
        parts = content.split(maxsplit=3)
        upi_id = parts[1]
        amount = None
        note = None

        if len(parts) >= 3:
            try:
                amount = float(parts[2])
            except:
                note = parts[2]

        if len(parts) == 4:
            note = parts[3]

        generate_upi_qr(upi_id, amount, note)
        await message.channel.send(file=discord.File("upi_qr.png"))
        return

    # ---- USD → LTC ----
    if re.fullmatch(r"\d+(\.\d+)?\$?", content):
        usd = float(content.replace("$", ""))
        price = get_ltc_price()
        await message.channel.send(f"{usd / price:.6f} LTC")
        return

    # ---- USDT BAL ----
    if content.lower().startswith("bal "):
        address = content.split(maxsplit=1)[1]
        bal = get_usdt_balances(address)
        await message.channel.send(
            f"ERC20: {bal['ERC20']}\n"
            f"BEP20: {bal['BEP20']}\n"
            f"POLY: {bal['POLY']}"
        )
        return

# ------------------- RUN -------------------
client.run(TOKEN)
