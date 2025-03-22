from mmengine import dump, load
import matplotlib.pyplot as plt

import numpy as np
import pandas as pd

from livermore.misc import get_readable_time, get_ny_time, time_to_seconds, get_last_time, process_database_results, plot_stock_candles, plot_multiple_stock_candles
from livermore.modeling.volatility_estimation import realized_volatility, parkinson_volatility, garman_klass_volatility, yang_zhang_volatility
from livermore.signal_utils import compute_vegas_channel_and_signal
from livermore.finnhub_engine import FinnhubEngine
from livermore import livermore_root


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
    print(candles_1d.keys())
    
    print(get_readable_time(candles_1d["t"][-1]))
    print(candles_1d["c"][-20:])
    rv_result = yang_zhang_volatility(candles_1d)
    rv_result = rv_result.tolist()
    
    # Create figure and axis
    plt.figure(figsize=(12, 6))
    
    # Plot RV with dates
    dates = [get_readable_time(t) for t in candles_1d["t"]]
    plt.plot(dates, rv_result, label='Yang-Zhang Volatility', color='blue', linewidth=2)
    
    # Customize the plot
    plt.title(f'{symbol} Realized Volatility', fontsize=14)
    plt.xlabel('Date', fontsize=12)
    plt.ylabel('Volatility', fontsize=12)
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.xticks(rotation=45)
    plt.legend()
    
    # Adjust layout to prevent label cutoff
    plt.tight_layout()
    plt.show()
    
    # ... rest of the code ...    candles = engine.query_candles_of_different_resolutions(symbol, num=200, last_time=None)
    print(get_readable_time(candles_1d["t"][-1]))
    print(candles_1d["c"][-20:])
    rv_result = yang_zhang_volatility(candles_1d)
    rv_result = rv_result.tolist()
    
    # Create figure and axis
    plt.figure(figsize=(12, 6))
    
    # Plot RV with dates
    dates = [get_readable_time(t) for t in candles_1d["t"]]
    plt.plot(dates, rv_result, label='Yang-Zhang Volatility', color='blue', linewidth=2)
    
    # Customize the plot
    plt.title(f'{symbol} Realized Volatility', fontsize=14)
    plt.xlabel('Date', fontsize=12)
    plt.ylabel('Volatility', fontsize=12)
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.xticks(rotation=45)
    plt.legend()
    
    # Adjust layout to prevent label cutoff
    plt.tight_layout()
    plt.show()

