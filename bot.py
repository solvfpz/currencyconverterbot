import discord
import requests
import re
import os
import qrcode
from urllib.parse import urlencode

# Discord bot token
TOKEN = os.getenv("DISCORD_TOKEN")
ETHERSCAN_KEY = os.getenv("ETHERSCAN_API_KEY")

if not TOKEN:
    raise ValueError("DISCORD_TOKEN environment variable is not set!")

if not ETHERSCAN_KEY:
    raise ValueError("ETHERSCAN_API_KEY environment variable is not set!")

# Discord intents
intents = discord.Intents.default()
intents.messages = True
intents.dm_messages = True

client = discord.Client(intents=intents)

# ---------- UPI → QR ----------
def generate_upi_qr(upi_id, amount=None, note=None):
    upi_url = f"upi://pay?pa={upi_id}"
    if amount:
        upi_url += f"&am={amount}"
    if note:
        upi_url += f"&tn={note}"

    img = qrcode.make(upi_url)
    img.save("upi_qr.png")

# ---------- LTC PRICE ----------
def get_ltc_price():
    url = "https://api.coinbase.com/v2/prices/LTC-USD/spot"
    r = requests.get(url, timeout=10)
    r.raise_for_status()
    return float(r.json()["data"]["amount"])

# ---------- LTC BALANCE ----------
def get_ltc_balance(address):
    url = f"https://api.blockcypher.com/v1/ltc/main/addrs/{address}/balance"
    r = requests.get(url, timeout=10)
    r.raise_for_status()
    return r.json()["final_balance"] / 1e8

# ---------- USDT (EVM) ----------
USDT_CONTRACTS = {
    "ERC20": "0xdAC17F958D2ee523a2206206994597C13D831ec7",
    "BEP20": "0x55d398326f99059fF775485246999027B3197955",
    "POLY":  "0x3813e82e6f7098b9583FC0F33a962D02018B6803"
}

CHAIN_IDS = {
    "ERC20": "1",
    "BEP20": "56",
    "POLY": "137"
}

def get_usdt_balance(address, network):
    params = {
        "chainid": CHAIN_IDS[network],
        "module": "account",
        "action": "tokenbalance",
        "contractaddress": USDT_CONTRACTS[network],
        "address": address,
        "tag": "latest",
        "apikey": ETHERSCAN_KEY
    }
    url = "https://api.etherscan.io/v2/api?" + urlencode(params)
    r = requests.get(url, timeout=10)
    r.raise_for_status()
    data = r.json()
    if data.get("status") != "1":
        return 0.0
    return int(data["result"]) / 1_000_000

# ---------- BOT EVENTS ----------
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

    # ---------- BALANCE CHECK ----------
    if content.lower().startswith("bal "):
        address = content.split(maxsplit=1)[1]

        try:
            if address.startswith("0x"):
                erc = get_usdt_balance(address, "ERC20")
                bep = get_usdt_balance(address, "BEP20")
                poly = get_usdt_balance(address, "POLY")

                await message.channel.send(
                    f"USDT Address: `{address}`\n\n"
                    f"USDT ERC20 : {erc:.2f} USD\n"
                    f"USDT BEP20 : {bep:.2f} USD\n"
                    f"USDT POLY  : {poly:.2f} USD"
                )
                return

            if address.startswith(("L", "M", "ltc1")):
                bal = get_ltc_balance(address)
                price = get_ltc_price()
                usd = bal * price

                await message.channel.send(
                    f"LTC Address: `{address}`\n\n"
                    f"LTC Balance: {bal:.6f} LTC\n"
                    f"USD Value: ${usd:.2f}"
                )
                return

            await message.channel.send("❌ Unsupported address format.")

        except Exception as e:
            print("BALANCE ERROR:", e)
            await message.channel.send("⚠️ Failed to fetch balance.")
        return

    # ---------- USD → LTC ----------
    match = re.fullmatch(r"(\d+(\.\d+)?)(\$)?", content)
    if match:
        usd = float(match.group(1))
        try:
            price = get_ltc_price()
            ltc = usd / price
            await message.channel.send(
                f"USD: ${usd:.2f}\n"
                f"LTC: {ltc:.6f}\n"
                f"LTC Price: ${price:.2f}"
            )
        except Exception as e:
            print("PRICE ERROR:", e)
            await message.channel.send("⚠️ Price fetch failed.")
        return

    await message.channel.send(
        "❌ Invalid input\n\n"
        "`10$` → USD to LTC\n"
        "`upi blaze@upi 500 note` → UPI QR\n"
        "`bal address` → Balance check"
    )

# Run bot
client.run(TOKEN)
