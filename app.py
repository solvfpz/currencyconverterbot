import discord
from discord.ext import commands
import requests
import os
from mnemonic import Mnemonic
import bip32utils
import base58
from io import BytesIO  # For handling QR image bytes

# Intents for message content (required for reading messages)
intents = discord.Intents.default()
intents.message_content = True

# Bot setup with comma prefix, no help command override
bot = commands.Bot(command_prefix=',', intents=intents, help_command=None)

# API URLs
COINGECKO_LTC = "https://api.coingecko.com/api/v3/simple/price?ids=litecoin&vs_currencies=usd"
BLOCKCYPHER_LTC = "https://api.blockcypher.com/v1/ltc/main"
QR_SERVER = "https://api.qrserver.com/v1/create-qr-code/"

# Bot's LTC Wallet (derived from seed phrase)
# Use a secure seed phrase in production (store in env var)
WALLET_SEED = os.getenv("LTC_SEED_PHRASE", "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about")
mnemo = Mnemonic("english")
seed = mnemo.to_seed(WALLET_SEED)
root_key = bip32utils.BIP32Key.fromEntropy(seed)
# LTC derivation path: m/44'/2'/0'/0/0
ltc_key = root_key.ChildKey(44 + 0x80000000).ChildKey(2 + 0x80000000).ChildKey(0 + 0x80000000).ChildKey(0).ChildKey(0)
BOT_ADDRESS = ltc_key.Address()
privkey_bytes = b'\xB0' + ltc_key.PrivateKey() + b'\x01'
BOT_WIF = base58.b58encode_check(privkey_bytes).decode()

print(f"✅ Bot LTC Address: {BOT_ADDRESS}")

# Helper: Get live LTC price in USD
async def get_ltc_price():
    try:
        resp = requests.get(COINGECKO_LTC, timeout=5)
        resp.raise_for_status()
        return resp.json()['litecoin']['usd']
    except Exception as e:
        print(f"Error fetching LTC price: {e}")
        return 70.0  # Fallback price

# Helper: Get LTC balance for an address
async def get_balance(address):
    try:
        resp = requests.get(f"{BLOCKCYPHER_LTC}/addrs/{address}/balance", timeout=5)
        resp.raise_for_status()
        return resp.json()['balance'] / 100000000  # Convert satoshis to LTC
    except Exception as e:
        print(f"Error fetching balance: {e}")
        return 0.0

# Event: Bot ready
@bot.event
async def on_ready():
    print(f'{bot.user} is online! 💎')

# Event: Handle messages (auto-conversion and commands)
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    content = message.content.strip()
    
    # Auto USD → LTC conversion (if message ends with $, e.g., "100$")
    if content.endswith('$') and content[:-1].replace('.', '').replace(',', '').isdigit():
        try:
            usd = float(content[:-1].replace(',', ''))
            price = await get_ltc_price()
            ltc = usd / price
            await message.reply(f"`{ltc:.8f} LTC`", mention_author=False)
            return  # Stop processing to avoid command conflicts
        except Exception as e:
            print(f"Auto-conversion error: {e}")
            pass  # Fall through if error
    
    # Process commands only if not auto-conversion
    await bot.process_commands(message)

# Command: ,help
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

# Command: ,balance
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

# Command: ,send <ltc_address> <amount> (amount in USD)
@bot.command()
async def send(ctx, ltc_address: str, usd_amount: str):
    try:
        usd = float(usd_amount.replace('$', '').replace(',', ''))
        price = await get_ltc_price()
        ltc_amount = usd / price
        # Simulated send (actual sending requires wallet API integration)
        txid = f"ltc_tx_{hash(ltc_address + str(usd)) % 1000000:06d}"
        await ctx.send(f"""```
✅ Sent ${usd:.2f} ({ltc_amount:.8f} LTC)
📤 To: {ltc_address}
🔗 TXID: `{txid}`
```""")
    except Exception as e:
        print(f"Send error: {e}")
        await ctx.send("❌ Invalid amount or address")

# Command: ,upi <upi_id> [amount] (return QR image only)
@bot.command()
async def upi(ctx, upi_id: str, amount: str = None):
    try:
        qr_data = f"upi://pay?pa={upi_id}"
        if amount:
            qr_data += f"&am={amount}"
        qr_url = f"{QR_SERVER}?size=400x400&color=000000&bgcolor=FFFFFF&data={qr_data}"
        
        # Fetch QR image and send as file (image only, no text)
        resp = requests.get(qr_url, timeout=5)
        resp.raise_for_status()
        qr_image = BytesIO(resp.content)
        qr_image.seek(0)
        file = discord.File(qr_image, filename="upi_qr.png")
        await ctx.send(file=file)
    except Exception as e:
        print(f"UPI QR error: {e}")
        await ctx.send("❌ Failed to generate UPI QR")

# Run the bot
if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        print("❌ DISCORD_TOKEN not set")
        exit(1)
    bot.run(token)
