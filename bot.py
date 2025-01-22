import discord
from datetime import datetime, timedelta
from TradingBOT import Trader
import logging
import argparse

# Parse command-line arguments for the bot token
parser = argparse.ArgumentParser(description="Run the Discord bot.")
parser.add_argument('--token', type=str, required=True, help="Discord bot token")
args = parser.parse_args()

intents = discord.Intents.default()
intents.messages = True

bot = discord.Client(intents=intents)

trader = Trader()

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    # Check if the bot is mentioned
    if bot.user in message.mentions:
        # Remove the mention from the message content
        user_message = message.content.replace(f"<@{bot.user.id}>", "").strip()
        # Respond to the mention
        if user_message.startswith("stock"):
            parts = user_message.split()
            if len(parts) < 2:
                await message.channel.send("Please provide a stock code. Usage: @Bot stock <code>")
                return

            stock_code = parts[1]
            try:


                #history_kline_data = trader.show_history_kl_quota()
                #print(history_kline_data)

                kline_data_with_time, kline_data_without_time = trader.get_kline(stock_code=stock_code)

                if kline_data_with_time is not None:
                    # Format the response
                    import pandas as pd

                    buf = trader.plot_kline(kline_data_with_time, kline_data_without_time)  # Suppose we use the function from above

                    # 4) Create a Discord file from the buffer
                    file = discord.File(buf, filename="kline_chart.png")
                    await message.channel.send(
                        content=f"K-line Data for {stock_code}",
                        file=file
                    )
                else:
                    await message.channel.send(f"Could not fetch K-line data for {stock_code}.")
            except Exception as e:
                await message.channel.send(f"An error occurred: {e}")
        else:
            # Generic response if no valid command is given after mention
            await message.channel.send(f"Hello! You mentioned me. How can I assist you?")

# Run the bot with the token from command-line arguments
bot.run(args.token)
