import discord
from discord.ext import commands
import requests
import json
import os
import asyncio

# APIs
QR_API = "https://api.qrserver.com/v1/create-qr-code/"
BLOCKCYPHER_LTC = "https://api.blockcypher.com/v1/ltc/main"
COINGECKO = "https://api.coingecko.com/api/v3/simple/price?ids=litecoin&vs_currencies=usd"

bot = commands.Bot(command_prefix=',', intents=discord.Intents.all(), help_command=None)

@bot.event
async def on_ready():
    print(f'{bot.user} LIVE! 💎 USD→LTC | UPI↔QR | LTC Balance')

# 💰 USD to LTC Converter
@bot.command(name='usd2ltc')
async def usd_to_ltc(ctx, usd_amount: float):
    try:
        resp = requests.get(COINGECKO)
        ltc_price = resp.json()['litecoin']['usd']
        ltc_amount = usd_amount / ltc_price
        embed = discord.Embed(title="💎 USD → LTC", color=0x00ff88)
        embed.add_field(name=f"${usd_amount:.2f}", value=f"`{ltc_amount:.8f} LTC`", inline=True)
        embed.add_field(name="Rate", value=f"1 LTC = ${ltc_price:.4f}", inline=True)
        await ctx.send(embed=embed)
    except:
        await ctx.send("❌ API error - try again")

# 📱 UPI to QR Code
@bot.command(name='upi')
async def upi_to_qr(ctx, *, upi_id):
    qr_data = f"upi://pay?pa={upi_id}"
    qr_url = f"{QR_API}?size=300x300&data={qr_data}"
    embed = discord.Embed(title="📱 UPI QR Code", description=f"`{upi_id}`", color=0x4169E1)
    embed.set_image(url=qr_url)
    await ctx.send(embed=embed)

# 🔄 QR to UPI (Extract UPI from QR data)
@bot.command(name='qr2upi')
async def qr_to_upi(ctx, *, qr_data):
    if "upi://" in qr_data.lower():
        upi_match = qr_data.split("pa=")[1].split("&")[0] if "pa=" in qr_data else "Invalid"
        embed = discord.Embed(title="🔍 QR → UPI", description=f"`{upi_match}`", color=0xFF69B4)
        qr_url = f"{QR_API}?size=200x200&data={qr_data}"
        embed.set_thumbnail(url=qr_url)
        await ctx.send(embed=embed)
    else:
        await ctx.send("❌ No UPI found in QR data")

# 💳 LTC Balance Checker
@bot.command(name='balance', aliases=['bal'])
async def ltc_balance(ctx, address: str):
    try:
        resp = requests.get(f"{BLOCKCYPHER_LTC}/addrs/{address}/balance")
        data = resp.json()
        if 'balance' in data:
            balance_sat = data['balance']
            balance_ltc = balance_sat / 100000000
            embed = discord.Embed(title="💰 LTC Balance", color=0xFFD700)
            embed.add_field(name=f"`{address[:12]}...`", value=f"{balance_ltc:.8f} LTC", inline=False)
            embed.add_field(name="Unconfirmed", value=f"{data.get('unconfirmed_balance', 0)/100000000:.8f} LTC", inline=True)
            await ctx.send(embed=embed)
        else:
            await ctx.send("❌ Invalid LTC address")
    except:
        await ctx.send("❌ Check failed - valid LTC address?")

# 🆕 Wallet Demo + QR
@bot.command(name='wallet')
async def create_wallet(ctx):
    # Demo data (use real HD wallet in production)
    demo_addr = "LhX8ASAB6X5kY6Z7kM9pQ2rT3uV4wE5xF6"
    demo_upi = "user@paytm"
    embed = discord.Embed(title="🆕 Wallet + UPI", color=0x00ff00)
    embed.add_field(name="LTC Address", value=f"`{demo_addr}`", inline=True)
    embed.add_field(name="UPI ID", value=f"`{demo_upi}`", inline=True)
    qr_url = f"{QR_API}?size=250x250&data=upi://pay?pa={demo_upi}"
    embed.set_image(url=qr_url)
    await ctx.send(embed=embed)

# 📋 Help Menu
@bot.command(name='help')
async def help_cmd(ctx):
    embed = discord.Embed(title="💎 Wallex Bot Commands", color=0x0099ff)
    embed.add_field(name="💰 Convert", value="`,usd2ltc 100` → $100 → LTC", inline=False)
    embed.add_field(name="📱 UPI QR", value="`,upi user@paytm`", inline=False)
    embed.add_field(name="🔍 QR→UPI", value="`,qr2upi upi://pay?pa=user`", inline=False)
    embed.add_field(name="💳 LTC Balance", value="`,balance LtcAddress`", inline=False)
    embed.add_field(name="🆕 Wallet", value="`,wallet`", inline=False)
    await ctx.send(embed=embed)

# 🛡️ Error handler
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("❌ Missing args! Type `,help`")
    elif isinstance(error, commands.BadArgument):
        await ctx.send("❌ Invalid amount/address! `,help`")

# Run bot
if __name__ == "__main__":
    bot.run(os.getenv('DISCORD_TOKEN'))
