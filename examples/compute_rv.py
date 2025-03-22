from mmengine import dump, load
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

import numpy as np
import pandas as pd

from livermore.misc import get_readable_time, get_ny_time, time_to_seconds, get_last_time, process_database_results, plot_stock_candles, plot_multiple_stock_candles
from livermore.modeling.volatility_estimation import realized_volatility, parkinson_volatility, garman_klass_volatility, yang_zhang_volatility
from livermore.signal_utils import compute_vegas_channel_and_signal
from livermore.finnhub_engine import FinnhubEngine
from livermore import livermore_root


def plot_rv(candles_1d, rv_result, name, symbol):
    fig, ax1 = plt.subplots(figsize=(12, 6))
    dates = pd.to_datetime([get_readable_time(_) for _ in candles_1d["t"]])
    rv_result = np.array(rv_result) * 100
    
    line1 = ax1.plot(dates, rv_result, label=name, color='#FF6961', linewidth=2)
    ax1.set_xlabel('Date', fontsize=12)
    ax1.set_ylabel('Volatility(%)', fontsize=12)
    
    # Create a second y-axis for price
    ax2 = ax1.twinx()
    line2 = ax2.plot(dates, candles_1d["c"], label='Price', color='#00BFFF', linewidth=2)
    ax2.set_ylabel('Price', fontsize=12)
    
    plt.title(f'{symbol} - Volatility', fontsize=14)
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.xticks(rotation=45)
    ax = plt.gca()
    ax.xaxis.set_major_locator(mdates.MonthLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))

    lines = line1 + line2
    labels = [l.get_label() for l in lines]
    fig.legend(lines, labels, loc='upper center', bbox_to_anchor=(0.5, 0.95), ncol=2)

    # Adjust layout to prevent label cutoff
    plt.tight_layout()
    plt.savefig("volatility_plot.pdf")


if __name__ == "__main__":
    formatted_date = "20250206"
    engine = FinnhubEngine(api_key="cu9bivpr01qnf5nmlh8gcu9bivpr01qnf5nmlh90")
    
    symbols_by_sectors = load(str(livermore_root / 'data/coarse_selection.json'))
    currency_map = load(str(livermore_root / f'data/currencies_map_{formatted_date}.json'))
    company_profiles = load(str(livermore_root / f'data/company_profiles_{formatted_date}.json'))
    opportunities = load(str(livermore_root / 'data/existing_opportunities.json'))
    
    symbols = []
    for name, value in symbols_by_sectors.items():
        symbols += value
    symbols = sorted(symbols, key=lambda x: 1E20 if x not in company_profiles else company_profiles[x]["marketCapitalization"] * currency_map[company_profiles[x]["currency"]] / 1000, reverse=True)
    
    symbol = "SPY"
    candles_1d = engine.query_candles_of_different_resolutions(symbol, resolutions="1d", num=200)["1d"]

    rv_result = yang_zhang_volatility(candles_1d)
    name = "Yang-Zhang Volatility"
    
    # rv_result = realized_volatility(candles_1d)
    # name = "Realized Volatility"
    
    rv_result = rv_result.tolist()
    plot_rv(candles_1d, rv_result, name, symbol)
