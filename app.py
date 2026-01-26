import discord
from discord.ext import commands
import requests
import os
import re
import asyncio

# ─────────────────────────────
# BOT INTENTS
# ─────────────────────────────
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(
    command_prefix=',',
    intents=intents,
    help_command=None
)

# ─────────────────────────────
# API ENDPOINTS
# ─────────────────────────────
BLOCKCYPHER_LTC = "https://api.blockcypher.com/v1/ltc/main"
COINGECKO_LTC = "https://api.coingecko.com/api/v3/simple/price?ids=litecoin&vs_currencies=usd"

# ─────────────────────────────
# BOT READY
# ─────────────────────────────
@bot.event
async def on_ready():
    print(f"✅ {bot.user} is online")
    print(f"🔗 Connected to {len(bot.guilds)} server(s)")

# ─────────────────────────────
# HELPERS
# ─────────────────────────────
async def get_ltc_price():
    try:
        loop = asyncio.get_event_loop()
        resp = await loop.run_in_executor(
            None, lambda: requests.get(COINGECKO_LTC, timeout=10)
        )
        resp.raise_for_status()
        return resp.json()["litecoin"]["usd"]
    except:
        return 70.0  # fallback price


async def get_ltc_balance(address, retries=3):
    url = f"{BLOCKCYPHER_LTC}/addrs/{address}/balance"

    for attempt in range(retries):
        try:
            loop = asyncio.get_event_loop()
            resp = await loop.run_in_executor(
                None, lambda: requests.get(url, timeout=10)
            )
            resp.raise_for_status()
            data = resp.json()

            return {
                "final_balance": data.get("final_balance", 0) / 100000000,
                "balance": data.get("balance", 0) / 100000000,
                "unconfirmed": data.get("unconfirmed_balance", 0) / 100000000,
                "n_tx": data.get("n_tx", 0)
            }

        except Exception as e:
            print(f"⚠️ Balance fetch error ({attempt+1}): {e}")
            if attempt < retries - 1:
                await asyncio.sleep(2)

    return None


def safe_eval_math(expression):
    try:
        expression = expression.replace(" ", "")

        if not re.fullmatch(r'[\d+\-*/().]+', expression):
            return None

        if not re.search(r'[\+\-\*/]', expression):
            return None

        result = eval(expression, {"__builtins__": {}}, {})
        return result
    except:
        return None

# ─────────────────────────────
# MESSAGE HANDLER (AUTO CALC)
# ─────────────────────────────
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # If command, don't calculate
    if message.content.startswith(','):
        await bot.process_commands(message)
        return

    content = message.content.strip()

    # Auto calculator
    if re.search(r'[\+\-\*/]', content) and re.fullmatch(r'[\d+\-*/().\s]+', content):
        result = safe_eval_math(content)

        if result is not None:
            if isinstance(result, float):
                result = int(result) if result.is_integer() else round(result, 8)

            await message.reply(str(result), mention_author=False)
            return

# ─────────────────────────────
# COMMAND: ,bal
# ─────────────────────────────
@bot.command(name="bal")
async def balance(ctx, address: str = None):
    if not address:
        await ctx.send("❌ Usage: `,bal <ltc_address>`")
        return

    if not (
        address.startswith("L") or
        address.startswith("M") or
        address.startswith("ltc1") or
        address.startswith("3")
    ):
        await ctx.send("❌ Invalid LTC address format")
        return

    loading = await ctx.send(f"🔍 Checking balance for `{address}`...")

    balance_data = await get_ltc_balance(address)
    if balance_data is None:
        await loading.edit(content="❌ Failed to fetch balance. Try again later.")
        return

    ltc_price = await get_ltc_price()
    usd_value = balance_data["final_balance"] * ltc_price

    reply = (
        f"Your LTC address is: {address}\n"
        f"Your LTC balance is: {balance_data['final_balance']:.4f} LTC\n"
        f"Your USD balance is: ${usd_value:.2f} USD"
    )

    await loading.edit(content=reply)

# ─────────────────────────────
# COMMAND: ,help
# ─────────────────────────────
@bot.command()
async def help(ctx):
    await ctx.send(
        "```\n"
        "🤖 LTC Balance & Calculator Bot\n\n"
        "Commands:\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        ",bal <address>  - Check LTC balance\n"
        ",help           - Show this help\n\n"
        "Auto Calculator:\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "Just type math expressions\n\n"
        "Examples:\n"
        "10*11\n"
        "100/5\n"
        "(50+10)*2\n"
        "```"
    )

# ─────────────────────────────
# RUN BOT
# ─────────────────────────────
if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")

    if not token:
        print("❌ DISCORD_TOKEN not found")
        exit(1)

    print("🚀 Starting bot...")
    bot.run(token)
