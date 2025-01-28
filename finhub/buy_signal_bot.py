import time
import pandas as pd
import numpy as np
from engine import FinnhubEngine
from metrics.ema import compute_ema
from metrics.lingfeng import calc_buy_sell_signals
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import pytz
LOOKBACK_COUNT=180 # lookback days



def ensure_timezone_aware(df):
    """
    Ensures that the DataFrame's index is timezone-aware.
    If it's timezone-naive, localizes it to UTC.
    
    Parameters:
    - df (pd.DataFrame): DataFrame with a datetime index.
    
    Returns:
    - pd.DataFrame: Timezone-aware DataFrame.
    """
    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index)
    
    if df.index.tz is None:
        # Assuming the original data is in UTC; adjust if different
        df = df.tz_localize('UTC')
    
    return df


def resample_kline_data(df, timeframe):
    """
    Resample kline data to a higher timeframe starting from market open (9:30 AM ET) for each trading day
    and ensure the last tick is at market close (4:00 PM ET) for each day.

    Parameters:
    - df (pd.DataFrame): Original kline data with a timezone-aware datetime index in US/Eastern.
    - timeframe (str): Resampling timeframe (e.g., '1H', '2H', '3H', '4H').

    Returns:
    - pd.DataFrame: Resampled kline data with the last tick at market close for each trading day.
    """
    # Step 1: Ensure the DataFrame index is a timezone-aware DatetimeIndex in US/Eastern
    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index)
    
    if df.index.tz is None:
        df = df.tz_localize('US/Eastern')
    else:
        df = df.tz_convert('US/Eastern')

    # Step 2: Add a 'date' column for grouping
    df['date'] = df.index.date

    # Initialize a list to hold resampled DataFrames for each day
    resampled_list = []

    # Group data by each trading day
    grouped = df.groupby('date')

    eastern = pytz.timezone('US/Eastern')
    now_eastern = datetime.now(eastern)
    today_date = now_eastern.date()
    for trading_date, group in grouped:
        # Define start and end times for the current trading day in ET
        start_time = pd.Timestamp(f"{trading_date} 09:30:00", tz='US/Eastern')
        end_time = pd.Timestamp(f"{trading_date} 15:30:00", tz='US/Eastern')

        # Filter data within trading hours for the current day
        df_trading = group[(group.index >= start_time) & (group.index <= end_time)]

        if df_trading.empty:
            continue  # Skip days with no trading data

        # Resample with alignment starting at 09:30 ET
        
        resampled = df_trading.resample(timeframe, origin=start_time).agg({
            'o': 'first',   # Open
            'c': 'last',    # Close
            'h': 'max',     # High
            'l': 'min',     # Low
            'v': 'sum'       # Volume
        }).dropna()

        # Remove the temporary 'date' column
        resampled = resampled.drop(columns=['date'], errors='ignore')

        # Append the resampled data for the current day to the list
        resampled_list.append(resampled)

    if not resampled_list:
        print("No trading data available for the specified resampling.")
        return pd.DataFrame()  # Return an empty DataFrame if no data is present

    # Concatenate all resampled daily DataFrames into a single DataFrame
    resampled_df = pd.concat(resampled_list)
    
    # Optional: Sort the resampled DataFrame by datetime index
    resampled_df = resampled_df.sort_index()

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


def remove_first_entry_each_day(df):
    """
    Removes the first entry (e.g., 14:30 UTC) for each trading day in the DataFrame.

    Parameters:
    - df (pd.DataFrame): DataFrame with a timezone-aware datetime index in UTC.

    Returns:
    - pd.DataFrame: DataFrame with the first entry of each trading day removed.
    """
    # Ensure the DataFrame index is a timezone-aware DatetimeIndex in UTC
    if not isinstance(df.index, pd.DatetimeIndex):
        raise TypeError("The DataFrame index must be a pandas DatetimeIndex.")
    
    if df.index.tz is None:
        raise ValueError("The DataFrame index must be timezone-aware (UTC).")
    
    # Sort the DataFrame by index to ensure chronological order
    df_sorted = df.sort_index()
    
    # Group by the date part of the index
    grouped = df_sorted.groupby(df_sorted.index.date)
    
    # Identify the first entry of each group (i.e., each trading day)
    first_entries = grouped.head(1).index
    
    # Drop the first entries from the DataFrame
    df_filtered = df_sorted.drop(first_entries)
    
    return df_filtered


