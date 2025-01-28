import time
import pandas as pd
import numpy as np
from engine import FinnhubEngine
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import discord
from discord.ext import commands, tasks
import asyncio
from dotenv import load_dotenv
from buy_signal_bot import BuySignalDetector
import os

# API Key
load_dotenv()
# Discord Bot Token
DISCORD_BOT_TOKEN = os.getenv("DISCORD_TOKEN") # Ensure this is kept secure

# Define your Discord channel ID where messages will be sent
DISCORD_CHANNEL_ID = os.getenv("DISCORD_CHANNEL")

# Initialize the Discord bot
intents = discord.Intents.default()
intents.message_content = True  # Enable privileged intents if needed

bot = commands.Bot(command_prefix='!', intents=intents)

# Initialize Finnhub Engine or any other necessary components
engine = FinnhubEngine()
symbol = "AAPL"  # Example symbol
detector = BuySignalDetector(symbol, engine)



# initialize signal detector for different stocks
stocks = {
    "semi_conductor": ["SMTC", "SOXX", "ARM", "AMAT", "LRCX", "QCOM", "INTC", "TSM", "ASML", "ALAB", "AVGO", "MU", "NVDA", "AMD"],
    "crypto": ["IBIT", "BTDR", "BTBT", "HUT", "COIN", "RIOT", "CLSK", "BTCT", "MSTR", "MARA"],
    "big_tech":["CRM", "MDB", "ZM", "NFLX", "SNOW", "PANW", "NVDA", "ORCL", "TSLL", "TSLA", "MSFT", "AMZN", "META", "AAPL", "GOOG"],
    "ai_software": ["TEM", "LUNR", "SOUN", "AFRM", "MRVL", "MNDY", "ASTS", "NBIS", "AISP", "INOD", "APLD", "NNOX", "ZETA", "AI", "BBAI"],
    "spy_qqq_iwm": ["IWM", "SPY", "QQQ"],
    "finance": ["DPST", "GS", "V", "WFC", "PYPL", "MS", "JPM", "BAC", "MA", "AXP"],
    "bio_med": ["WBA", "JNJ", "UNH", "FDMT", "DNLI", "BHVN", "AURA", "WAY", "ARCT", "HIMS"],
    "vol": ["VIX", "UVXY"],
    "tlt_tmf": ["TLT", "TMF"],
    "energy": ["CAT", "CEG", "LTBR", "LNG", "GEV", "SMR", "RUN", "ARRY", "VRT", "VST", "FSLR", "KOLD", "OKLO", "XOM", "OXY"],
}

channel2id = {
    "semi_conductor": 1333613478685970554,
    "crypto": 1333613521891495998,
    "big_tech": 1333613598450384987,
    "ai_software": 1333613642431594527,
    "spy_qqq_iwm": 1333613691110821888,
    "finance": 1333613735604125737,
    "bio_med": 1333613812309557319,
    "vol": 1333613896623198298,
    "tlt_tmf": 1333614021915574304,
    "energy": 1333614121886683207,
}

id2channel = {v: k for k, v in channel2id.items()}

detector_dict = {}
for _, stock_list in stocks.items():
    for stock in stock_list:
        detector = BuySignalDetector(stock, engine)
        detector_dict[stock] = detector



@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    print('------')
    if not send_hello_message.is_running():
        send_hello_message.start()
        print("Started background task to send 'Hello!' messages every minute.")


@tasks.loop(minutes=60) # we run the detector every 1 hour
async def send_hello_message():
    await bot.wait_until_ready()
    channels = bot.get_all_channels()
    msg_sent = False

    try:
        for chan in channels:
            # other channel are not considered
            if chan.id in channel2id.values():
                cur_sector = id2channel[chan.id]
                print("Assessing buy signal for sector: ", cur_sector)
                for stock_symbol in stocks[cur_sector]:
                    detector = detector_dict[stock_symbol]
                    # print(f"Assessing buy signals for {stock_symbol}")
                    signal_status = detector.multi_resolution_signal()
                    # print(signal_status)
                    # signal is a dict, eg: {'30min': False, '1H': False, '2H': False, '3H': False, '4H': False, 'D': False, 'Good_buying_option': False}
                    await asyncio.sleep(1)
                    if any(signal_status.values()):
                        warning_msg = "\n\n" + "#" * 20
                        warning_msg += f"\nWarning: Buy signal triggered for {stock_symbol} in the past 2 days!"
                        warning_msg += "\nSignal Status:"
                        for timeframe, triggered in signal_status.items():
                            warning_msg += f"\n{timeframe}: {'Yes' if triggered else 'No'}"
                        warning_msg += "\n\n"
                        try:
                            await chan.send(warning_msg)
                            print(f"Warning msg sent!")
                            msg_sent = True
                        except Exception as e:
                            print(f"Failed to send message: {e}")
                await asyncio.sleep(60) # reset the request after each sector is finished
    except Exception as e:
        print(f"Error occurred: {e}")
                    
    if not msg_sent:
        print(f"No warning triggered in this period.")

# Run the bot
bot.run(DISCORD_BOT_TOKEN)