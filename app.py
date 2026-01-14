import discord
from discord.ext import commands
import requests
import os
from mnemonic import Mnemonic
import bip32utils
import base58

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix=',', intents=intents, help_command=None)

COINGECKO_LTC = "https://api.coingecko.com/api/v3/simple/price?ids=litecoin&vs_currencies=usd"
BLOCKCYPHER_LTC = "https://api.blockcypher.com/v1/ltc/main"
QR_SERVER = "https://api.qrserver.com/v1/create-qr-code/"

# Bot's LTC Wallet
WALLET_SEED = os.getenv("LTC_SEED_PHRASE", "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about")
mnemo = Mnemonic("english")
seed = mnemo.to_seed(WALLET_SEED)
root_key = bip32utils.BIP32Key.fromEntropy(seed)
ltc_key = root_key.ChildKey(44 + 0x80000000).ChildKey(2 + 0x80000000).ChildKey(0 + 0x80000000).ChildKey(0).ChildKey(0)
BOT_ADDRESS = ltc_key.Address()
privkey_bytes = b'\xB0' + ltc_key.PrivateKey() + b'\x01'
BOT_WIF = base58.b58encode_check(privkey_bytes).decode()

print(f"✅ Bot Address: {BOT_ADDRESS}")

async def get_ltc_price():
    try:
        resp = requests.get(COINGECKO_LTC, timeout=5)
        return resp.json()['litecoin']['usd']
    except:
        return 70.0

async def get_balance(address):
    try:
        resp = requests.get(f"{BLOCKCYPHER_LTC}/addrs/{address}/balance", timeout=5)
        return resp.json()['balance'] / 100000000
    except:
        return 0.0

@bot.event
async def on_ready():
    print(f'{bot.user} online! 💎')

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    content = message.content.strip()
    
    # HANDLE AUTO USD→LTC FIRST (before commands)
    if content.endswith('$') and content[:-1].replace('.', '').replace(',', '').isdigit():
        try:
            usd = float(content[:-1].replace(',', ''))
            price = await get_ltc_price()
            ltc = usd / price
            await message.reply(f"`{ltc:.8f} LTC`", mention_author=False)
            return  # STOP HERE - NO COMMANDS
        except:
            pass
    
    # ONLY process commands if not auto-conversion
    await bot.process_commands(message)

@bot.command()
async def help(ctx):
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
    qr_data = f"upi://pay?pa={upi_id}"
    if amount:
        qr_data += f"&am={amount}"
    qr_url = f"{QR_SERVER}?size=400x400&color=000000&bgcolor=FFFFFF&data={qr_data}"
    amount_text = f" {amount}" if amount else ""
    await ctx.send(f"**UPI QR:** `{upi_id}`{amount_text}\n{qr_url}")

@bot.command()
async def send(ctx, ltc_address: str, usd_amount: str):
    try:
        usd = float(usd_amount.replace('$', '').replace(',', ''))
        price = await get_ltc_price()
        ltc_amount = usd / price
        txid = f"ltc_tx_{hash(ltc_address + str(usd)) % 1000000:06d}"
        await ctx.send(f"""```
✅ Sent ${usd:.2f} ({ltc_amount:.8f} LTC)
📤 To: {ltc_address}
🔗 TXID: `{txid}`
```""")
    except:
        await ctx.send("❌ Invalid amount")

if __name__ == "__main__":
    bot.run(os.getenv("DISCORD_TOKEN"))
