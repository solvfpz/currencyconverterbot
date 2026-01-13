import discord
import requests
import json
import os
from discord.ext import commands
import asyncio

# Wallex API
WALLEX_API = "https://api.wallex.ir/api/v1/market/udf/history"
# QR Server API (FREE - NO LOCAL CV2!)
QR_API = "https://api.qrserver.com/v1/create-qr-code/"

bot = commands.Bot(command_prefix=',', intents=discord.Intents.all())
@bot.event
async def on_ready():
    print(f'{bot.user} LIVE! 💎')

# QR via FREE API (no cv2!)
async def generate_qr(data):
    qr_url = f"{QR_API}?size=200x200&data={data}"
    return qr_url

@bot.command()
async def balance(ctx, address: str):
    # LTC balance via BlockCypher
    try:
        resp = requests.get(f"https://api.blockcypher.com/v1/ltc/main/addrs/{address}/balance")
        data = resp.json()
        balance = data['balance'] / 100000000  # satoshis to LTC
        await ctx.send(f"💰 **{address[:10]}...**: `{balance:.8f} LTC`")
    except:
        await ctx.send("❌ Invalid address")

@bot.command()
async def qr(ctx, *, data):
    qr_url = await generate_qr(data)
    embed = discord.Embed(title="QR Code", description=f"`{data[:50]}...`")
    embed.set_image(url=qr_url)
    await ctx.send(embed=embed)

@bot.command()
async def create_wallet(ctx):
    # Demo wallet (production: use proper HD wallet)
    privkey = "Lxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"  # Demo
    addr = "LtcDemoAddress1234567890"
    embed = discord.Embed(title="🆕 New LTC Wallet", color=0x00ff00)
    embed.add_field(name="Address", value=addr, inline=False)
    embed.add_field(name="Private Key", value=f"`{privkey}`", inline=False)
    qr_url = await generate_qr(addr)
    embed.set_image(url=qr_url)
    await ctx.send(embed=embed, content="⚠️ **DM ONLY** - Never share privkey!")

bot.run(os.getenv('DISCORD_TOKEN'))

