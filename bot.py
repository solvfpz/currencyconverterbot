import discord
import requests
import re
import os
import qrcode

# ------------------- CONFIG -------------------
TOKEN = os.getenv("DISCORD_TOKEN")
ETHERSCAN_API_KEY = os.getenv("ETHERSCAN_API_KEY")  # Add this in Railway shared variables

if not TOKEN:
    raise ValueError("DISCORD_TOKEN environment variable is not set!")
if not ETHERSCAN_API_KEY:
    raise ValueError("ETHERSCAN_API_KEY environment variable is not set!")

# Discord intents
intents = discord.Intents.default()
intents.messages = True
intents.dm_messages = True
client = discord.Client(intents=intents)

# ------------------- STEP 1: LTC PRICE -------------------
def get_ltc_price():
    url = "https://api.coinbase.com/v2/prices/LTC-USD/spot"
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    data = response.json()
    return float(data["data"]["amount"])

# ------------------- STEP 2: UPI QR -------------------
def generate_upi_qr(upi_id, amount=None, note=None):
    upi_url = f"upi://pay?pa={upi_id}"
    if amount:
        upi_url += f"&am={amount}"
    if note:
        upi_url += f"&tn={note}"
    img = qrcode.make(upi_url)
    img.save("upi_qr.png")

# ------------------- STEP 3: USDT BALANCES -------------------
chain_urls = {
    "ERC20": "https://api.etherscan.io/api",
    "BEP20": "https://api.bscscan.com/api",
    "POLY": "https://api.polygonscan.com/api"
}

token_contracts = {
    "ERC20": "0xdAC17F958D2ee523a2206206994597C13D831ec7",  # USDT ETH
    "BEP20": "0x55d398326f99059ff775485246999027b3197955",   # USDT BSC
    "POLY": "0xc2132D05D31c914a87C6611C10748AEb04B58e8F"    # USDT POLY
}

def get_usdt_balances(address):
    balances = {}
    for chain in chain_urls:
        url = f"{chain_urls[chain]}?module=account&action=tokenbalance&contractaddress={token_contracts[chain]}&address={address}&tag=latest&apikey={ETHERSCAN_API_KEY}"
        try:
            res = requests.get(url, timeout=10).json()
            if res["status"] == "1":
                # USDT has 6 decimals
                balances[chain] = int(res["result"]) / 10**6
            else:
                balances[chain] = 0.0
        except Exception as e:
            print(f"Error fetching {chain} balance: {e}")
            balances[chain] = 0.0
    return balances

# ------------------- EVENTS -------------------
@client.event
async def on_ready():
    print(f"Bot logged in as {client.user}")

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if isinstance(message.channel, discord.DMChannel):
        content = message.content.strip()

        # ----------- UPI QR COMMAND -----------
        if content.lower().startswith("upi "):
            parts = content.split(maxsplit=3)
            if len(parts) < 2:
                await message.channel.send("❌ Usage:\n`upi upi_id amount(optional) note(optional)`")
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
            await message.channel.send(content="Here is your UPI QR code:", file=discord.File("upi_qr.png"))
            return

        # ----------- USD → LTC CONVERTER -----------
        match = re.fullmatch(r"(\d+(\.\d+)?)(\$)?", content)
        if match:
            usd = float(match.group(1))
            try:
                ltc_price = get_ltc_price()
                ltc = usd / ltc_price
                await message.channel.send(
                    f"USD: ${usd:.2f}\nLTC: {ltc:.6f}\nLTC Price: ${ltc_price:.2f}"
                )
            except Exception as e:
                print(f"API ERROR: {e}")
                await message.channel.send("⚠️ Coinbase API error. Try again later.")
            return

        # ----------- USDT BALANCE CHECK -----------
        if content.lower().startswith("bal "):
            parts = content.split(maxsplit=1)
            if len(parts) != 2:
                await message.channel.send("❌ Usage: `bal wallet_address`")
                return

            address = parts[1]
            try:
                balances = get_usdt_balances(address)
                msg = f"USDT Address: {address}\n"
                msg += f"USDT ERC20: {balances['ERC20']:.2f}$\n"
                msg += f"USDT BEP20: {balances['BEP20']:.2f}$\n"
                msg += f"USDT POLY: {balances['POLY']:.2f}$"
                await message.channel.send(msg)
            except Exception as e:
                print(f"Balance check error: {e}")
                await message.channel.send("⚠️ Could not fetch balances. Check the address or try again later.")
            return

        # ----------- INVALID MESSAGE -----------
        await message.channel.send(
            "❌ Invalid command.\n"
            "Send amount like `10` or `10$` for LTC conversion,\n"
            "Generate UPI QR: `upi blaze@upi 500 Payment`,\n"
            "Check USDT balance: `bal wallet_address`"
        )

# ------------------- RUN BOT -------------------
client.run(TOKEN)
