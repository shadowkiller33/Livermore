import time
import pandas as pd
import numpy as np
from engine import FinnhubEngine
from metrics.ema import compute_ema
from metrics.lingfeng import calc_buy_sell_signals
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

LOOKBACK_COUNT=365


def resample_kline_data(df, timeframe):
    """
    Resample 1-hour kline data to a higher timeframe.
    
    Parameters:
    - df (pd.DataFrame): Original 1-hour kline data with datetime index.
    - timeframe (str): Resampling timeframe (e.g., '2H', '3H', '4H').
    
    Returns:
    - pd.DataFrame: Resampled kline data.
    """
    resampled_df = df.resample(timeframe).agg({
        'o': 'first',
        'c': 'last',
        'h': 'max',
        'l': 'min',
        'v': 'sum'  # Assuming 'v' is volume
    }).dropna()
    
    return resampled_df


def get_past_month_dates():
    """
    Returns a list of dates for the past week (including today).
    Format: YYYY-MM-DD
    """
    today = datetime.now().date()
    past_week = [today - timedelta(days=i) for i in range(31)]
    past_week_dates = [day.strftime('%Y-%m-%d') for day in reversed(past_week)]
    return past_week_dates


class BuySignalDetector:
    def __init__(self, stock_symbol, engine: FinnhubEngine):
        self.engine = engine
        self.stock_symbol = stock_symbol    
        self.visual = True # disable this when serving in real-time


    def multi_resolution_signal(self):
        day_data = self.engine.get_historical_prices(self.stock_symbol, 
                                                            resolution='D', 
                                                            count=LOOKBACK_COUNT,
                                                            )
        day_data['t'] = pd.to_datetime(day_data['t'], unit='s')
        day_data.set_index('t', inplace=True)
        day_signal = self.compute_vegas_channel_and_signel(day_data, visualize=False)

        halfhour_data = self.engine.get_historical_prices(self.stock_symbol, 
                                                            resolution='30', 
                                                            count=LOOKBACK_COUNT,
                                                            )
        halfhour_data['t'] = pd.to_datetime(halfhour_data['t'], unit='s')
        halfhour_data.set_index('t', inplace=True)
        halfhour_signal = self.compute_vegas_channel_and_signel(halfhour_data, visualize=False)

        onehour_historical_data = self.engine.get_historical_prices(self.stock_symbol, 
                                                            resolution='60', 
                                                            count=LOOKBACK_COUNT,
                                                            )
        onehour_historical_data['t'] = pd.to_datetime(onehour_historical_data['t'], unit='s')
        onehour_historical_data.set_index('t', inplace=True)
        twohour_historical_data = resample_kline_data(onehour_historical_data, '2h')
        threehour_historical_data = resample_kline_data(onehour_historical_data, '3h')
        fourhour_historical_data = resample_kline_data(onehour_historical_data, '4h')

        onehour_signal = self.compute_vegas_channel_and_signel(onehour_historical_data, visualize=False)
        twohour_signal = self.compute_vegas_channel_and_signel(twohour_historical_data, visualize=False)
        threehour_signal = self.compute_vegas_channel_and_signel(threehour_historical_data, visualize=False)
        fourhour_signal = self.compute_vegas_channel_and_signel(fourhour_historical_data, visualize=False)

        # combine all signals for warning
        resampled_data = {
            '30min': halfhour_signal,
            '1H': onehour_signal,
            '2H': twohour_signal,
            '3H': threehour_signal,
            '4H': fourhour_signal,
            'D': day_signal,
        }
        return self.check_buy_signals_past_two_days(resampled_data)

        # check if any signal is triggered last week/month, this is debugging purpose
        # self.check_buy_signals_past_week(resampled_data)


    def check_buy_signals_past_two_days(self, resampled_data):
        """
        Checks if any buy signal was triggered in each timeframe within the past 2 days.

        Parameters:
        - resampled_data (dict): Dictionary containing buy signals for different timeframes.

        Returns:
        - dict: Dictionary with timeframes as keys and boolean values indicating buy signals.
        """
        two_days_ago = datetime.now() - timedelta(days=2)
        signal_status = {}
        total_triggered = 0
        for timeframe, df in resampled_data.items():
            # Ensure the DataFrame index is datetime
            if not isinstance(df.index, pd.DatetimeIndex):
                df.index = pd.to_datetime(df.index)
            
            # Filter signals within the past 2 days
            recent_signals = df[df.index >= two_days_ago]
            triggered_buy = bool(recent_signals['buy_signal'].sum() > 0)
            signal_status[timeframe] = triggered_buy
            if triggered_buy:
                total_triggered += 1
        signal_status['Good_buying_option'] = total_triggered >= 3
        return signal_status

    def check_buy_signals_past_week(self, resampled_data):
        """
        For each day in the past week, check if any buy signal was triggered
        across all timeframes.
        """
        past_week_dates = get_past_month_dates()  # ['2025-01-21', ..., '2025-01-27']

        report_df = pd.DataFrame(0, index=past_week_dates, columns=resampled_data.keys())
        
        for label, df in resampled_data.items():
            # Filter buy signals within the past week
            df_buy_signals = df[df['buy_signal'] == 1]
            for timestamp in df_buy_signals.index:
                date_str = timestamp.strftime('%Y-%m-%d')
                if date_str in report_df.index:
                    report_df.at[date_str, label] = 1  # Mark as 1 if signal exists
        report_df['Good_buying_option'] = (report_df.sum(axis=1) >= 3).astype(int)
        # Display the report
        print("\nDetailed Buy Signal Report for the Past Week:")
        print(report_df)


    



    def compute_vegas_channel_and_signel(self, data, visualize=True):
        historical_data = data.copy()
        # A:EMA(HIGH,24),COLORBLUE;
        # B:EMA(LOW,23),COLORBLUE;
        # A1:EMA(H,89),COLORORANGE;
        # B1:EMA(L,90),COLORORANGE;
        alpha1 = compute_ema(historical_data, 24, 'h')
        beta1 = compute_ema(historical_data, 23, 'l')
        alpha2 = compute_ema(historical_data, 89, 'h')
        beta2 = compute_ema(historical_data, 90, 'l')

        # Add EMAs to the DataFrame for easy plotting
        historical_data['alpha1'] = alpha1
        historical_data['beta1'] = beta1
        historical_data['alpha2'] = alpha2
        historical_data['beta2'] = beta2

        # compute lingfeng metric on buy and sell signal
        kline_data = list(zip(
            historical_data['o'],  # Open
            historical_data['c'],  # Close
            historical_data['h'],  # High
            historical_data['l']   # Low
        ))

        # 2. Call calc_buy_sell_signals function
        buy_signals, sell_signals = calc_buy_sell_signals(kline_data, s=12, p=26, m=9)
        historical_data['buy_signal'] = buy_signals
        historical_data['sell_signal'] = sell_signals

        if visualize:
            self.plot_vegas_channel(historical_data)
        return historical_data


    def plot_vegas_channel(self, df: pd.DataFrame):
        plt.figure(figsize=(14, 7))
        
        # Plot Closing Price
        plt.plot(df.index, df['c'], label='Closing Price', color='black', linewidth=2)
        
        # Plot EMAs
        plt.plot(df.index, df['alpha1'], label='alpha1', color='blue', linestyle='--')
        plt.plot(df.index, df['beta1'], label='beta1', color='blue', linestyle='--')
        plt.plot(df.index, df['alpha2'], label='alpha2', color='orange', linestyle='-.')
        plt.plot(df.index, df['beta2'], label='beta2', color='orange', linestyle='-.')

        buy_dates = df.index[df['buy_signal'] == 1]
        buy_prices = df['c'][df['buy_signal'] == 1]
        plt.scatter(buy_dates, buy_prices, marker='^', color='green', label='Buy Signal', s=100)

        # Plot Sell Signals
        sell_dates = df.index[df['sell_signal'] == 1]
        sell_prices = df['c'][df['sell_signal'] == 1]
        plt.scatter(sell_dates, sell_prices, marker='v', color='red', label='Sell Signal', s=100)


        # Formatting the Plot
        plt.title(f"{self.stock_symbol} Price with Vegas Channels and Buy/Sell Signals")
        plt.xlabel("Date")
        plt.ylabel("Price")
        plt.legend()
        plt.grid(True)
        plt.tight_layout()
        plt.show()



if __name__ == "__main__":
    symbol = "AAPL"
    engine = FinnhubEngine()
    detector = BuySignalDetector(symbol, engine)
    detector.multi_resolution_signal()
    