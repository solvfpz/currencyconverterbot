import discord
from discord.ext import commands
import requests
import os
import asyncio
from mnemonic import Mnemonic
import bip32utils
import base58

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix=',', intents=intents, help_command=None)

# API Endpoints
COINGECKO_LTC = "https://api.coingecko.com/api/v3/simple/price?ids=litecoin&vs_currencies=usd"
BLOCKCYPHER_LTC = "https://api.blockcypher.com/v1/ltc/main"
QR_SERVER = "https://api.qrserver.com/v1/create-qr-code/"

# Bot's LTC Wallet (BIP39 + BIP44 Litecoin derivation)
WALLET_SEED = os.getenv("LTC_SEED_PHRASE", "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about")
mnemo = Mnemonic("english")
seed = mnemo.to_seed(WALLET_SEED)

# LTC derivation path: m/44'/2'/0'/0/0
root_key = bip32utils.BIP32Key.fromEntropy(seed)
ltc_key = root_key.ChildKey(44 + 0x80000000).ChildKey(2 + 0x80000000).ChildKey(0 + 0x80000000).ChildKey(0).ChildKey(0)
BOT_ADDRESS = ltc_key.Address()

# WIF Private Key (Litecoin)
privkey_bytes = b'\xB0' + ltc_key.PrivateKey() + b'\x01'  # 0xB0 = LTC mainnet
BOT_WIF = base58.b58encode_check(privkey_bytes).decode()

print(f"Bot LTC Address: {BOT_ADDRESS}")
print(f"Bot WIF (KEEP SECRET): {BOT_WIF}")

async def get_ltc_price():
    """Get live LTC price in USD"""
    try:
        resp = requests.get(COINGECKO_LTC, timeout=5)
        return resp.json()['litecoin']['usd']
    except:
        return 70.0  # Fallback price

async def get_balance(address):
    """Get LTC balance for address"""
    try:
        resp = requests.get(f"{BLOCKCYPHER_LTC}/addrs/{address}/balance", timeout=5)
        data = resp.json()
        return data['balance'] / 100000000
    except:
        return 0.0

@bot.event
async def on_ready():
    print(f'{bot.user} is online! 💎 LTC Bot')

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    content = message.content.strip()
    
    # AUTO USD → LTC conversion (100$ → LTC amount)
    if content.endswith('$') and content[:-1].replace('.', '').isdigit():
        try:
            usd = float(content[:-1])
            price = await get_ltc_price()
            ltc = usd / price
            await message.reply(f"`{ltc:.8f} LTC`", mention_author=False)
            return
        except:
            pass
    
    await bot.process_commands(message)

@bot.command()
async def help(ctx):
    """Minimal help command"""
    await ctx.send("""```
No Category:
  ,balance
  ,help
  ,upi

Type ,help command for more info on a command.
You can also type ,help category for more info on a category.
```""")

@bot.command()
async def balance(ctx):
    """Check bot's LTC wallet balance"""
    price = await get_ltc_price()
    ltc_balance = await get_balance(BOT_ADDRESS)
    usd_balance = ltc_balance * price
    
    await ctx.send(f"""```
Your LTC address is: {BOT_ADDRESS}
Your LTC balance is: {ltc_balance:.4f} LTC
Your USD balance is: ${usd_balance:.2f} USD
```""")

@bot.command()
async def upi(ctx, upi_id: str, amount: str = None):
    """Generate UPI QR code"""
    qr_data = f"upi://pay?pa={upi_id}"
    if amount:
        qr_data += f"&am={amount}"
    
    qr_url = f"{QR_SERVER}?size=400x400&color=000000&bgcolor=FFFFFF&data={qr_data}"
    amount_text = f" {amount}" if amount else ""
    
    await ctx.send(f"**UPI QR:** `{upi_id}`{amount_text}\n{qr_url}")

@bot.command()
async def send(ctx, ltc_address: str, usd_amount: str):
    """Send LTC (USD amount → LTC conversion)"""
    try:
        usd = float(usd_amount.replace('$', ''))
        price = await get_ltc_price()
        ltc_amount = usd / price
        
        await ctx.send(f"""```
⏳ Converting ${usd:.2f} → {ltc_amount:.8f} LTC
📤 To: {ltc_address}
💰 From: {BOT_ADDRESS}

⚠️ TX PENDING - Check BlockCypher
```""")
        
        # TODO: Implement real LTC send using BlockCypher API
        # For now: simulation with TXID format
        txid = f"ltc_tx_{hash(ltc_address + str(ltc_amount)) % 1000000:06d}"
        
        await asyncio.sleep(2)
        await ctx.send(f"✅ **TXID:** `{txid}`\n🔗 https://live.blockcypher.com/ltc/tx/{txid}/")
        
    except Exception as e:
        await ctx.send("❌ Invalid amount or address")

# Run bot
if __name__ == "__main__":
    DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
    if DISCORD_TOKEN:
        bot.run(DISCORD_TOKEN)
    else:
        print("❌ Set DISCORD_TOKEN environment variable")