class BuySignalDetector:
    def __init__(self, stock_symbol, engine: FinnhubEngine):
        self.engine = engine
        self.stock_symbol = stock_symbol    
        self.visual = True # disable this when serving in real-time


    def multi_resolution_signal(self):
        lookback_four_halfhour = LOOKBACK_COUNT * 24 * 60 // 30
        halfhour_data = self.engine.get_historical_prices(self.stock_symbol, 
                                                    resolution='30', 
                                                    count=lookback_four_halfhour,
                                                    )


        halfhour_filtered = remove_first_entry_each_day(halfhour_data)
        # halfhour without first row to compute signal
        halfhour_signal = self.compute_vegas_channel_and_signel(halfhour_filtered, visualize=False)

        day_data = self.engine.get_historical_prices(self.stock_symbol, 
                                                            resolution='D', 
                                                            count=LOOKBACK_COUNT,
                                                            )

        day_signal = self.compute_vegas_channel_and_signel(day_data, visualize=False)
  
        onehour_historical_data = resample_kline_data(halfhour_data, '1h')   
        twohour_historical_data = resample_kline_data(halfhour_data, '2h')
        threehour_historical_data = resample_kline_data(halfhour_data, '3h')
        fourhour_historical_data = resample_kline_data(halfhour_data, '4h')
        
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
    

    def check_buy_signals_past_two_days(self, resampled_data):
        # Define the timezone (US/Eastern in this case)
        eastern = pytz.timezone('US/Eastern')

        # Get the current time in US/Eastern
        now_eastern = datetime.now(eastern)

        # Calculate two days ago in US/Eastern timezone
        two_days_ago = now_eastern - timedelta(days=2)

        signal_status = {}
        total_triggered = 0
        for timeframe, df in resampled_data.items():
            # Ensure the DataFrame index is datetime and timezone-aware
            if not isinstance(df.index, pd.DatetimeIndex):
                df.index = pd.to_datetime(df.index)
            
            if df.index.tz is None:
                # Assuming the DataFrame's timestamps are in US/Eastern if tz-naive
                df = df.tz_localize(eastern)
            else:
                # Ensure the DataFrame's timezone matches 'eastern'
                df = df.tz_convert(eastern)

            # Filter signals within the past 2 days
            recent_signals = df[df.index >= two_days_ago]
            # print(timeframe, recent_signals)
            triggered_buy = bool(recent_signals['buy_signal'].sum() > 0)
            signal_status[timeframe] = triggered_buy
            if triggered_buy:
                total_triggered += 1

        signal_status['Good_buying_option'] = total_triggered >= 3
        # print(resampled_data)
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
    stocks = {
        "semi_conductor": ["NVDA", "AMD", "SMTC", "SOXX", "ARM", "AMAT", "LRCX", "QCOM", "INTC", "TSM", "ASML", "ALAB", "AVGO", "MU"],
        "crypto": ["IBIT", "BTDR", "BTBT", "HUT", "COIN", "RIOT", "CLSK", "BTCT", "MSTR", "MARA"],
        "big_tech":["CRM", "MDB", "ZM", "NFLX", "SNOW", "PANW", "NVDA", "ORCL", "TSLL", "TSLA", "MSFT", "AMZN", "META", "AAPL", "GOOG"],
        "ai_software": ["TEM", "LUNR", "SOUN", "AFRM", "MRVL", "MNDY", "ASTS", "AISP", "INOD", "APLD", "NNOX", "ZETA", "AI", "BBAI"],
        "spy_qqq_iwm": ["IWM", "SPY", "QQQ"],
        "finance": ["DPST", "GS", "V", "WFC", "PYPL", "MS", "JPM", "BAC", "MA", "AXP"],
        "bio_med": ["WBA", "JNJ", "UNH", "FDMT", "DNLI", "BHVN", "AURA", "WAY", "ARCT", "HIMS"],
        "vol": ["UVXY"],
        "tlt_tmf": ["TLT", "TMF"],
        "energy": ["CAT", "CEG", "LTBR", "LNG", "GEV", "SMR", "RUN", "ARRY", "VRT", "VST", "FSLR", "KOLD", "OKLO", "XOM", "OXY"],
    }
    engine = FinnhubEngine()
    # NBIS, VIX data cannot be retrieved
    for sector, symbols in stocks.items():
        if sector != "energy":
            continue
        
        for symbol in symbols:
            print(symbol)
            detector = BuySignalDetector(symbol, engine)
            signal = detector.multi_resolution_signal()
            if any(signal.values()):
                print(f"Buy Signal Detected for {symbol}!")
                print(signal)
            time.sleep(10)
