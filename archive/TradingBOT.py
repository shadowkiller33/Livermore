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
import io
import matplotlib.transforms as mtransforms


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


    def get_kline(self, stock_code, ktype='K_DAY', max_count=160):
        quote_ctx = OpenQuoteContext(host='127.0.0.1', port=11111)
        current_time = datetime.now()
        start_time = (current_time - timedelta(days=max_count)).strftime('%Y-%m-%d')

        ret, data, page_req_key = quote_ctx.request_history_kline(
            stock_code, 
            start=start_time, 
            ktype=ktype, 
            max_count=max_count,
            extended_time=False
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
        print(len(data))
        open_ = data['open']
        close_ = data['close']
        high_ = data['high']
        low_ = data['low']
        time_key_ = data['time_key']
        name = data['name'][0]

        kline_data_with_time = [
            (time_key_[i], open_[i], high_[i], low_[i], close_[i]) 
            for i in range(len(open_))
        ]
        kline_data_without_time = [
            (open_[i], high_[i], low_[i], close_[i]) 
            for i in range(len(open_))
        ]
        quote_ctx.close()
        return (kline_data_with_time, kline_data_without_time, name, ktype)

    


    def plot_kline(self, kline_data_with_time, kline_data_without_time, name, ktype, ema_args):
        """
        kline_data_with_time: 
            A list of lists [datetime, open, high, low, close], e.g.:
                [
                ['2022-01-01 09:30', 10.5, 10.8, 10.2, 10.6],
                ...
                ]
            We'll build a Pandas DataFrame from this and plot.

        Returns a BytesIO (PNG) containing the plot.
        """

        # 1) Basic checks
        if not kline_data_with_time:
            print("No data to plot (kline_data_with_time is empty).")
            return None

        # 2) Build DataFrame with DatetimeIndex and OHLC columns
        df = pd.DataFrame(kline_data_with_time, columns=['Datetime', 'Open', 'High', 'Low', 'Close'])
        df['Datetime'] = pd.to_datetime(df['Datetime'])
        df.set_index('Datetime', inplace=True)
        buy_signals, sell_signals = calc_buy_sell_signals(kline_data_without_time)
        # Make sure buy_signals[i] corresponds to df.iloc[i], i.e. same length/order.

        # 4) Compute the two EMA channels
   
        df['A']  = df['High'].ewm(span=ema_args[0], adjust=False).mean()   
        df['B']  = df['Low'].ewm(span=ema_args[1],  adjust=False).mean()   
        df['A1'] = df['High'].ewm(span=ema_args[2], adjust=False).mean()   
        df['B1'] = df['Low'].ewm(span=ema_args[3],  adjust=False).mean()   

        # 5) Prepare the lines (addplot) for the two channels
        ap_a  = mpf.make_addplot(df['A'],  color='blue')
        ap_b  = mpf.make_addplot(df['B'],  color='blue')
        ap_a1 = mpf.make_addplot(df['A1'], color='orange')
        ap_b1 = mpf.make_addplot(df['B1'], color='orange')

        # 6) Now we plot the candlestick chart, capturing fig+ax
        fig, axlist = mpf.plot(
            df,
            type='candle',
            style='charles',
            addplot=[ap_a, ap_b, ap_a1, ap_b1],
            title=f"Stock:{name}, K-line Chart (Level: {ktype})",
            ylabel='Price',
            volume=False,
            # Instead of figratio/figscale, just set a plain figsize:
            figsize=(14, 7),         # width=14, height=7
            tight_layout=True,       # make sure things aren’t jammed on edges
            returnfig=True
        )
        ax = axlist[0]  # The main price axis

        # 7) Plot "BUY"/"SELL" text below each bar if signals == 1
        #    We'll position the text slightly below the Low price
        index_list = df.index.to_list()
        lows = df['Low'].values
        print(len(buy_signals))
        for i in range(len(df)):
            # BUY signal
            if buy_signals[i] == 1:
                ax.text(
                    x=index_list[i],
                    y=lows[i]-10,
                    s='BUY',
                    color='black',
                    fontsize=12,
                    clip_on=False
                )
            # SELL signal
            if sell_signals[i] == 1:
                ax.text(
                    x=index_list[i],
                    y=lows[i],
                    s='SELL',
                    ha='center',
                    va='bottom',
                    color='red',
                    fontsize=12,
                    clip_on=False
                )
        ymax = df['High'].max()
        
        ax.set_ylim( None, ymax * 1.05 ) 
        # 8) Save figure into a PNG buffer (if needed)


        plt.show()
        buf = io.BytesIO()
        

        fig.savefig(buf, format='png')
        buf.seek(0)

        # 9) Cleanup
        plt.close(fig)

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
    kline_data_with_time, kline_data_without_time, name, ktype = trader.get_kline('HK.02015')
    buf = trader.plot_kline(kline_data_with_time, kline_data_without_time, name, ktype, [24,23,89,90])
    print(buf)
    trader.close_context()
