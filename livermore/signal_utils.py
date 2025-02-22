import time
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import pytz

from datetime import datetime, timedelta

from livermore.misc import create_mpf_style_df, filter_market_time
from livermore.metrics.lingfeng import calc_buy_sell_signals


LOOKBACK_COUNT=180 # lookback days


def compute_ema(df, lookback, price_column="c"):
    if price_column not in df.columns:
        raise ValueError(f"Column '{price_column}' does not exist in the DataFrame.")
    ema = df[price_column].ewm(span=lookback, adjust=False).mean()
    return ema


def compute_vegas_channel_and_signal(data, market_time_only=True):
    if isinstance(data, dict):
        data = create_mpf_style_df(data)
    if market_time_only:
        data = filter_market_time(data)
    for col in ["Open", "Close", "High", "Low", "Date"]:
        assert col in data.columns, f"Column '{col}' not found in the DataFrame."
    
    alpha1 = compute_ema(data, 24, "High")
    beta1 = compute_ema(data, 23, "Low")
    
    alpha2 = compute_ema(data, 89, "High")
    beta2 = compute_ema(data, 90, "Low")
    
    # compute lingfeng metric on buy and sell signal
    kline_data = list(zip(
        data["Open"],  # Open
        data["Close"],  # Close
        data["High"],  # High
        data["Low"]   # Low
    ))
    
    buy_signals, sell_signals = calc_buy_sell_signals(kline_data, s=12, p=26, m=9)
    return {
        "alpha1": alpha1,
        "beta1": beta1,
        "alpha2": alpha2,
        "beta2": beta2,
        "buy_signal": buy_signals,
        "sell_signal": sell_signals,
    }


if __name__ == "__main__":
    pass


