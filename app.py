import discord
from discord.ext import commands
import requests
import os
import bip32utils
import hashlib
import base58
from mnemonic import Mnemonic

bot = commands.Bot(command_prefix=',', intents=discord.Intents.default(), help_command=None)

# APIs
BLOCKCYPHER_LTC = "https://api.blockcypher.com/v1/ltc/main"
COINGECKO = "https://api.coingecko.com/api/v3/simple/price?ids=litecoin&vs_currencies=usd"
QR_API = "https://api.qrserver.com/v1/create-qr-code/"

# Global wallet storage (production: use database)
wallets = {}

@bot.event
async def on_ready():
    print(f'{bot.user} LIVE! 💎')

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    
    # Auto USD→LTC: "100$" → "100$ = 1.234 LTC"
    content = message.content.strip()
    if content.endswith('$') and content[:-1].replace('.', '').isdigit():
        usd_amount = float(content[:-1])
        try:
            resp = requests.get(COINGECKO)
            ltc_price = resp.json()['litecoin']['usd']
            ltc_amount = usd_amount / ltc_price
            await message.reply(f"{content} = `{ltc_amount:.8f} LTC`")
        except:
            pass
    
    await bot.process_commands(message)

# 💳 LTC Balance
@bot.command(name='bal')
async def balance(ctx, address: str):
    try:
        resp = requests.get(f"{BLOCKCYPHER_LTC}/addrs/{address}/balance")
        data = resp.json()
        balance_ltc = data['balance'] / 100000000
        usd_price = requests.get(COINGECKO).json()['litecoin']['usd']
        balance_usd = balance_ltc * usd_price
        
        await ctx.send(f"""```
Your LTC address is: {address}
Your LTC balance is: {balance_ltc:.4f} LTC
Your USD balance is: ${balance_usd:.2f} USD
```""")
    except:
        await ctx.send("❌ Invalid address")

# 📱 UPI QR
@bot.command(name='upi')
async def upi_qr(ctx, upi: str, amount: str = None):
    qr_data = f"upi://pay?pa={upi}"
    if amount:
        qr_data += f"&am={amount}"
    
    # Exact QR style match
    qr_url = f"{QR_API}?size=400x400&color=000000&bgcolor=ffffff&data={qr_data}"
    await ctx.send(f"**UPI QR:** `{upi}` {f'${amount}' if amount else ''}\n{qr_url}")

# 🆕 Create LTC Wallet
@bot.command(name='wallet')
async def create_wallet(ctx):
    mnemo = Mnemonic("english")
    seed_phrase = mnemo.generate(strength=128)
    seed = mnemo.to_seed(seed_phrase)
    
    # LTC wallet derivation (m/44'/2'/0'/0/0)
    bip32_root = bip32utils.BIP32Key.fromEntropy(seed)
    bip32_child = bip32_root.ChildKey(44 + 0x80000000).ChildKey(2 + 0x80000000).ChildKey(0 + 0x80000000).ChildKey(0).ChildKey(0)
    
    privkey_wif = base58.b58encode_check(b'\x80' + bip32_child.PrivateKey() + b'\x01').decode()
    address = bip32_child.Address()
    
    wallets[str(ctx.author.id)] = {
        'seed': seed_phrase,
        'address': address,
        'privkey': privkey_wif
    }
    
    qr_url = f"{QR_API}?size=300x300&data={address}"
    await ctx.send(f"""```
🆕 Your LTC Wallet:
Address: {address}
Seed: {seed_phrase}
Private Key: {privkey_wif}

💰 Check: ,bal {address}
📱 QR: {qr_url}
```""")

# 📤 Send LTC (USD amount)
@bot.command(name='send')
async def send_ltc(ctx, to_address: str, usd_amount: str):
    if str(ctx.author.id) not in wallets:
        return await ctx.send("❌ Create wallet first: `,wallet`")
    
    try:
        usd_float = float(usd_amount.replace('$', ''))
        ltc_price = requests.get(COINGECKO).json()['litecoin']['usd']
        ltc_amount = usd_float / ltc_price
        
        wallet = wallets[str(ctx.author.id)]
        await ctx.send(f"""```
✅ Send Ready:
From: {wallet['address']}
To: {to_address}
USD: ${usd_float}
LTC: {ltc_amount:.8f}

⚠️ Production: Use BlockCypher/Tatum API
```""")
    except:
        await ctx.send("❌ Invalid USD amount")

# 📋 Minimal Help
@bot.command(name='help')
async def help_cmd(ctx):
    await ctx.send("""```
No Category:
  ,bal         
  ,help
  ,upi
Type ,help command for more info on a command.
You can also type ,help category for more info on a category.
```""")

bot.run(os.getenv('DISCORD_TOKEN'))
