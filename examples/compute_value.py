from mmengine import dump, load
from collections import defaultdict
from pathlib import Path

from livermore.misc import get_readable_time, get_ny_time, time_to_seconds, get_last_time, process_database_results, plot_stock_candles, plot_multiple_stock_candles
from livermore.signal_utils import compute_vegas_channel_and_signal
from livermore import livermore_root
from livermore.finnhub_engine import FinnhubEngine
import time


__this_folder__ = Path(__file__).parent


if __name__ == "__main__":
    # sectors = load(str(livermore_root / 'data/etf_by_sectors.json'))["sectors"]
    engine = FinnhubEngine(api_key="cu9bivpr01qnf5nmlh8gcu9bivpr01qnf5nmlh90")
    # candles, symbol, kline_type="", signals=None, filename=None, figsize=(16, 9), time_range=None, max_num=100, market_time_only=True, output_ax=None, show_legend=True
    
    
    symbol = "SPY"
    candles = engine.query_candles_of_different_resolutions(symbol, num=num, resolutions=["1d"])["1d"]
    print(len(candles), len(candles["t"]), get_readable_time(candles["t"][0]), get_readable_time(candles["t"][-1]))
    plot_stock_candles(candles, symbol, filename=__this_folder__ / "imgs/spy.png", max_num=None)
    
    
    """
    symbol = "SPY"
    candles = engine.query_candles_of_different_resolutions(symbol, num=num, resolutions=["1d"])["1d"]
    print(len(candles), len(candles["t"]), get_readable_time(candles["t"][0]), get_readable_time(candles["t"][-1]))
    plot_stock_candles(candles, symbol, filename=__this_folder__ / "imgs/spy.png", max_num=None)
    
    symbol = "GLD"
    candles = engine.query_candles_of_different_resolutions(symbol, num=num, resolutions=["1d"])["1d"]
    print(len(candles), len(candles["t"]), get_readable_time(candles["t"][0]), get_readable_time(candles["t"][-1]))
    plot_stock_candles(candles, symbol, filename=__this_folder__ / "imgs/gld.png", max_num=None)
    
    
    symbol = "QQQ"
    candles = engine.query_candles_of_different_resolutions(symbol, num=num, resolutions=["1d"])["1d"]
    print(len(candles), len(candles["t"]), get_readable_time(candles["t"][0]), get_readable_time(candles["t"][-1]))
    plot_stock_candles(candles, symbol, filename=__this_folder__ / "imgs/qqq.png", max_num=None)
    
    
    symbol = "IWM"
    candles = engine.query_candles_of_different_resolutions(symbol, num=num, resolutions=["1d"])["1d"]
    print(len(candles), len(candles["t"]), get_readable_time(candles["t"][0]), get_readable_time(candles["t"][-1]))
    plot_stock_candles(candles, symbol, filename=__this_folder__ / "imgs/iwm.png", max_num=None)
    """
    exit(0)
    