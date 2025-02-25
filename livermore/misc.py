import pytz
# import mplfinance as mpf
import time
import pandas as pd
import numpy as np
import matplotlib.ticker as ticker
import io
from PIL import Image

from copy import deepcopy

from matplotlib import pyplot as plt
from matplotlib.patches import Rectangle
from matplotlib.ticker import MaxNLocator
    
from mmengine import load, dump
from IPython import embed  
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta


def get_ny_time(timestamp=None):
    if not isinstance(timestamp, datetime):
        if timestamp is None:
            timestamp = int(time.time())
        timestamp = datetime.fromtimestamp(timestamp).replace(second=0, microsecond=0)
    ny_timezone = pytz.timezone('America/New_York')
    return timestamp.astimezone(ny_timezone)


def get_begining_of_day(timestamp=None):
    if timestamp is None:
        timestamp = time.time()
    now = get_ny_time(timestamp)
    begining_of_day = now.replace(hour=9, minute=30)
    if begining_of_day > now:
        begining_of_day -= pd.Timedelta("1d")
    return begining_of_day


def get_last_time(unit="1m"):
    # Get the begining of a unit before the current time, use 9:30 am as the start of the day
    now = time.time()
    now = get_ny_time(now)
    begining_of_day = get_begining_of_day(now)
    
    day_begin = now.replace(hour=9, minute=30)
    day_end = now.replace(hour=16, minute=0)
    delta = now - begining_of_day
    seconds = delta.total_seconds()
    
    # print(now, begining_of_day)
    # print(delta)
    # print(delta.hour, delta.minute)
    # exit(0)
    
    if unit.endswith("m"):
        minutes = seconds // 60
        interval = int(unit[:-1])
        minutes = (minutes // interval) * interval
        return begining_of_day + pd.Timedelta(f"{minutes - interval}m") 
    elif unit.endswith("h"):
        hours = seconds // 3600
        interval = int(unit[:-1])
        hours = (hours // interval) * interval
        return begining_of_day + pd.Timedelta(f"{hours - interval}h") 
    else:
        # Compute the begining of the previous day
        assert unit == "1d"
        if now.time() > day_end.time() or now.time() < day_begin.time():
            return begining_of_day
        else:
            return begining_of_day - pd.Timedelta("1d")


def get_readable_time(timestamp):
    if not isinstance(timestamp, datetime):
        timestamp = datetime.fromtimestamp(timestamp)
    
    ny_timezone = pytz.timezone('America/New_York')
    ny_time = timestamp.astimezone(ny_timezone)
    return ny_time.strftime('%Y-%m-%d %H:%M')


def time_to_seconds(time_str):
    unit_map = {"d": "days", "h": "hours", "m": "minutes", "s": "seconds"}
    num, unit = eval(time_str[:-1]), time_str[-1].lower()
    if unit in unit_map:
        return timedelta(**{unit_map[unit]: num}).total_seconds()
    return None


def is_in_working_time(timestamp):
    if not isinstance(timestamp, datetime):
        timestamp = datetime.fromtimestamp(timestamp)
    start_time = datetime.time(9, 30)
    end_time = datetime.time(16, 0)
    current_time = dt.time()
    return start_time <= current_time <= end_time


def create_mpf_style_df(data):
    data = {
        "Open": data["o"],
        "High": data["h"],
        "Low": data["l"],
        "Close": data["c"],
        "Volume": data["v"],
        "Date": [get_ny_time(_) for _ in data["t"]]
    }
    df = pd.DataFrame(data)
    df = df.sort_values(by='Date', ascending=True)
    return df


def get_good_date(df):
    str_format = []
    if df["Date"].dt.year.nunique() > 1:
        str_format.append("%y")
        if df["Date"].dt.day.nunique() > 1:
            str_format += ["%m", "%d"]
        elif df["Date"].dt.month.nunique() > 1:
            str_format.append("%m")
    elif df["Date"].dt.month.nunique() > 1:
        str_format.append("%m")
        if df["Date"].dt.day.nunique() > 1:
            str_format += ["%d"]
    elif df["Date"].dt.day.nunique() > 1:
        str_format = ["%m", "%d"]
    str_format = "-".join(str_format)
    
    if not (df["Date"].dt.hour.nunique() == 1 and df["Date"].dt.minute.nunique() == 1):
        str_format += " %H:%M"
    date = df["Date"].dt.strftime(str_format)
    return date


def filter_market_time(df):
    if not (df["Date"].dt.hour.nunique() == 1 and df["Date"].dt.minute.nunique() == 1): # Day-level Data 
        start_time = pd.to_datetime('09:30:00').time()
        end_time = pd.to_datetime('16:00:00').time()
        df = df[
            (df['Date'].dt.time >= start_time) &
            (df['Date'].dt.time < end_time)
        ]
    return df


def process_database_results(dataset):
    from collections import defaultdict
    ret = defaultdict(list)
    for item in dataset:
        item = {
            "o": item.open_price,
            "c": item.close_price,
            "h": item.high_price,
            "l": item.low_price,
            "t": item.timestamp,
            "v": item.volume
        }
        for key in ["o", "c", "h", "l", "t", "v"]:
            ret[key].append(item[key])
    return dict(ret)


def plot_stock_candles(candles, symbol, kline_type="", signals=None, filename=None, figsize=(16, 9), time_range=None, max_num=100, market_time_only=True, output_ax=None, show_legend=True):
    df = create_mpf_style_df(candles)
    if market_time_only:
        df = filter_market_time(df)
    
    if time_range:
        df = df[(df["Date"] >= time_range[0]) & (df["Date"] <= time_range[1])]
    if signals is not None:
        assert len(signals["alpha1"]) == len(df), f"{len(signals['alpha1'])} != {len(df)}"
    
    if max_num is not None:
        df = df.tail(max_num)
        if signals is not None:
            signals = deepcopy(signals)
            for key in ["alpha1", "beta1", "alpha2", "beta2", "buy_signal", "sell_signal"]:
                signals[key] = signals[key][-max_num:]
            # print(len(signals["buy_signal"]), signals["buy_signal"])
    
    st_time, end_time = df["Date"].min(), df["Date"].max()
    colors = ["#63C582" if close >= open_ else "#EA434F" for open_, close in zip(df["Open"], df["Close"])]
    if output_ax is not None:
        ax = output_ax
    else:
        fig, ax = plt.subplots(figsize=figsize)
    width = 0.8
    for i in range(len(df)):
        item = df.iloc[i].to_dict()
        center = (item["Open"] + item["Close"]) / 2
        side_length = abs(item["Open"] - item["Close"]) / 2
        if item["Open"] > item["Close"]:
            square = Rectangle((i - width / 2, center), width, side_length, fill=False, edgecolor=colors[i])
        else:
            square = Rectangle((i - width / 2, center), width, side_length, edgecolor=colors[i], facecolor=colors[i])
        ax.add_patch(square)
        ax.plot([i, i], [item["Low"], item["High"]], color=colors[i], linewidth=1)
    
    date = get_good_date(df)
    ax.set_xticks(range(len(df)))
    ax.set_xticklabels(date, rotation=90)
    
    if signals is not None:
        ax.plot(range(len(df)), signals['alpha1'], color='blue', linestyle='-')
        ax.plot(range(len(df)), signals['beta1'], color='blue', linestyle='-', label="Fast")
        
        ax.plot(range(len(df)), signals['alpha2'], color='orange', linestyle='-')
        ax.plot(range(len(df)), signals['beta2'], color='orange', linestyle='-', label="Slow")
        
        indices = np.where(signals['buy_signal'])[0]
        buy_prices = df.iloc[indices]["Low"] - (df.iloc[indices]["Low"] * 0.05).clip(upper=3, lower=1)
        ax.scatter(indices, buy_prices, marker='^', color='red', label='Buy', s=100)
        
        indices = np.where(signals['sell_signal'])[0]
        buy_prices = df.iloc[indices]["High"] + (df.iloc[indices]["High"] * 0.05).clip(upper=3, lower=1)
        ax.scatter(indices, buy_prices, marker='v', color='green', label='Sell', s=100)

    ax.xaxis.set_major_locator(MaxNLocator(integer=True, prune='both', nbins=50))
    if output_ax is None:
        ax.set_title(f'{symbol} | {date.iloc[0]} - {date.iloc[-1]} | {kline_type} K-Line', fontweight='bold', fontsize=20)
        ax.set_xlabel('Date', fontweight='bold', fontsize=20)
        ax.set_ylabel('Price', fontweight='bold', fontsize=20)
    else:
        ax.set_title(kline_type, fontweight='bold', fontsize=14)
    
    ax.tick_params(axis="x", labelsize=14) 
    ax.tick_params(axis="y", labelsize=14) 
    
    ax.set_xlim(-1, len(df))
    if show_legend:
        ax.legend(fontsize=14)
    ret = None
    if output_ax is None:
        fig.tight_layout()
        if filename:
            fig.savefig(filename, format="png", dpi=100, bbox_inches="tight")
        else:
            buffer = io.BytesIO()
            fig.savefig(buffer, format="png", dpi=100, bbox_inches="tight")
            buffer.seek(0)
            ret = buffer
        plt.close(fig)
        plt.cla()
    return ret


def plot_multiple_stock_candles(candles, symbol, filename=None, figsize=(30, 12), time_range=None, max_num=100, market_time_only=True):
    from livermore.signal_utils import compute_vegas_channel_and_signal
    fig, axes = plt.subplots(2, 3, figsize=figsize)
    axes = axes.flatten()
    # print(axes.shape)
    data = candles["1h"]
    # print(data.keys())
    st_time, end_time = data["t"][0], data["t"][-1]
    fig.suptitle(f'{symbol} | {get_readable_time(st_time)} - {get_readable_time(end_time)}', fontweight='bold', fontsize=20)
    
    for i, resolution in enumerate(["30m", "1h", "2h", "3h", "4h", "1d"]):
        # print(resolution, len(candles[resolution]["t"]))
        signals = compute_vegas_channel_and_signal(candles[resolution])
        plot_stock_candles(candles[resolution], symbol, resolution, signals, filename, figsize, time_range, max_num, market_time_only, output_ax=axes[i], show_legend=i==0)
    fig.tight_layout()
    ret = None
    if filename:
        fig.savefig(filename, format="png", dpi=100, bbox_inches="tight")
    else:
        buffer = io.BytesIO()
        fig.savefig(buffer, format="png", dpi=100, bbox_inches="tight")
        buffer.seek(0)
        ret = buffer
    plt.close(fig)
    plt.cla()
    return ret


def analyze_option_chain(symbol, output_path='temp_plot.png'):
    engine = FinnhubEngine()
    
    # Retrieve the option chain data from Finnhub API.
    try:
        # option_chain_data = engine.get_option_chain(symbol, expiration)
        option_chain_data = engine.get_option_chain(symbol)
    except Exception as e:
        print(f"Error retrieving option chain data: {e}")
        return

    # Plot the next three option chain distributions
    chains_to_plot = option_chain_data[:3]
    num_chains = len(chains_to_plot)
    
    # Create a figure with one subplot per option chain.
    fig, axs = plt.subplots(num_chains, 1, figsize=(12, 6 * num_chains))
    if num_chains == 1:
        axs = [axs]
    
    for idx, chain in enumerate(chains_to_plot):
        ax = axs[idx]
        
        # Extract overall stats for display in the subplot title.
        overall_call_volume = chain.get('callVolume')
        overall_put_volume = chain.get('putVolume')
        overall_volume_ratio = chain.get('putCallVolumeRatio')
        overall_call_open_interest = chain.get('callOpenInterest')
        overall_put_open_interest = chain.get('putOpenInterest')
        overall_open_interest_ratio = chain.get('putCallOpenInterestRatio')
        chain_expiration = chain.get('expirationDate')
        
        # Extract the options lists for calls and puts.
        try:
            call_list = chain['options']['CALL']
            put_list = chain['options']['PUT']
        except KeyError as e:
            print(f"Missing options data in chain {idx}: {e}")
            continue

        # Convert lists to DataFrames.
        call_df = pd.DataFrame(call_list)
        put_df = pd.DataFrame(put_list)

        # Ensure 'strike' and 'volume' columns are numeric.
        for col in ['strike', 'volume']:
            if col in call_df.columns:
                call_df[col] = pd.to_numeric(call_df[col], errors='coerce')
            if col in put_df.columns:
                put_df[col] = pd.to_numeric(put_df[col], errors='coerce')

        # Drop rows with missing values in 'strike' or 'volume' and sort by strike.
        call_df.dropna(subset=['strike', 'volume'], inplace=True)
        put_df.dropna(subset=['strike', 'volume'], inplace=True)
        call_df.sort_values('strike', inplace=True)
        put_df.sort_values('strike', inplace=True)

        # Filter out strikes with very small volume.
        call_threshold = 0.05 * call_df['volume'].max() if not call_df.empty else 0
        put_threshold = 0.05 * put_df['volume'].max() if not put_df.empty else 0
        call_df_filtered = call_df[call_df['volume'] >= call_threshold].copy()
        put_df_filtered = put_df[put_df['volume'] >= put_threshold].copy()

        # Compute weighted mean strike price for calls and puts.
        if call_df_filtered['volume'].sum() > 0:
            mean_strike_call = (call_df_filtered['strike'] * call_df_filtered['volume']).sum() / call_df_filtered['volume'].sum()
        else:
            mean_strike_call = np.nan

        if put_df_filtered['volume'].sum() > 0:
            mean_strike_put = (put_df_filtered['strike'] * put_df_filtered['volume']).sum() / put_df_filtered['volume'].sum()
        else:
            mean_strike_put = np.nan

        print(f"Chain {idx+1} (Expiration {chain_expiration}):")
        print(f"  Weighted mean strike (Call): {mean_strike_call:.2f}")
        print(f"  Weighted mean strike (Put): {mean_strike_put:.2f}")

        # Merge the filtered DataFrames on 'strike'.
        merged_df = pd.merge(call_df_filtered[['strike', 'volume']], 
                             put_df_filtered[['strike', 'volume']], 
                             on='strike', 
                             how='outer', 
                             suffixes=('_call', '_put'))
        merged_df.fillna(0, inplace=True)
        merged_df.sort_values('strike', inplace=True)
        
        # Plot the call and put volumes as grouped bar charts.
        x = merged_df['strike'].values
        width = 0.4  # Width of each bar
        
        ax.bar(x - width/2, merged_df['volume_call'], width=width, color='blue', alpha=0.7, label='Call Volume')
        ax.bar(x + width/2, merged_df['volume_put'], width=width, color='red', alpha=0.7, label='Put Volume')
        
        ax.set_xlabel("Strike Price")
        ax.set_ylabel("Volume")
        # Format the call/put ratio as a percentage with 1 decimal.
        vol_ratio_percent = overall_volume_ratio * 100 if overall_volume_ratio is not None else 0
        overall_open_interest_ratio = overall_open_interest_ratio * 100 if overall_open_interest_ratio is not None else 0
        title = (f"{symbol} Option Volume Distribution\nExpiration: {chain_expiration}\n"
                 f"Overall Vol Ratio (Put/Call): {vol_ratio_percent:.1f}%, "
                 f"Open Interest Ratio (Put/Call): {overall_open_interest_ratio:.1f}%")
        ax.set_title(title)
        
        # Dynamically set x-ticks so that they are not too wide or narrow.
        if not merged_df.empty:
            min_strike = merged_df['strike'].min()
            max_strike = merged_df['strike'].max()
            # Compute a reasonable tick step (about 10 ticks)
            tick_range = max_strike - min_strike
            tick_step = max(1, np.ceil(tick_range / 10))
            xticks = np.arange(min_strike, max_strike + tick_step, tick_step)
            ax.set_xticks(xticks)
            ax.set_xticklabels([str(int(tick)) for tick in xticks], rotation=45, ha='right')
        else:
            ax.set_xticks([])

        # Mark the weighted mean strike prices with vertical lines.
        if not np.isnan(mean_strike_call):
            ax.axvline(mean_strike_call, color='blue', linestyle='--', linewidth=1.5,
                       label=f'Call Mean Strike ({mean_strike_call:.1f})')
        if not np.isnan(mean_strike_put):
            ax.axvline(mean_strike_put, color='red', linestyle='--', linewidth=1.5,
                       label=f'Put Mean Strike ({mean_strike_put:.1f})')
        
        # Instead of arrow annotations, simply display text for the max call and put strike.
        if not merged_df.empty and merged_df['volume_call'].max() > 0:
            idx_max_call = merged_df['volume_call'].idxmax()
            strike_max_call = merged_df.loc[idx_max_call, 'strike']
            # Place the text in the top-left corner of the subplot.
            ax.text(0.02, 0.95, f"Max Call Strike: {strike_max_call}",
                    transform=ax.transAxes, ha='left', va='top', color='blue', fontsize=10)
        
        if not merged_df.empty and merged_df['volume_put'].max() > 0:
            idx_max_put = merged_df['volume_put'].idxmax()
            strike_max_put = merged_df.loc[idx_max_put, 'strike']
            # Place the text in the top-right corner of the subplot.
            ax.text(0.98, 0.95, f"Max Put Strike: {strike_max_put}",
                    transform=ax.transAxes, ha='right', va='top', color='red', fontsize=10)
        
        ax.legend()

    fig.tight_layout()
    # plt.show()
    if output_path is not None:
        fig.savefig(output_path, dpi=300)
        fig.close()
        return output_path
    else:
        buf = io.BytesIO()
        fig.savefig(buf, format="png", bbox_inches="tight")
        fig.close()
        buf.seek(0) 
        image = Image.open(buf)
        return image
