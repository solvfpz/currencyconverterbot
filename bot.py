import discord
import requests
import re
import os
import qrcode

# ================== ENV ==================
TOKEN = os.getenv("DISCORD_TOKEN")
ETHERSCAN_API_KEY = os.getenv("ETHERSCAN_API_KEY")

if not TOKEN:
    raise ValueError("DISCORD_TOKEN not set")

if not ETHERSCAN_API_KEY:
    raise ValueError("ETHERSCAN_API_KEY not set")

# ================== DISCORD ==================
intents = discord.Intents.default()
intents.messages = True
intents.dm_messages = True

client = discord.Client(intents=intents)

# ================== USDT CONTRACTS (FIX) ==================
USDT_CONTRACTS = {
    "ERC20": ("0xdAC17F958D2ee523a2206206994597C13D831ec7", 1),
    "BEP20": ("0x55d398326f99059fF775485246999027B3197955", 56),
    "POLY":  ("0x3813e82e6f7098b9583FC0F33a962D02018B6803", 137),
}

# ================== UPI → QR ==================
def generate_upi_qr(upi_id, amount=None, note=None):
    upi_url = f"upi://pay?pa={upi_id}"
    if amount:
        upi_url += f"&am={amount}"
    if note:
        upi_url += f"&tn={note}"

    img = qrcode.make(upi_url)
    img.save("upi_qr.png")

# ================== LTC PRICE ==================
def get_ltc_price():
    url = "https://api.coinbase.com/v2/prices/LTC-USD/spot"
    r = requests.get(url, timeout=10)
    r.raise_for_status()
    return float(r.json()["data"]["amount"])

# ================== USDT BALANCE (FIXED) ==================
def get_usdt_balances(address):
    balances = {}

    for chain, (contract, chain_id) in USDT_CONTRACTS.items():
        url = "https://api.etherscan.io/v2/api"
        params = {
            "apikey": ETHERSCAN_API_KEY,
            "chainid": chain_id,
            "module": "account",
            "action": "tokenbalance",
            "contractaddress": contract,
            "address": address,
            "tag": "latest"
        }

        r = requests.get(url, params=params, timeout=10)
        data = r.json()

        if data.get("status") == "1":
            balances[chain] = int(data["result"]) / 1_000_000
        else:
            balances[chain] = 0.0

    return balances

# ================== EVENTS ==================
@client.event
async def on_ready():
    print(f"Logged in as {client.user}")

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if not isinstance(message.channel, discord.DMChannel):
        return

    content = message.content.strip()

    # ---------- BAL COMMAND ----------
    if content.lower().startswith("bal "):
        address = content.split(maxsplit=1)[1]

        usdt = get_usdt_balances(address)

        reply = (
            f"USDT Address: {address}\n\n"
            f"USDT ERC20 : {usdt['ERC20']:.2f} USD\n"
            f"USDT BEP20 : {usdt['BEP20']:.2f} USD\n"
            f"USDT POLY  : {usdt['POLY']:.2f} USD"
        )

        await message.channel.send(reply)
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
            content="Here is your UPI QR code:",
            file=discord.File("upi_qr.png")
        )
        return

    # ---------- USD → LTC ----------
    match = re.fullmatch(r"(\d+(\.\d+)?)(\$)?", content)

    if not match:
        await message.channel.send(
            "❌ Usage:\n"
            "`10` or `10$`\n"
            "`upi blaze@upi 500 Payment`\n"
            "`bal 0xYourAddress`"
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
        await message.channel.send("⚠️ API error. Try again later.")

# ================== RUN ==================
client.run(TOKEN)
