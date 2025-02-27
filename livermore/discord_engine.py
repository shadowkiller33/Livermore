import logging
logging.getLogger("discord.gateway").setLevel(logging.ERROR)

import time
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
import json
import discord
import asyncio


from itertools import chain
from tqdm import tqdm
from datetime import datetime, timedelta
from mmengine import load, dump

from livermore.finnhub_engine import FinnhubEngine
from livermore.misc import plot_multiple_stock_candles, get_ny_time, get_readable_time
from livermore import livermore_root
from discord.ext import commands, tasks



intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)
engine = FinnhubEngine(api_key="cu9bivpr01qnf5nmlh8gcu9bivpr01qnf5nmlh90")

profiles = load(str(livermore_root / 'data/large_companies_20250206.json'))
lingfeng_selections = load(str(livermore_root / 'data/selected_sotcks.json'))
lingfeng_selections = list(chain(*lingfeng_selections.values()))
symbols_by_sectors = load(str(livermore_root / 'data/lingfeng_symbols.json'))
symbols_to_sector = {}
for name, value in symbols_by_sectors.items():
    for item in value:
        symbols_to_sector[item] = name
symbols = list(symbols_to_sector.keys())


async def create_category_channel(guild, category_name):
    try:
        # Create a category channel in the guild
        category = await guild.create_category_channel(category_name)
        print(f'Successfully created category channel: {category.name}')
    except discord.Forbidden:
        print('The bot does not have the permission to create a category channel.')
    except discord.HTTPException as e:
        print(f'An error occurred while creating the category channel: {e}')


async def create_text_channel(guild, channel_name, category_name=None):
    # Find the category by its name
    category = discord.utils.get(guild.categories, name=category_name)
    if category is None:
        print(f'Category "{category_name}" not found in guild "{guild.name}".')
        return
    try:
        # Create a text channel under the category
        text_channel = await guild.create_text_channel(channel_name, category=category)
        print(f'Successfully created text channel "{text_channel.name}" under category "{category.name}" in guild "{guild.name}".')
    except discord.Forbidden:
        print('The bot does not have the permission to create a text channel.')
    except discord.HTTPException as e:
        print(f'An error occurred while creating the text channel: {e}')


async def delete_channel_by_id(bot, channel_id):
    channel = bot.get_channel(channel_id)
    if channel:
        await channel.delete()
    else:
        print(f"Channel {channel_id} not found.")


async def delete_channels_by_category_name(guild, category_name):
    category = discord.utils.get(guild.categories, name=category_name)
    if category is None:
        print(f"Category {category_name} not found.")
        return

    for channel in category.channels:
        await channel.delete()
        print(f"Deleted channel: {channel.name}")

    print(f"All channels under '{category_name}' have been deleted.")


def find_channel(guild, channel_name, category_name=None):
    channel_name = channel_name.replace(" ", "-").lower()
    if category_name is not None:
        channels = discord.utils.get(guild.categories, name=category_name).channels
    else:
        channels = guild.channels
    return discord.utils.get(channels, name=channel_name)


# @bot.command()
# async def send_test_image(ctx):
#     with open(livermore_root / "data" / "tmp" / "test.png", "rb") as img:
#         content = discord.File(img)
#         await ctx.send("Here is an test image!", file=content)


@bot.command()
async def plot_stock_candle(ctx, symbol):
    # engine.update_recent_candles(symbol)
    data = engine.query_candles_of_different_resolutions(symbol, num=200)
    image = plot_multiple_stock_candles(data, symbol, filename=None)
    await ctx.send(f"Here is the candlestick plot for {symbol}!", file=discord.File(image, f"{symbol}.png"))
    image.close()


@bot.command()
async def plot_options(ctx, symbol: str, expiration: str):
    """
    Discord command to generate the options plot for a given stock symbol and expiration date.
    Usage: !plot_options NVDA 2025-02-15
    """
    # Validate the expiration date format.
    try:
        # This will raise a ValueError if the format is not correct.
        dt = datetime.strptime(expiration, '%Y-%m-%d')
        print(dt)
    except ValueError:
        await ctx.send("Expiration date must be in **YYYY-MM-DD** format. Please try again.")
        return

    await ctx.send(f"Generating options plot for {symbol} with expiration {dt}...")
    output_file_name = f"{symbol}_{dt}.png"
    
    # Generate the plot if the file doesn't already exist.
    if not os.path.exists(output_file_name):
        analyze_option_chain(symbol, expiration, output_file_name)
    try:
        await ctx.send(file=discord.File(output_file_name))
    except Exception as e:
        await ctx.send(f"Error sending the plot: {e}")


async def create_signal_v2_channels(guild):
    category_name = "Signal-V2"
    if find_channel(guild, category_name) is None:
        await create_category_channel(guild, category_name)
    
    for sector_name in ["Good"] + list(symbols_by_sectors.keys()):
        if find_channel(guild, sector_name, category_name) is None:
            await create_text_channel(guild, sector_name, category_name)
    

