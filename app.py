import discord
from discord.ext import commands
import requests
import os
from mnemonic import Mnemonic
import bip32utils
import base58

bot = commands.Bot(command_prefix=',', intents=discord.Intents.default(), help_command=None)

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
            resp = requests.get(COINGECKO_LTC, timeout=5)
            ltc_price = resp.json()['litecoin']['usd']
            ltc_amount = usd / ltc_price
            await message.reply(f"{content} = `{ltc_amount:.8f} LTC`", mention_author=False)
        except: pass
    
    await bot.process_commands(message)

@bot.command(name='bal')
async def balance(ctx, address: str):
    try:
        resp = requests.get(f"{BLOCKCYPHER_LTC}/addrs/{address}/balance", timeout=5)
        data = resp.json()
        balance_ltc = data['balance'] / 100000000
        usd_price = requests.get(COINGECKO_LTC, timeout=5).json()['litecoin']['usd']
        balance_usd = balance_ltc * usd_price
        
        await ctx.send(f"""```
Your LTC address is: {address}
Your LTC balance is: {balance_ltc:.4f} LTC
Your USD balance is: ${balance_usd:.2f} USD
```""")
    except:
        pass  # Silent fail ✅

@bot.command(name='upi')
async def upi_qr(ctx, upi: str, amount: str = None):
    qr_data = f"upi://pay?pa={upi}"
    if amount: qr_data += f"&am={amount}"
    
    qr_url = f"{QR_API}?size=400x400&color=000000&bgcolor=ffffff&data={qr_data}"
    amount_text = f" {amount}" if amount else ""
    await ctx.send(f"**UPI QR:** `{upi}`{amount_text}\n{qr_url}")

@bot.command(name='wallet')
async def create_wallet(ctx):
    mnemo = Mnemonic("english")
    seed_phrase = mnemo.generate(strength=128)
    seed = mnemo.to_seed(seed_phrase)
    
    root = bip32utils.BIP32Key.fromEntropy(seed)
    ltc_path = root.ChildKey(44 + 0x80000000).ChildKey(2 + 0x80000000).ChildKey(0 + 0x80000000).ChildKey(0).ChildKey(0)
    
    privkey_bytes = b'\xB0' + ltc_path.PrivateKey() + b'\x01'
    privkey_wif = base58.b58encode_check(privkey_bytes).decode()
    address = ltc_path.Address()
    
    wallets[str(ctx.author.id)] = {'seed': seed_phrase, 'address': address, 'privkey': privkey_wif}
    
    qr_url = f"{QR_API}?size=300x300&data={address}"
    await ctx.send(f"""```
🆕 Litecoin Wallet:
Address: {address}
12-Word Seed: {seed_phrase}
WIF Private Key: {privkey_wif}

💰 Check: ,bal {address}
📱 Receive QR: {qr_url}
```""")

@bot.command(name='help')
async def help_cmd(ctx):
    await ctx.send("""```
💎 Wallex Bot Commands
💰 Convert: ,usd2ltc 100 (or just "100$")
📱 UPI QR: ,upi user@paytm [amount]
🔍 LTC Balance: ,bal LtcAddress  
🆕 Wallet: ,wallet
```""")

if __name__ == "__main__":
    bot.run(os.getenv('DISCORD_TOKEN'))
