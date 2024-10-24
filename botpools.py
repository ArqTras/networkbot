import re
import requests
import logging
import asyncio
import discord
from discord.ext import commands
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Enable logging (excluding debug information)
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# Important links
important_links = (
    "🔗 *Important Links*\n\n"
    "🌐 [ArQmA website](https://arqma.com/)\n"
    "📂 [Github](https://github.com/arqma)\n"
    "📖 [Documentation](https://github.com/arqma/arqma/wiki/)\n"
    "🖥️ [GUI Wallet](https://github.com/arqma/arqma-electron-wallet/releases/)\n"
    "📝 [Paper Wallet](https://generate.arqma.com/)\n"
    "⛏️ [Pool stats](https://miningpoolstats.stream/arqma)\n"
    "💬 [Telegram](https://telegram.arqma.com/)\n"
    "🎮 [Discord](https://chat.arqma.com/)\n"
)

# Available commands for Telegram
telegram_available_commands = (
    "📜 *Available Commands*\n\n"
    "📊 /network - Get Arqma network statistics\n"
    "🔗 /links - Display important Arqma-related links\n"
    "⛏️ /pools - Display Arqma mining pools with hashrates\n"
    "❓ /helpme - Show this help message\n"
)

# Available commands for Discord
discord_available_commands = (
    "📜 **Available Commands**\n\n"
    "📊 !network - Get Arqma network statistics\n"
    "🔗 !links - Display important Arqma-related links\n"
    "⛏️ !pools - Display Arqma mining pools with hashrates\n"
    "❓ !helpme - Show this help message\n"
)

# Function to read the token from the specified file
def read_token_file(file_name):
    try:
        with open(file_name, "r") as file:
            token = file.read().strip()
        return token
    except FileNotFoundError:
        logger.error(f"{file_name} file not found. Please create the file and add your bot token.")
        return None
    except Exception as e:
        logger.error(f"An error occurred while reading the {file_name} file: {e}")
        return None

# Helper function to get data from a URL
def get_data(url, context):
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return response.text if context == 'poolsSecurity' else response.json()
        else:
            logger.error(f"Failed to fetch {context} data, status code: {response.status_code}")
            return None
    except Exception as e:
        logger.error(f"Error fetching {context} data: {e}")
        return None

# Function to fetch and process pool data for the /pools command
def fetch_pools_data():
    pools_security = get_data('https://miningpoolstats.stream/arqma', 'poolsSecurity')
    if pools_security is None:
        return None

    match = re.search(r'var last_time = "([^"]+)"', pools_security)
    if not match:
        logger.error("Failed to extract 't' parameter from poolsSecurity data.")
        return None

    t = match.group(1)

    pools_query_url = f'https://data.miningpoolstats.stream/data/arqma.js?t={t}'
    pools_query = get_data(pools_query_url, 'poolsQuery')
    if pools_query is None:
        return None

    pools_info = pools_query.get('data', [])
    sorted_pools = sorted(pools_info, key=lambda x: x.get('hashrate', 0), reverse=True)

    formatted_pools = []
    for pool in sorted_pools:
        name = pool.get('pool_id', 'Unknown Pool')
        hashrate = pool.get('hashrate', 0)

        if hashrate >= 1_000_000:  # If hashrate is 1 MH/s or greater
            hashrate_mh = hashrate / 1_000_000
            formatted_pools.append(f"⛏️ *{name}*: {hashrate_mh:.2f} MH/s")
        else:  # If hashrate is less than 1 MH/s, display in KH/s
            hashrate_kh = hashrate / 1_000
            formatted_pools.append(f"⛏️ *{name}*: {hashrate_kh:.2f} KH/s")

    return "\n".join(formatted_pools)

# Function to fetch network info
def fetch_network_info():
    url = "https://explorer.arqma.com/api/networkinfo"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json().get('data', {})
            height = data.get('height', 'N/A')
            hash_rate = data.get('hash_rate', 0) / 1_000_000  # Convert hash_rate to MH/s
            difficulty = data.get('difficulty', 'N/A')
            return {'height': height, 'hashrate': hash_rate, 'difficulty': difficulty}
        else:
            logger.error(f"Failed to fetch network info, status code: {response.status_code}")
            return None
    except Exception as e:
        logger.error(f"Error fetching network info: {e}")
        return None

# Function to fetch emission data
def fetch_emission_data():
    url = "https://explorer.arqma.com/api/emission"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json().get('data', {})
        emission = int(data.get('coinbase', 0) / 100_000)
        emission_str = str(emission)[:8]
        return {'emission': emission_str}
    else:
        logger.error(f"Failed to fetch emission data, status code: {response.status_code}")
        return None