async def send_test_to_all_v2_channels(guild):
    category_name = "Signal-V2"
    for sector_name in ["Good"] + list(symbols_by_sectors.keys()):
        channel = find_channel(guild, channel_name, category_name)
        message = f"This is a test message for the {sector_name} channel."
        await channel.send(message)


@bot.event
async def on_ready():
    print(f'Logged in as Uer: {bot.user} (ID: {bot.user.id})')
    guild = bot.guilds[0]
    # all_channels = guild.channels
    # await delete_channels_by_category_name(guild, "Signal-V2")
    # await create_signal_v2_channels(guild)
    # await send_test_to_all_v2_channels(guild)
    # await send_stock_buy_signals()
    print(f"Start the server at {get_readable_time(get_ny_time())}!")
    print('------')
    if not send_stock_buy_signals.is_running():
        send_stock_buy_signals.start()
        print("Started background task to send buy signals every 30 minutes.")


PREVIOUS_SIGNAL = None


async def send_signals_to_channel(symbol, signals, is_strong, channel_name):
    # Determine embed color based on signal strength
    color = 0x00FF00  # Green by default
    if is_strong:
        color = 0xFF0000  # Red for multiple signals
    channel = find_channel(bot.guilds[0], channel_name, "Signal-V2")
    # print(channel.id)

    # Create an Embed object
    embed = discord.Embed(
        title=f"{symbol} - Strong Buy" if is_strong else f"{symbol} - {len(signals)} signals",
        color=color,
        timestamp=datetime.utcnow()
    )

    for signal in ["30m", "1h", "2h", "3h", "4h", "1d"]:
        status = "✅" if signal in signals else "❌"
        embed.add_field(
            name=signal,
            value=status,
            inline=True
        )
    embed.set_footer(text="Alert")

    try:
        if channel_name == "Good":
            await channel.send(embed=embed, allowed_mentions=discord.AllowedMentions.none())
            await plot_stock_candle(channel, symbol)
        else:
            await channel.send(embed=embed)
        print(f"Buy signal message sent to channel {channel.id} for stock {symbol}!")
        # msg_sent = True
        # Update the last sent time and signal status for the stock
        # last_sent_data[stock_symbol] = {
        #     "last_sent_time": now,
        #     "last_signal_status": signal_status
        # }
        # save_last_sent_data()  # Persist the update
    except Exception as e:
        print(f"Failed to send message to channel {channel.id}: {e}")
    

@tasks.loop(minutes=30)  # Run the detector every 30 minutes
async def send_stock_buy_signals():
    weights = {
        '30m': 1,
        '1h': 2,
        '2h': 3,
        '3h': 4,
        '4h': 5,
        '1d': 6,
    }
    global PREVIOUS_SIGNAL
    await bot.wait_until_ready()
    try:
        PREVIOUS_SIGNAL = load(livermore_root / 'data/previous_signals.json')
    except:
        PREVIOUS_SIGNAL = {}
    now = get_ny_time()
    if now.weekday() >= 5:
        print ("Skip scanning the stocks on weekends.")
        return
    # alls_opportunities = load(str(livermore_root / 'data/tmp/all_opportunities.json'))
    count = 0
    print(f"Start to scan {len(symbols)} stocks at {get_readable_time(now)}!")
    for symbol in tqdm(symbols):
        # signals = alls_opportunities.get(symbol, {})
        signals = engine.get_recent_signals(symbol)
        if len(signals) == 0 :
            continue
        indices = ["30m", "1h", "2h", "3h", "4h", "1d"]
        is_strong = sum([_ in ["1h", "2h", "3h", "4h", "1d"] for _ in signals]) >= 3
        # best_signal = max([indices.index(_) for _ in signals])
        if not (symbol in lingfeng_selections or is_strong):
            continue
        previous_signal = PREVIOUS_SIGNAL.get(symbol, None)
        if previous_signal is not None:
            previous_score = sum([weights[_] for _ in previous_signal["signal"]])
            current_score = sum([weights[_] for _ in signals])
            timestamp = datetime.fromtimestamp(previous_signal["timestamp"])
            if current_score <= previous_score and (datetime.now() - timestamp < timedelta(hours=24)):
                continue
        PREVIOUS_SIGNAL[symbol] = {"signal": signals, "timestamp": int(time.time())}
        latest_time = get_readable_time(max(list(signals.values())))
        sector_name = symbols_to_sector[symbol]
        count += 1
        print(f"Send signal for {symbol} to channel {sector_name} with {list(signals.keys())} at {latest_time}.")
        await send_signals_to_channel(symbol, signals, is_strong, sector_name)
        if is_strong:
            print(f"Send signal for {symbol} to channel Good with {list(signals.keys())} at {latest_time}.")
            await send_signals_to_channel(symbol, signals, is_strong, "Good")
        dump(PREVIOUS_SIGNAL, livermore_root / 'data/previous_signals.json', indent=2)
            

if __name__ == "__main__":
    DISCORD_BOT_TOKEN = "MTMzMDc5NjEwMzYyODYxOTgyNg.GYqzYE.Dl7aeeapKgk_JeKTVTzX-NiIoWMOqIGFGI46EY"
    bot.run(DISCORD_BOT_TOKEN)
