import discord
import requests
import re
import os
import cv2
import json
import asyncio
from urllib.parse import urlparse, parse_qs
from PIL import Image
import numpy as np
import bip39
from bitcoinlib.wallets import Wallet
from bitcoinlib.networks import Network

# ---------------- CONFIG ----------------
TOKEN = os.getenv("DISCORD_TOKEN")
WALLETS_FILE = "wallets.json"
LTC_NETWORK = Network('litecoin')

# Load/Save wallets
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
    wallet_name = f"wallex_{user_id}"
    wallet = Wallet.create(wallet_name, network=LTC_NETWORK, witness_type='segwit')
    address = wallet.get_key().address
    private_key = wallet.get_key().wif
    
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
        return data['balance'] / 100000000  # Satoshis to LTC
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
    image = Image.open(io.BytesIO(image_bytes))
    image_cv = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
    
    detector = cv2.QRCodeDetector()
    data, _, _ = detector.detectAndDecode(image_cv)

    if not data or "upi://" not in data.lower():
        return None

    parsed = urlparse(data)
    params = parse_qs(parsed.query)
    return params.get("pa", [None])[0]

async def download_image(url):
    try:
        response = await asyncio.to_thread(requests.get, url, timeout=10)
        return response.content
    except:
        return None

# ---------------- DISCORD EVENTS ----------------
@client.event
async def on_ready():
    print(f"✅ Wallex + QR Bot ready!")
    print(f"👛 {len(wallets_data)} wallets loaded")
    print(f"📱 DM: {client.user}")

@client.event
async def on_message(message):
    if message.author == client.user or not isinstance(message.channel, discord.DMChannel):
        return

    content = message.content.lower().strip()
    user_id = str(message.author.id)

    # ========== WALLEX COMMANDS ==========
    if content == ",balance" or content == ",bal":
        wallet = get_wallet(user_id)
        if not wallet:
            await message.channel.send("👛 **No wallet!** Use `,create_wallet`")
            return
        
        wallet['balance'] = await get_ltc_balance(wallet['address'])
        price = await get_ltc_price()
        usd = wallet['balance'] * price
        
        embed = discord.Embed(title="💰 Wallex", description="**APP**", color=0x5865F2)
        embed.add_field(name="LTC Address", value=f"`{wallet['address'][:20]}...`", inline=False)
        embed.add_field(name="LTC Balance", value=f"{wallet['balance']:.6f} LTC", inline=True)
        embed.add_field(name="USD Balance", value=f"${usd:.2f}", inline=True)
        embed.timestamp = discord.utils.utcnow()
        
        await message.channel.send(embed=embed)
        return

    elif content == ",address":
        wallet = get_wallet(user_id)
        if not wallet:
            await message.channel.send("👛 **No wallet!** Use `,create_wallet`")
            return
        
        embed = discord.Embed(title="📱 Your LTC Address", description=f"`{wallet['address']}`", color=0x00D4AA)
        await message.channel.send(embed=embed)
        return

    elif content == ",create_wallet":
        if get_wallet(user_id):
            await message.channel.send("❌ **Wallet exists!** Use `,balance`")
            return
        
        wallet = create_wallet(user_id)
        embed = discord.Embed(title="✅ Wallet Created!", description=f"**Address:** `{wallet['address']}`", color=0x00D4AA)
        await message.channel.send(embed=embed)
        return

    elif content == ",delete_wallet":
        if not get_wallet(user_id):
            await message.channel.send("👛 **No wallet found!**")
            return
        
        del wallets_data[user_id]
        save_wallets(wallets_data)
        await message.channel.send("🗑️ **Wallet deleted!**")
        return

    elif content == ",private_key":
        wallet = get_wallet(user_id)
        if not wallet:
            await message.channel.send("👛 **No wallet!**")
            return
        
        embed = discord.Embed(title="🔑 Private Key", description=f"```{wallet['private_key']}```", color=0xFFAA00)
        embed.set_footer(text="⚠️ NEVER SHARE!")
        await message.channel.send(embed=embed)
        return

    elif content == ",help":
        embed = discord.Embed(title="📋 Wallex Commands", color=0x5865F2)
        embed.add_field(name="💰 Wallet", value="`,balance, ,address, ,create_wallet, ,delete_wallet, ,private_key`", inline=False)
        embed.add_field(name="📱 QR/UPI", value="`Send QR image` or `,nqr` (reply)", inline=False)
        embed.add_field(name="💵 Convert", value="`10$` → LTC amount", inline=False)
        await message.channel.send(embed=embed)
        return

    # ========== QR/UPI SCANNER ==========
    if content == ",nqr" and message.reference:
        ref = await message.channel.fetch_message(message.reference.message_id)
        image_bytes = None

        if ref.attachments:
            image_bytes = await ref.attachments[0].read()
        elif ref.embeds and ref.embeds[0].image:
            image_bytes = await download_image(ref.embeds[0].image.url)

        if image_bytes:
            upi = extract_upi_from_qr(image_bytes)
            await message.channel.send(f"**UPI:** `{upi or '❌ Not found'}`")
        else:
            await message.channel.send("❌ **Reply to QR image only**")
        return

    # Direct QR image
    image_bytes = None
    if message.attachments:
        att = message.attachments[0]
        if 'image' in att.content_type:
            image_bytes = await att.read()
    elif message.embeds and message.embeds[0].image:
        image_bytes = await download_image(message.embeds[0].image.url)

    if image_bytes:
        upi = extract_upi_from_qr(image_bytes)
        await message.channel.send(f"**UPI:** `{upi or '❌ Not found'}`")
        return

    # ========== USD → LTC ==========
    m = re.fullmatch(r"(\d+(\.\d+)?)(\$)?", content)
    if m:
        usd = float(m.group(1))
        price = await get_ltc_price()
        ltc = usd / price
        await message.channel.send(f"`{ltc:.6f}` **LTC**")
        return

    # Help
    await message.channel.send(
        "**🎮 Wallex + QR Bot**\n"
        "`📸 Send QR` → UPI ID\n"
        "`,nqr` **reply** → UPI ID\n"
        "`💰 ,balance` → LTC wallet\n"
        "`10$` → USD to LTC\n"
        "`? ,help` → All commands"
    )

client.run(TOKEN)
