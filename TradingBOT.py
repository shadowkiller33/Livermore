# MooMoo API Documentation, English:
# https://openapi.moomoo.com/moomoo-api-doc/en/intro/intro.html
# 官方文档，中文:
# https://openapi.moomoo.com/moomoo-api-doc/intro/intro.html

from moomoo import *
import schedule
import seaborn as sns
import matplotlib.pyplot as plt
import numpy as np
from Trading.metrics import calc_buy_sell_signals
import mplfinance as mpf

'''
Step 1: Set up the environment information
'''
# Environment Variables
MOOMOOOPEND_ADDRESS = "127.0.0.1"  # should be same as the OpenD host IP, just keep as default
MOOMOOOPEND_PORT = 11111  # should be same as the OpenD port number, make sure keep both the same
# REAL = "REAL"
# SIMULATE = "SIMULATE"

'''
Step 2: Set up the account information
'''
SECURITY_FIRM = SecurityFirm.FUTUINC  # set up the security firm based on your broker account registration
# for U.S. account, use FUTUINC, (default)
# for HongKong account, use FUTUSECURITIES
# for Singapore account, use FUTUSG
# for Australia account, use FUTUAU

'''
Step 3: Set up the trading information
'''
FILL_OUTSIDE_MARKET_HOURS = True  # enable if order fills on extended hours
TRADING_MARKET = TrdMarket.US  # set up the trading market, US market, HK for HongKong, etc.
# NONE = "N/A"
# HK = "HK"
# US = "US"
# CN = "CN"
# HKCC = "HKCC"
# FUTURES = "FUTURES"


# Trader class:
class Trader:
    def __init__(self, name='Your Trader Name'):
        self.name = name
        self.trade_context = None

    def init_context(self):
        self.trade_context = OpenSecTradeContext(filter_trdmarket=TRADING_MARKET, host=MOOMOOOPEND_ADDRESS,
                                                 port=MOOMOOOPEND_PORT, security_firm=SECURITY_FIRM)

    def close_context(self):
        self.trade_context.close()


    def get_kline(self, stock_code, ktype='K_DAY', max_count=50):
        quote_ctx = OpenQuoteContext(host='127.0.0.1', port=11111)
        current_time = datetime.now()
        start_time = (current_time - timedelta(days=50)).strftime('%Y-%m-%d')

        ret, data, page_req_key = quote_ctx.request_history_kline(
            stock_code, 
            start=start_time, 
            ktype=ktype, 
            max_count=max_count
        )
        if ret != RET_OK:
            # ret not OK means an error occurred
            print(f"Error requesting kline data: {data}")
            quote_ctx.close()
            return ([], [])
        
        if data.empty:
            # data is empty => no rows returned
            print("No kline data returned; the DataFrame is empty.")
            quote_ctx.close()
            return ([], [])

        open_ = data['open']
        close_ = data['close']
        high_ = data['high']
        low_ = data['low']
        time_key_ = data['time_key']

        kline_data_with_time = [
            (time_key_[i], open_[i], high_[i], low_[i], close_[i]) 
            for i in range(len(open_))
        ]
        kline_data_without_time = [
            (open_[i], high_[i], low_[i], close_[i]) 
            for i in range(len(open_))
        ]
        quote_ctx.close()
        return (kline_data_with_time, kline_data_without_time)

    


    def plot_kline(self, kline_data_with_time, kline_data_without_time):
        if not kline_data_with_time:
            print("No data to plot (kline_data_with_time is empty).")
            return None

        # 1) Calculate signals
        buy_signals, sell_signals = calc_buy_sell_signals(
            kline_data_without_time, s=12, p=26, m=9
        )

        # 2) Build DataFrame
        df = pd.DataFrame(
            kline_data_with_time,
            columns=['DatetimeIndex', 'Open', 'High', 'Low', 'Close']
        )
        df['DatetimeIndex'] = pd.to_datetime(df['DatetimeIndex'])
        df.set_index('DatetimeIndex', inplace=True)

        # 3) Plot using mplfinance
        #    We'll capture fig and ax objects so we can annotate after plotting.
        fig, axlist = mpf.plot(
            df,
            type='candle',
            style='charles',
            title='Candlestick Chart with Text BUY/SELL',
            ylabel='Price',
            volume=False,
            figratio=(12,6),
            figscale=1.2,
            returnfig=True   # Important: we need fig and ax to annotate
        )

        ax = axlist[0]  # The main price axis

        # 4) Annotate text for BUY/SELL signals
        #    We'll place the text slightly below the candle's Low price for clarity.
        #    For a better visual, you might scale the y a bit more (e.g. low * 0.98, etc.)
        index_list = df.index.to_list()  # list of Timestamps for each row
        lows = df['Low'].values

        for i in range(len(df)):
            if buy_signals[i] == 1:
                ax.text(
                    x=index_list[i],
                    y=lows[i] * 0.99,         # a bit below the candle
                    s='BUY',
                    color='green',
                    fontsize=8,              # adjust as you like
                    ha='center',
                    va='top'
                )
            if sell_signals[i] == 1:
                ax.text(
                    x=index_list[i],
                    y=lows[i] * 0.99,
                    s='SELL',
                    color='red',
                    fontsize=8,
                    ha='center',
                    va='top'
                )

        # 5) If you want to save the figure to a buffer (e.g., for a web response):
        buf = io.BytesIO()
        fig.savefig(buf, format='png', bbox_inches='tight')
        buf.seek(0)

        plt.close(fig)  # Close it to free memory if you're done with it

        return buf

        
        
        
    
    def show_history_kl_quota(self, get_detail):
        quote_ctx = OpenQuoteContext(host='127.0.0.1', port=11111)

        ret, data = quote_ctx.get_history_kl_quota(get_detail=True)  # 设置 true 代表需要返回详细的拉取历史 K 线的记录
        if ret == RET_OK:
            print(data)
        else:
            print('error:', data)
        quote_ctx.close()

        return data


if __name__ == '__main__':
    trader = Trader()
    trader.init_context()
    kline_data_with_time, kline_data_without_time = trader.get_kline('HK.00700')
    buf = trader.plot_kline(kline_data_with_time, kline_data_without_time)
    print(buf)
    trader.close_context()
