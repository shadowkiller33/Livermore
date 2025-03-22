from mmengine import dump, load
from collections import defaultdict
from pathlib import Path

from livermore.misc import get_readable_time, get_ny_time, time_to_seconds, get_last_time, process_database_results, plot_stock_candles, plot_multiple_stock_candles
from livermore.signal_utils import compute_vegas_channel_and_signal
from livermore import livermore_root
from livermore.finnhub_engine import FinnhubEngine, STOCK_SPLITS
from datetime import datetime
import time, numpy as np


__this_folder__ = Path(__file__).parent


def compute_yields_over_years(dataset):
    dataset = {dataset["t"][i]: {key: dataset[key][i] for key in dataset if key not in "t"} for i in range(len(dataset["t"]))}
    close_over_years = defaultdict(list)
    yield_over_years = {}
    for timestamp in dataset:
        year = datetime.fromtimestamp(timestamp).year
        close_over_years[year].append([timestamp, dataset[timestamp]["c"]])
    
    for year in close_over_years:
        yield_over_years[year] = sorted(close_over_years[year], key=lambda x: x[0])
        yield_over_years[year] = (yield_over_years[year][-1][1] / yield_over_years[year][0][1] - 1) * 100
        # print(year, yield_over_years[year])
    return yield_over_years


def compare_sectors_yields_this_year():
    sector_performance = {}
    rvs = {}
    for symbol in all_symbols:
        candles = engine.query_candles_of_different_resolutions(symbol, num=None, resolutions=["1d"])["1d"]
        # plot_stock_candles(candles, symbol, filename=__this_folder__ / f"imgs/{symbol}.png".lower(), max_num=None)
        # print(symbol, profiles[symbol]["description"])
        yield_over_years = compute_yields_over_years(candles)
        sector_performance[symbol] = yield_over_years[this_year]
        rvs[symbol] = engine.get_realized_volatility(candles["c"])[-100:]
    for symbol in sorted(sector_performance, key=lambda x: sector_performance[x], reverse=True):
        rv = rvs[symbol]

        print(symbol, sector_performance[symbol], profiles[symbol]["description"], np.mean(rv[-100:]), np.mean(rv[-5:]))


def compute_alpha_and_beta():
    import statsmodels.api as sm
    
    candles = {}
    for symbol in all_symbols:
        # print(symbol)
        candles[symbol] = engine.query_candles_of_different_resolutions(symbol, num=None, resolutions=["1d"])["1d"]
        
        # print(candles[symbol]["c"][-1])
        # print(candles["SPY"]["c"][-1])
        
    baseline = {candles["SPY"]["t"][i]: candles["SPY"]["c"][i] / candles["SPY"]["o"][i] - 1 for i in range(len(candles["SPY"]["t"]))}
    
    for symbol in candles.keys():
        if symbol == "SPY":
            continue
        
        # print(symbol)
        # print(candles[symbol]["c"][-1])
        # print(candles["SPY"]["c"][-1])
        
        # exit(0)
        yields = {candles[symbol]["t"][i]: candles[symbol]["c"][i] / candles[symbol]["o"][i] - 1 for i in range(len(candles[symbol]["t"]))}
        # print(symbol, len(yields), len(baseline), yields.keys())
        
        shared_dates = set(baseline.keys()) & set(yields.keys())
        stock_returns = [yields[date] * 100 for date in shared_dates]
        market_returns = [baseline[date] * 100 for date in shared_dates]
        print(symbol, profiles[symbol]["description"], "#Data", len(market_returns), len(stock_returns))
        
        pos_stock_returns = [stock_returns[i] for i in range(len(stock_returns)) if market_returns[i] > 0]
        pos_market_returns = [market_returns[i] for i in range(len(market_returns)) if market_returns[i] > 0]
        model = sm.OLS(pos_stock_returns, sm.add_constant(pos_market_returns)).fit()
        # print(model.params)
        alpha, beta = model.params
        print(f"Pos Alpha: {alpha:.6f}  Beta: {beta:.6f}")
        
        neg_stock_returns = [stock_returns[i] for i in range(len(stock_returns)) if market_returns[i] < 0]
        neg_market_returns = [market_returns[i] for i in range(len(market_returns)) if market_returns[i] < 0]
        model = sm.OLS(neg_stock_returns, sm.add_constant(neg_market_returns)).fit()
        # print(model.params)
        alpha, beta = model.params
        print(f"Neg Alpha: {alpha:.6f}  Beta: {beta:.6f}")


if __name__ == "__main__":
    this_year = datetime.now().year
    profiles = load(livermore_root / "data/stock_symbols.json")
    print(len(profiles))
    profiles = {item["symbol"]: item for item in profiles}
    sectors = load(str(livermore_root / 'data/etf_by_sectors.json'))["sectors"]
    engine = FinnhubEngine(api_key="cu9bivpr01qnf5nmlh8gcu9bivpr01qnf5nmlh90")
    # candles, symbol, kline_type="", signals=None, filename=None, figsize=(16, 9), time_range=None, max_num=100, market_time_only=True, output_ax=None, show_legend=True
    
    all_symbols = sectors + ["QQQ", "IWM", "SPY"]
    
    # compare_sectors_yields_this_year()
    compute_alpha_and_beta()
    
