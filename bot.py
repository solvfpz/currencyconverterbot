import discord
import requests
import re
import os
import qrcode

# ---------------- CONFIG ----------------
TOKEN = os.getenv("DISCORD_TOKEN")
ETHERSCAN_API_KEY = os.getenv("ETHERSCAN_API_KEY")

if not TOKEN:
    raise ValueError("DISCORD_TOKEN not set")

if not ETHERSCAN_API_KEY:
    raise ValueError("ETHERSCAN_API_KEY not set")

# ---------------- DISCORD SETUP ----------------
intents = discord.Intents.default()
intents.messages = True
intents.dm_messages = True
client = discord.Client(intents=intents)

# ---------------- UPI → QR ----------------
def generate_upi_qr(upi_id, amount=None, note=None):
    upi_url = f"upi://pay?pa={upi_id}"
    if amount:
        upi_url += f"&am={amount}"
    if note:
        upi_url += f"&tn={note}"
    img = qrcode.make(upi_url)
    img.save("upi_qr.png")

# ---------------- LTC PRICE ----------------
def get_ltc_price():
    url = "https://api.coinbase.com/v2/prices/LTC-USD/spot"
    r = requests.get(url, timeout=10)
    r.raise_for_status()
    return float(r.json()["data"]["amount"])

# ---------------- USDT CONTRACTS (FIXED) ----------------
USDT_CONTRACTS = {
    "ERC20": ("1",   "0xdAC17F958D2ee523a2206206994597C13D831ec7"),
    "BEP20": ("56",  "0x55d398326f99059ff775485246999027b3197955"),
    "POLY":  ("137", "0xc2132D05D31c914a87C6611C10748AEb04B58e8F")
}

# ---------------- USDT BALANCE (ETHERSCAN V2) ----------------
def get_usdt_balance(chainid, contract, address):
    url = "https://api.etherscan.io/v2/api"
    params = {
        "apikey": ETHERSCAN_API_KEY,
        "chainid": chainid,
        "module": "account",
        "action": "tokenbalance",
        "contractaddress": contract,
        "address": address,
        "tag": "latest"
    }
    r = requests.get(url, params=params, timeout=10)
    data = r.json()

    if data.get("status") != "1":
        return 0.0

    return int(data["result"]) / 1_000_000  # USDT = 6 decimals

# ---------------- LTC BALANCE ----------------
def get_ltc_balance(address):
    url = f"https://api.blockcypher.com/v1/ltc/main/addrs/{address}/balance"
    r = requests.get(url, timeout=10)
    data = r.json()
    return data["final_balance"] / 1e8

# ---------------- EVENTS ----------------
@client.event
async def on_ready():
    print(f"Bot logged in as {client.user}")

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if not isinstance(message.channel, discord.DMChannel):
        return

    content = message.content.strip()

    # ---------- UPI COMMAND ----------
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

    # ---------- BALANCE COMMAND ----------
    if content.lower().startswith("bal "):
        address = content.split()[1]

        usdt_balances = {}
        for name, (chainid, contract) in USDT_CONTRACTS.items():
            usdt_balances[name] = get_usdt_balance(chainid, contract, address)

        ltc_balance = get_ltc_balance(address)
        ltc_price = get_ltc_price()
        ltc_usd = ltc_balance * ltc_price

        reply = (
            f"**USDT Address:** `{address}`\n\n"
            f"USDT ERC20 : {usdt_balances['ERC20']:.2f} USD\n"
            f"USDT BEP20 : {usdt_balances['BEP20']:.2f} USD\n"
            f"USDT POLY  : {usdt_balances['POLY']:.2f} USD\n\n"
            f"**LTC Address:** `{address}`\n"
            f"LTC Balance : {ltc_balance:.6f} LTC\n"
            f"USD Value   : ${ltc_usd:.2f}"
        )

        await message.channel.send(reply)
        return

    # ---------- USD → LTC ----------
    match = re.fullmatch(r"(\d+(\.\d+)?)(\$)?", content)
    if match:
        usd = float(match.group(1))
        ltc_price = get_ltc_price()
        ltc = usd / ltc_price
        await message.channel.send(
            f"USD: ${usd:.2f}\n"
            f"LTC: {ltc:.6f}\n"
            f"LTC Price: ${ltc_price:.2f}"
        )
        return

    await message.channel.send(
        "❌ Commands:\n"
        "`10` → USD to LTC\n"
        "`upi upi_id amount note`\n"
        "`bal address`"
    )

# ---------------- RUN ----------------
client.run(TOKEN)