# Function to fetch ARQ price in BTC
def fetch_arq_price():
    url = "https://tradeogre.com/api/v1/ticker/arq-btc"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            price_in_btc = float(data.get('price', 0))
            price_in_sat = round(price_in_btc * 100_000_000)
            price_btc_formatted = f"{price_in_btc:.8f}"
            return {'price_btc': price_btc_formatted, 'price_sat': price_in_sat}
        else:
            logger.error(f"Failed to fetch ARQ price from TradeOgre, status code: {response.status_code}")
            return None
    except Exception as e:
        logger.error(f"Error fetching ARQ price: {e}")
        return None

# Telegram bot command handler for /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Hello! Use /network to get the latest Arqma network, emission, and price stats.")

# Telegram bot command handler for /pools
async def pools(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    pool_data = fetch_pools_data()
    if pool_data:
        await update.message.reply_text(f"🔗 *Arqma Pools*\n\n{pool_data}", parse_mode='Markdown')
    else:
        await update.message.reply_text("Failed to fetch pool data.")

# Telegram bot command handler for /network
async def network(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    network_data = fetch_network_info()
    emission_data = fetch_emission_data()
    arq_price = fetch_arq_price()

    if network_data and emission_data and arq_price:
        message = (
            "🔗 *Arqma Network Stats*\n\n"
            f"📊 *Network Height*: {network_data['height']}\n"
            f"💻 *Network Hashrate*: {network_data['hashrate']:.2f} MH/s\n"
            f"⚙️ *Network Difficulty*: {network_data['difficulty']}\n"
            f"🪙 *Total Emission (Coinbase)*: {emission_data['emission']} ARQ\n"
            f"💰 *TO Price*: {arq_price['price_btc']} BTC ({arq_price['price_sat']} sat)\n"
        )
        await update.message.reply_text(message, parse_mode='Markdown')
    else:
        await update.message.reply_text("Failed to fetch network, emission, or price data.")

# Telegram bot command handler for /links
async def links(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(important_links, parse_mode='Markdown')

# Telegram bot command handler for /helpme
async def helpme(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(telegram_available_commands, parse_mode='Markdown')

# Discord bot setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Discord bot command handler for !pools
@bot.command(name="pools")
async def discord_pools(ctx):
    pool_data = fetch_pools_data()
    if pool_data:
        await ctx.send(f"🔗 **Arqma Pools**\n\n{pool_data}")
    else:
        await ctx.send("Failed to fetch pool data.")

# Discord bot command handler for !network
@bot.command(name="network")
async def discord_network(ctx):
    network_data = fetch_network_info()
    emission_data = fetch_emission_data()
    arq_price = fetch_arq_price()

    if network_data and emission_data and arq_price:
        message = (
            "🔗 **Arqma Network Stats**\n\n"
            f"📊 **Network Height**: {network_data['height']}\n"
            f"💻 **Network Hashrate**: {network_data['hashrate']:.2f} MH/s\n"
            f"⚙️ **Network Difficulty**: {network_data['difficulty']}\n"
            f"🪙 **Total Emission (Coinbase)**: {emission_data['emission']} ARQ\n"
            f"💰 **TO Price**: {arq_price['price_btc']} BTC ({arq_price['price_sat']} sat)\n"
        )
        await ctx.send(message)
    else:
        await ctx.send("Failed to fetch network, emission, or price data.")

# Discord bot command handler for !links
@bot.command(name="links")
async def discord_links(ctx):
    await ctx.send(important_links)

# Discord bot command handler for !helpme
@bot.command(name="helpme")
async def discord_helpme(ctx):
    await ctx.send(discord_available_commands)

# Function to start the Telegram bot asynchronously
async def start_telegram_bot():
    token = read_token_file("token.info")
    if not token:
        return

    application = Application.builder().token(token).build()
    application.add_handler(CommandHandler("pools", pools))
    application.add_handler(CommandHandler("network", network))
    application.add_handler(CommandHandler("links", links))
    application.add_handler(CommandHandler("helpme", helpme))
    application.add_handler(CommandHandler("start", start))

    logger.info("Telegram bot is connected and running...")
    await application.initialize()
    await application.start()
    await application.updater.start_polling()

# Function to start the Discord bot asynchronously
async def start_discord_bot():
    token = read_token_file("discord_token.info")
    if not token:
        return

    logger.info("Discord bot is connected and running...")
    await bot.start(token)

# Main function to run both Telegram and Discord bots concurrently
async def main():
    await asyncio.gather(
        start_telegram_bot(),
        start_discord_bot()
    )

if __name__ == '__main__':
    asyncio.run(main())

