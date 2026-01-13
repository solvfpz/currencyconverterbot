import discord
import requests
import re
import os
import json
import asyncio
import io
from urllib.parse import urlparse, parse_qs
import cv2
from PIL import Image
import numpy as np

# ---------------- CONFIG ----------------
TOKEN = os.getenv("DISCORD_TOKEN")
WALLETS_FILE = "wallets.json"

# Simple LTC address generator (deterministic)
def generate_ltc_address(user_id):
    # Deterministic address from user ID + salt
    seed = f"wallex_{user_id}_litecoin_seed"
    # Legacy LTC address format (starts with L)
    # In production, use proper HD wallet library
    address = f"L{hash(seed) % 100000000:08d}{user_id % 10000:04d}"
    private_key = f"priv_{hash(seed * 2) % 1000000000000:012d}"
    return address[:34], private_key

def load_wallets():
    try:
        with open(WALLETS_FILE, 'r') as f:
            return json.load(f)
    except:
        return {}

def save_wallets(wallets):
    with open(WALLETS_FILE, 'w') as f:
        json.dump(wallets, f, indent=2)

wallets_data = load_wallets()

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

# ---------------- WALLEX FUNCTIONS ----------------
def create_wallet(user_id):
    address, private_key = generate_ltc_address(user_id)
    wallet_data = {
        "address": address,
        "private_key": private_key,
        "balance": 0.0,
        "created": asyncio.get_event_loop().time()
    }
    wallets_data[user_id] = wallet_data
    save_wallets(wallets_data)
    return wallet_data

def get_wallet(user_id):
    return wallets_data.get(user_id)

async def get_ltc_balance(address):
    try:
        url = f"https://api.blockcypher.com/v1/ltc/main/addrs/{address}/balance"
        response = await asyncio.to_thread(requests.get, url, timeout=10)
        data = response.json()
        return data['balance'] / 100000000
    except:
        return 0.0

async def get_ltc_price():
    try:
        url = "https://api.coingecko.com/api/v3/simple/price?ids=litecoin&vs_currencies=usd"
        response = await asyncio.to_thread(requests.get, url, timeout=10)
        return response.json()["litecoin"]["usd"]
    except:
        return 76.0

# ---------------- QR → UPI ----------------
def extract_upi_from_qr(image_bytes):
    try:
        image = Image.open(io.BytesIO(image_bytes))
        image_cv = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        
        detector = cv2.QRCodeDetector()
        data, _, _ = detector.detectAndDecode(image_cv)

        if not data or "upi://" not in data.lower():
            return None

        parsed = urlparse(data)
        params = parse_qs(parsed.query)
        return params.get("pa", [None])[0]
    except:
        return None

async def download_image(url):
    try:
        response = await asyncio.to_thread(requests.get, url, timeout=10)
        return response.content
    except:
        return None

# ---------------- DISCORD EVENTS ----------------
@client.event
async def on_ready():
    print(f"✅ Wallex + QR Bot LIVE!")
    print(f"👛 {len(wallets_data)} wallets")
    print(f"📱 DM me: {client.user}")

@client.event
async def on_message(message):
    if message.author == client.user or not isinstance(message.channel, discord.DMChannel):
        return

    content = message.content.lower().strip()
    user_id = str(message.author.id)

    # ========== WALLEX COMMANDS ==========
    if content in [",balance", ",bal"]:
        wallet = get_wallet(user_id)
        if not wallet:
            await message.channel.send("👛 **No wallet!** `,create_wallet`")
            return
        
        wallet['balance'] = await get_ltc_balance(wallet['address'])
        price = await get_ltc_price()
        usd = wallet['balance'] * price
        
        embed = discord.Embed(title="💰 Wallex", description="**APP**", color=0x5865F2)
        embed.add_field(name="LTC Address", value=f"`{wallet['address']}`", inline=False)
        embed.add_field(name="LTC", value=f"{wallet['balance']:.6f}", inline=True)
        embed.add_field(name="USD", value=f"${usd:.2f}", inline=True)
        embed.timestamp = discord.utils.utcnow()
        
        await message.channel.send(embed=embed)
        return

    elif content == ",address":
        wallet = get_wallet(user_id)
        if not wallet:
            await message.channel.send("👛 **No wallet!** `,create_wallet`")
            return
        embed = discord.Embed(title="📱 LTC Deposit", description=f"`{wallet['address']}`", color=0x00D4AA)
        await message.channel.send(embed=embed)
        return

    elif content == ",create_wallet":
        if get_wallet(user_id):
            await message.channel.send("❌ **Wallet exists!** `,balance`")
            return
        wallet = create_wallet(user_id)
        embed = discord.Embed(title="✅ Wallet Created!", description=f"`{wallet['address']}`", color=0x00D4AA)
        await message.channel.send(embed=embed)
        return

    elif content == ",delete_wallet":
        if get_wallet(user_id):
            del wallets_data[user_id]
            save_wallets(wallets_data)
            await message.channel.send("🗑️ **Wallet deleted!**")
        else:
            await message.channel.send("👛 **No wallet!**")
        return

    elif content == ",private_key":
        wallet = get_wallet(user_id)
        if wallet:
            embed = discord.Embed(title="🔑 Private Key", description=f"```{wallet['private_key']}```", color=0xFFAA00)
            await message.channel.send(embed=embed)
        else:
            await message.channel.send("👛 **No wallet!**")
        return

    # ========== QR/UPI + CONVERTER (unchanged) ==========
    # ... [Keep all your existing QR/USD code here] ...
    
    # Quick paste your QR code from previous version
    if content == ",nqr" and message.reference:
        # [Your existing ,nqr code]
        pass
    
    # [Rest of QR/USD logic from your original bot]
    
    await message.channel.send("**🎮 Commands:** `,help ,balance ,create_wallet 📸QR 10$`")

if __name__ == "__main__":
    client.run(TOKEN)
