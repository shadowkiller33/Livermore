from mmengine import dump, load

import numpy as np
import pandas as pd

from livermore.misc import get_readable_time, get_ny_time, time_to_seconds, get_last_time, process_database_results, plot_stock_candles, plot_multiple_stock_candles
from livermore.stock_candle_database import stock_candle_db
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
    
    symbol = "NVDA"
    
    candles = engine.query_candles_of_different_resolutions(symbol, num=200, last_time=None)
    print(get_readable_time(candles["1d"]["t"][-1]))
    rv_result = engine.calculate_realized_volatility(candles["1d"]["c"])
    print(rv_result.tail(30))

