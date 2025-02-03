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
import json

# API Key
load_dotenv()
# Discord Bot Token
DISCORD_BOT_TOKEN = os.getenv("DISCORD_TOKEN") # Ensure this is kept secure

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
    "semi_conductor": ["NVDA", "AMD", "SMTC", "SOXX", "ARM", "AMAT", "LRCX", "QCOM", "INTC", "TSM", "ASML", "ALAB", "AVGO", "MU", "AAOI"],
    "crypto": ["IBIT", "BTDR", "BTBT", "HUT", "COIN", "RIOT", "CLSK", "BTCT", "MSTR", "MARA"],
    "big_tech":["NFLX", "NVDA", "ORCL", "TSLL", "TSLA", "MSFT", "AMZN", "META", "AAPL", "GOOG"],
    "saas": ["CRM", "MDB", "ZM", "SNOW", "ORCL", "NOW", "WDAY", "SHOP", "CRWD", "DDOG", "TWLO", "SAP", "INTU", "UBER", "APP", "DOCU", "ANET"],
    "ai_software": ["AFRM", "MNDY", "AISP", "INOD", "APLD", "NNOX",  "ADBE", "PANW", "IBM", "PLTR", "CRDO", "INTA", "CLS"],
    "social": ['SNAP', 'RDDT', "PINS", "RBLX", "DIS", "LYV"],
    'robo': ["SERV", "ISRG", "TER"],
    "spy_qqq_iwm": ["IWM", "SPY", "QQQ"],
    "finance": ["DPST", "GS", "V", "WFC", "PYPL", "MS", "JPM", "BAC", "MA", "AXP", "UPST", "SOFI"],
    "bio_med": ["WBA", "JNJ", "UNH", "LLY", "MRNA", "NVO", "PFE", "AMGN", "WAY",  "HIMS", "NVS", "AZN", "ABBV"],
    "vol": ["UVXY"],
    "tlt_tmf": ["TLT", "TMF"],
    "defense": ["LMT", "NOC", "RTX", "GD", "BA", "HII", "LHX", "TXT"],
    "nuclear": ['OKLO', 'SMR', 'LTBR', 'NEE', 'NNE'],
    "energy": ["CAT", "CEG", "LNG", "GEV", "RUN", "ARRY", "VRT", "VST", "FSLR", "KOLD", "XOM", "OXY", "GE"],
    "space": ["DXYZ", "RKLB", "ASTS", "LUNR", "KULR"],
    "small_ai": ["LUNR", "SOUN", "AFRM", "MNDY", "AISP", "INOD", "APLD", "ZETA", "AI", "BBAI", "TEM", "SERV"],
    "short_eft": ['SOXS', 'SQQQ', 'SPXU', 'SDOW', "TSLZ", "NVD", "TZA", "SH"],
    "food": ["MCD", "WEN", "QSR", "SBUX", "DPZ", "PZZA", "WING", "KO", "PEP", "COST", "WMT"],
    "drone": ["AVAV", "BA", "LMT", "NOC", "RCAT", "ACHR", "PDYN"],
    "sports": ["NKE", "UAA", "DKNG", "PENN", "LULU", "ADDYY"],
    "fashion": ['EL', 'LVMUY', 'LRLCY', 'ELF', "TPR", "RL", "TJX"],
    "travel": ["AAL", "ABNB", "RCL", "CCL", "TCOM", "BKNG", "EXPE", "DAL", "UAL", "LUV"],
    "auto_drive": ["RIVN", "TSLA", "UBER", "LYFT"],
    "CN": ["BABA", "TCEHY", "JD", "BIDU", "NTES", "PDD", "BILI", "JD", "FXI", "YINN", "YANG"]
}

# testing purpose
# stocks = {
#     "semi_conductor": ["AMD", "AMD"]
# }


