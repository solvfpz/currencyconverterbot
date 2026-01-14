import discord
from discord.ext import commands
import requests
import os
import hashlib
import base58
from mnemonic import Mnemonic
import bip32utils

bot = commands.Bot(command_prefix=',', intents=discord.Intents.default(), help_command=None)

# APIs - Litecoin ONLY
BLOCKCYPHER_LTC = "https://api.blockcypher.com/v1/ltc/main"
COINGECKO_LTC = "https://api.coingecko.com/api/v3/simple/price?ids=litecoin&vs_currencies=usd"
QR_API = "https://api.qrserver.com/v1/create-qr-code/"

wallets = {}

@bot.event
async def on_ready():
    print(f'{bot.user} LIVE! 💎 LTC Wallet')

@bot.event
async def on_message(message):
    if message.author.bot: return
    
    # Auto USD→LTC: "100$" 
    content = message.content.strip()
    if content.endswith('$') and content[:-1].replace('.', '').isdigit():
        try:
            usd = float(content[:-1])
            resp = requests.get(COINGECKO_LTC)
            ltc_price = resp.json()['litecoin']['usd']
            ltc_amount = usd / ltc_price
            await message.reply(f"{content} = `{ltc_amount:.8f} LTC`")
        except: pass
    
    await bot.process_commands(message)

@bot.command(name='bal')
async def balance(ctx, address: str):
    try:
        resp = requests.get(f"{BLOCKCYPHER_LTC}/addrs/{address}/balance")
        data = resp.json()
        balance_ltc = data['balance'] / 100000000
        usd_price = requests.get(COINGECKO_LTC).json()['litecoin']['usd']
        balance_usd = balance_ltc * usd_price
        
        await ctx.send(f"""```
Your LTC address is: {address}
Your LTC balance is: {balance_ltc:.4f} LTC
Your USD balance is: ${balance_usd:.2f} USD
```""")
    except Exception as e:
        await ctx.send("❌ Invalid LTC address")

@bot.command(name='upi')
async def upi_qr(ctx, upi: str, amount: str = None):
    qr_data = f"upi://pay?pa={upi}"
    if amount: qr_data += f"&am={amount}"
    
    qr_url = f"{QR_API}?size=400x400&color=000000&bgcolor=ffffff&data={qr_data}"
    await ctx.send(f"**UPI QR:** `{upi}` {f'{amount}' if amount else ''}\n{qr_url}")

@bot.command(name='wallet')
async def create_wallet(ctx):
    mnemo = Mnemonic("english")
    seed_phrase = mnemo.generate(strength=128)
    seed = mnemo.to_seed(seed_phrase)
    
    # Litecoin BIP44: m/44'/2'/0'/0/0
    root = bip32utils.BIP32Key.fromEntropy(seed)
    ltc_path = root.ChildKey(44 + 0x80000000).ChildKey(2 + 0x80000000).ChildKey(0 + 0x80000000).ChildKey(0).ChildKey(0)
    
    # WIF Private Key (Litecoin)
    privkey_bytes = b'\xB0' + ltc_path.PrivateKey() + b'\x01'  # 0xB0 = Litecoin mainnet
    privkey_wif = base58.b58encode_check(privkey_bytes).decode()
    address = ltc_path.Address()
    
    wallets[str(ctx.author.id)] = {
        'seed': seed_phrase,
        'address': address,
        'privkey': privkey_wif
    }
    
    qr_url = f"{QR_API}?size=300x300&data={address}"
    await ctx.send(f"""```
🆕 Litecoin Wallet:
Address: {address}
12-Word Seed: {seed_phrase}
WIF Private Key: {privkey_wif}

💰 Check: ,bal {address}
📱 Receive QR: {qr_url}

✅ Works in Exodus/TrustWallet!
```""")

@bot.command(name='send')
async def send_ltc(ctx, to_address: str, usd_amount: str):
    if str(ctx.author.id) not in wallets:
        return await ctx.send("❌ Create wallet: `,wallet`")
    
    try:
        usd = float(usd_amount.replace('$', ''))
        ltc_price = requests.get(COINGECKO_LTC).json()['litecoin']['usd']
        ltc_amount = usd / ltc_price
        
        wallet = wallets[str(ctx.author.id)]
        await ctx.send(f"""```
✅ LTC Send Ready:
From: {wallet['address']}
To: {to_address}
USD Amount: ${usd:.2f}
LTC Amount: {ltc_amount:.8f}

⚠️ Use Exodus/TrustWallet to send
```""")
    except:
        await ctx.send("❌ Invalid USD amount (use: 20$)")

@bot.command(name='help')
async def help_cmd(ctx):
    await ctx.send("""```
No Category:
  ,bal         
  ,help
  ,upi
Type ,help command for more info on a command.
```""")

if __name__ == "__main__":
    bot.run(os.getenv('DISCORD_TOKEN'))
