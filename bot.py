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
intents.messages = True
intents.dm_messages = True
client = discord.Client(intents=intents)

# ------------------- STEP 1: LTC PRICE -------------------
def get_ltc_price():
    url = "https://api.coinbase.com/v2/prices/LTC-USD/spot"
    r = requests.get(url, timeout=10)
    r.raise_for_status()
    return float(r.json()["data"]["amount"])

# ------------------- STEP 2: UPI → QR -------------------
def generate_upi_qr(upi_id, amount=None, note=None):
    upi_url = f"upi://pay?pa={upi_id}"
    if amount:
        upi_url += f"&am={amount}"
    if note:
        upi_url += f"&tn={note}"

    img = qrcode.make(upi_url)
    img.save("upi_qr.png")

# ------------------- STEP 3: QR → UPI (OpenCV) -------------------
def extract_upi_from_qr(image_path):
    img = cv2.imread(image_path)
    detector = cv2.QRCodeDetector()
    data, _, _ = detector.detectAndDecode(img)

    if not data or not data.startswith("upi://"):
        return None

    parsed = urlparse(data)
    params = parse_qs(parsed.query)

    return {
        "upi_id": params.get("pa", [None])[0],
    }

# ------------------- STEP 4: USDT BALANCES -------------------
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
            if res.get("status") == "1":
                balances[chain] = int(res["result"]) / 10**6
            else:
                balances[chain] = 0.0
        except Exception as e:
            print(f"{chain} error:", e)
            balances[chain] = 0.0

    return balances

# ------------------- EVENTS -------------------
@client.event
async def on_ready():
    print(f"✅ Bot logged in as {client.user}")

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if not isinstance(message.channel, discord.DMChannel):
        return

    content = message.content.strip()

    # ---------- QR IMAGE → UPI ----------
    if message.attachments:
        attachment = message.attachments[0]
        if attachment.filename.lower().endswith((".png", ".jpg", ".jpeg")):
            path = "qr_upload.png"
            await attachment.save(path)

            data = extract_upi_from_qr(path)
            if not data or not data["upi_id"]:
                await message.channel.send("❌ No valid UPI QR detected.")
                return

            await message.channel.send(data["upi_id"])
            
            return

    # ---------- UPI → QR ----------
    if content.lower().startswith("upi "):
        parts = content.split(maxsplit=3)

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
            content="📲 Your UPI QR:",
            file=discord.File("upi_qr.png")
        )
        return

    # ---------- USD → LTC ----------
    match = re.fullmatch(r"(\d+(\.\d+)?)(\$)?", content)
    if match:
        usd = float(match.group(1))
        try:
            price = get_ltc_price()
            await message.channel.send(
                f"USD: ${usd:.2f}\n"
                f"LTC: {usd / price:.6f}\n"
                f"LTC Price: ${price:.2f}"
            )
        except Exception:
            await message.channel.send("⚠️ Price fetch failed.")
        return

    # ---------- USDT BALANCE ----------
    if content.lower().startswith("bal "):
        address = content.split(maxsplit=1)[1]
        balances = get_usdt_balances(address)

        await message.channel.send(
            f"USDT Address: {address}\n"
            f"USDT ERC20 : {balances['ERC20']:.2f} USD\n"
            f"USDT BEP20 : {balances['BEP20']:.2f} USD\n"
            f"USDT POLY  : {balances['POLY']:.2f} USD"
        )
        return

    # ---------- HELP ----------
    await message.channel.send(
        "❌ Invalid command\n\n"
        "`10$` → USD to LTC\n"
        "`upi upi@id 500 note`\n"
        "`bal wallet_address`\n"
        "Or send a **UPI QR image**"
    )

# ------------------- RUN -------------------
client.run(TOKEN)