channel2id = {
    "semi_conductor": int(os.getenv("SEMI_CONDUCTOR")),
    "crypto": int(os.getenv("CRYPTO")),
    "big_tech": int(os.getenv("BIG_TECH")),
    "ai_software": int(os.getenv("AI_SOFTWARE")),
    "spy_qqq_iwm": int(os.getenv("SPY_QQQ_IWM")),
    "finance": int(os.getenv("FINANCE")),
    "bio_med": int(os.getenv("BIO_MED")),
    "vol": int(os.getenv("VOL")),
    "tlt_tmf": int(os.getenv("TLT_TMF")),
    "energy": int(os.getenv("ENERGY")),
    "space": int(os.getenv("SPACE")),
    "robo": int(os.getenv("ROBO")),
    "social": int(os.getenv("SOCIAL")),
    "defense": int(os.getenv("DEFENSE")),
    "nuclear": int(os.getenv("NUCLEAR")),
    "small_ai": int(os.getenv("SMALL_AI")),
    "short_eft": int(os.getenv("SHORT_EFT")),
    "food": int(os.getenv("FOOD")),
    "drone": int(os.getenv("DRONE")),
    "sports": int(os.getenv("SPORTS")),
    "fashion": int(os.getenv("FASHION")),
    "travel": int(os.getenv("TRAVEL")),
    "auto_drive": int(os.getenv("AUTO_DRIVE")),
    "CN": int(os.getenv("CN"))
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
    if not send_buy_signal_message.is_running():
        send_buy_signal_message.start()
        print("Started background task to send buy signals every hour.")


# Initialize a dictionary to track the last sent time for each stock
last_sent_times_file = 'last_sent_times.json'

# Load existing tracking data if available
if os.path.exists(last_sent_times_file):
    with open(last_sent_times_file, 'r') as f:
        last_sent_data = json.load(f)
    # Convert string timestamps back to datetime objects
    last_sent_data = {
        k: {
            "last_sent_time": datetime.fromisoformat(v["last_sent_time"]),
            "last_signal_status": v["last_signal_status"]
        } for k, v in last_sent_data.items()
    }
else:
    last_sent_data = {}

# Function to save tracking data to a file
def save_last_sent_data():
    with open(last_sent_times_file, 'w') as f:
        # Convert datetime objects to ISO format strings for JSON serialization
        json.dump({
            k: {
                "last_sent_time": v["last_sent_time"].isoformat(),
                "last_signal_status": v["last_signal_status"]
            } for k, v in last_sent_data.items()
        }, f, indent=4)




@tasks.loop(minutes=90)  # Run the detector every 1 hour
async def send_buy_signal_message():
    await bot.wait_until_ready()
    channels = bot.get_all_channels()

    try:
        for chan in channels:
            # Only consider specific channels
            if chan.id in channel2id.values():
                cur_sector = id2channel[chan.id]
                print("Assessing buy signal for sector: ", cur_sector)
                for stock_symbol in stocks[cur_sector]:
                    print(f"Assessing buy signal for stock: {stock_symbol}")
                    detector = detector_dict[stock_symbol]
                    # Assess buy signals for the current stock
                    signal_status = detector.multi_resolution_signal()
                    await asyncio.sleep(15)
                    if any(signal_status.values()):
                        now = datetime.utcnow()
                        last_sent_info = last_sent_data.get(stock_symbol)

                        send_message = False
                        if last_sent_info:
                            last_sent_time = last_sent_info["last_sent_time"]
                            last_signal_status = last_sent_info["last_signal_status"]

                            # Check if signal status has changed
                            if signal_status != last_signal_status:
                                send_message = True
                                print(f"Signal status changed for {stock_symbol}. Preparing to send message.")
                            else:
                                # Check if a message was sent within the last 24 hours
                                if (now - last_sent_time) > timedelta(days=1):
                                    send_message = True
                                    print(f"24 hours passed since last message for {stock_symbol}. Preparing to send message.")
                                else:
                                    print(f"Message for {stock_symbol} was sent less than a day ago and no signal change. Skipping.")
                        else:
                            # No previous record, send message
                            send_message = True
                            print(f"No previous message sent for {stock_symbol}. Preparing to send message.")
                    
                        if send_message:
                            # Determine embed color based on signal strength
                            color = 0x00FF00  # Green by default
                            if signal_status.get('Good_buying_option'):
                                color = 0xFFA500  # Orange for good buying options
                            if sum(signal_status.values()) > 3:
                                color = 0xFF0000  # Red for multiple signals

                            # Create an Embed object
                            embed = discord.Embed(
                                title="📈 **Buy Signal Triggered!**",
                                description=f"**{stock_symbol}** has triggered a buy signal.",
                                color=color,
                                timestamp=datetime.utcnow()
                            )

                            # Add a field for each timeframe's signal status
                            for timeframe, triggered in signal_status.items():
                                status = "✅ Yes" if triggered else "❌ No"
                                embed.add_field(
                                    name=timeframe,
                                    value=status,
                                    inline=True
                                )

                            # Add a footer for additional context
                            embed.set_footer(text="Automated Alert", icon_url="https://i.imgur.com/rdm3D7P.png")

                            try:
                                await chan.send(embed=embed)
                                print(f"Buy signal message sent to channel {chan.id} for stock {stock_symbol}!")
                                msg_sent = True
                                # Update the last sent time and signal status for the stock
                                last_sent_data[stock_symbol] = {
                                    "last_sent_time": now,
                                    "last_signal_status": signal_status
                                }
                                save_last_sent_data()  # Persist the update
                            except Exception as e:
                                print(f"Failed to send message to channel {chan.id}: {e}")

            else:
                print(f"Channel {chan.id} is not in the monitored list.")

    except Exception as e:
        print(f"Error occurred: {e}")


# Run the bot
bot.run(DISCORD_BOT_TOKEN)