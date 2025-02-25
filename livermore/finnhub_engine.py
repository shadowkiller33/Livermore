import requests
import os
import time
import pandas as pd
import pytz
import finnhub
import retrying
import numpy as np
import bisect
import json

from mmengine import dump, load
from pathlib import Path
from datetime import datetime, time as dt_time, date
from collections import defaultdict
from IPython import embed
from tqdm import tqdm, trange
from zoneinfo import ZoneInfo
from itertools import chain

from livermore.misc import get_readable_time, get_ny_time, time_to_seconds, get_last_time, process_database_results, plot_stock_candles, plot_multiple_stock_candles, get_begining_of_day
from livermore.stock_candle_database import stock_candle_db
from livermore.signal_utils import compute_vegas_channel_and_signal
from livermore import livermore_root


# Finnhub API Key
try:
    from dotenv import load_dotenv
    load_dotenv()
except:
    pass
API_KEY = os.getenv("FIN_TOKEN")
__this_folder__ = Path(__file__).parent

# Finnhub Option Chain Endpoint

OPTION_CHAIN_URL = "https://finnhub.io/api/v1/stock/option-chain"
QUOTE_URL = "https://finnhub.io/api/v1/quote"
HISTORICAL_PRICE_URL = "https://finnhub.io/api/v1/stock/candle"

try:
    STOCK_SPLITS = load(str(livermore_root / 'data/stock_splits.json'))
except:
    STOCK_SPLITS = None

try:
    STOCK_DIVIDENDS = load(str(livermore_root / 'data/stock_dividends.json'))
except:
    STOCK_DIVIDENDS = None


class FinnhubEngine:
    def __init__(self, api_key=API_KEY):
        self.finnhub_client = finnhub.Client(api_key=api_key)

    @retrying.retry(stop_max_attempt_number=None, wait_fixed=10)
    def get_stock_quote(self, symbol):
        return self.finnhub_client.quote(symbol)

    @retrying.retry(stop_max_attempt_number=None, wait_fixed=10)
    def get_option_chain(self, symbol, expiration=None):
        if isinstance(expiration, str):
            templates = ["%y-%m-%d", "%Y-%m-%d", "%Y.%m.%d", "%y.%m.%d"]
            for template in templates:
                try:
                    expiration = datetime.strptime(expiration, template)
                    break
                except:
                    continue
            assert isinstance(expiration, datetime)
        if isinstance(expiration, datetime):
            expiration = expiration.timestamp()
        # print(expiration)
        # exit(0)
        return self.finnhub_client.option_chain(symbol=symbol)
    
    @retrying.retry(stop_max_attempt_number=None, wait_fixed=10)
    def get_stock_splits(self, symbol):
        return self.finnhub_client.stock_splits(symbol, _from="2000-01-01", to=date.today().strftime("%Y-%m-%d"))

    def update_stock_splits(self, symbols):
        global STOCK_SPLITS
        time = datetime.strptime(STOCK_SPLITS["time"], "%Y-%m-%d").date()
        today = date.today()
        if today <= time:
            return
        ret = {}
        for symbol in tqdm(symbols):
            ret[symbol] = self.get_stock_splits(symbol)
        STOCK_SPLITS = {
            "time": today.strftime("%Y-%m-%d"),
            "data": ret
        }
        dump(STOCK_SPLITS, str(livermore_root / 'data/stock_splits.json'), indent=2)


    @retrying.retry(stop_max_attempt_number=None, wait_fixed=10)
    def get_stock_basic_dividends(self, symbol):
        return self.finnhub_client.stock_basic_dividends(symbol, _from="2000-01-01", to=date.today().strftime("%Y-%m-%d"))

    def update_stock_basic_dividends(self, symbols):
        global STOCK_DIVIDENDS
        time = datetime.strptime(STOCK_DIVIDENDS["time"], "%Y-%m-%d").date()
        today = date.today()
        if today <= time:
            return
        ret = {}
        for symbol in tqdm(symbols):
            ret[symbol] = self.get_stock_basic_dividends(symbol)
        STOCK_DIVIDENDS = {
            "time": today.strftime("%Y-%m-%d"),
            "data": ret
        }
        dump(STOCK_DIVIDENDS, str(livermore_root / 'data/stock_splits.json'), indent=2)

    def get_stock_symbols(self):
        return self.finnhub_client.stock_symbols('US')
    
    @retrying.retry(stop_max_attempt_number=None, wait_fixed=10)
    def get_company_profile(self, symbol):
        return self.finnhub_client.company_profile2(symbol=symbol)

    def compute_candles_for_different_resolutions(self, symbol, resolutions):
        # Compute 30m, 1h, 2h, 3h, 4h, 1d candles. Only store the complete candles during the market time
        
        if isinstance(resolutions, str):
            resolutions = [resolutions]
        for resolution in resolutions:
            assert resolution in ["30m", "1h", "2h", "3h", "4h", "1d"]
        
        min_t1, max_t1 = stock_candle_db.get_min_max_timestamp(symbol, candle_type="1m")
        if min_t1 is None:
            return
        min_tn, max_tn = stock_candle_db.get_min_max_timestamp(symbol, candle_type=resolution)
        
        day_start, day_end = dt_time(9, 30), dt_time(16, 0)
        day_start_1 = dt_time(9, 31)
        one_day = pd.Timedelta("1d")
        
        print(f"Compting multi-resolution {symbol} candles from {get_readable_time(min_t1)} to {get_readable_time(max_t1)}.")
        def loop_compute(start_time, end_time):
            if start_time > end_time:
                return
            candles = stock_candle_db.query_candles(symbol, start_time, end_time, candle_type="1m")
            start_time, end_time = get_ny_time(start_time), get_ny_time(end_time)
            
            def compute_resolution(resolution):
                nonlocal candles, start_time, end_time
                ret = defaultdict(list)
                delta_time = pd.Timedelta(resolution)
                assert delta_time <= one_day
                idx = 0
                day = start_time.replace(hour=9, minute=30)
                while day <= end_time:
                    day = day.astimezone(ZoneInfo("America/New_York"))
                    if day.weekday() >= 5:
                        day = (day + one_day).replace(hour=9, minute=30)
                        continue
                    
                    period_begin = day.replace(hour=9, minute=30)
                    while period_begin < start_time:
                        period_begin += delta_time
                    period_end = period_begin + delta_time
                    period_end = min(period_end, period_begin.replace(hour=16, minute=0))
                    
                    if period_begin.time() == day_start:
                        # Skip the first minute of the day
                        begin_timestamp = (period_begin + pd.Timedelta("1m")).timestamp()
                    else:
                        begin_timestamp = period_begin.timestamp()
                    begin_idx = idx
                    while idx < len(candles) and candles[idx].timestamp < begin_timestamp:
                        idx += 1
                    if idx >= len(candles):
                        break
                    day_count = 0
                    while period_begin < end_time and period_begin.time() < day_end and period_end <= end_time:
                        end_timestamp = period_end.timestamp()
                        open_price = candles[idx].open_price
                        low, high, vol = 1E20, -1E20, 0
                        day_count += 1
                        # item = defaultdict(list)
                        period_count = 0
                        begin_idx = idx
                        while idx < len(candles) and candles[idx].timestamp < end_timestamp:
                            low = min(low, candles[idx].low_price)
                            high = max(high, candles[idx].high_price)
                            vol += candles[idx].volume
                            close_price = candles[idx].close_price
                            idx += 1
                            period_count += 1
                        if vol > 0:
                            timestamp = period_begin.replace(hour=9, minute=30).timestamp() if period_begin.time() == day_start_1 else period_begin.timestamp()
                            item = {
                                "o": open_price,
                                "c": close_price,
                                "h": high,
                                "l": low,
                                "t": timestamp,
                                "v": vol,
                                "candle_type": resolution
                            }
                            for key in item:
                                ret[key].append(item[key])
                        if idx >= len(candles):
                            break
                        # print(get_readable_time(period_begin), get_readable_time(period_end), get_readable_time(end_time), period_count)
                        period_begin += delta_time
                        period_end += delta_time
                        period_end = min(period_end, period_begin.replace(hour=15, minute=59))
                        if resolution == "1d":
                            break
                    if idx >= len(candles):
                        break
                    # break
                    day = (day + one_day).replace(hour=9, minute=30)
                if len(ret["t"]) > 0:
                    stock_candle_db.update_multiple_candles(symbol, dict(ret), resolution)
            for resolution in resolutions:
                compute_resolution(resolution)
        
        if min_tn is not None:
            print(f"We already have multi-resolution {symbol} candles from {get_readable_time(min_tn)} to {get_readable_time(max_tn)}.")
        if min_tn is not None:
            min_t1 = min(min_tn, min_t1)
            max_t1 = max(max_tn, max_t1)
            
            # Recompute the incomplete candles
            loop_compute(min_t1, min_tn + time_to_seconds(resolution))
            loop_compute(max_tn - time_to_seconds(resolution), max_t1)
        else:
            loop_compute(min_t1, max_t1)

    @retrying.retry(stop_max_attempt_number=None, wait_fixed=10)
    def _download_candles(self, symbol, resolution, start_time, end_time=None):
        assert resolution in [1, 5, 15, 30, 60, 'D', 'W', 'M']
        start_time = int(start_time)
        if end_time is None:
            end_time = get_last_time() # Get the last minute of the current time
        else:
            end_time = int(end_time)
        ret = self.finnhub_client.stock_candles(symbol, resolution, start_time, end_time)
        ret.pop("s")
        return ret

    def download_candles(self, symbol, new_start=None, new_end=None):
        # To make sure the data stored in the database is always a continuous interval and new interval can always cover the old interval
        old_start, old_end = stock_candle_db.get_min_max_timestamp(symbol, candle_type="1m")  # [C, D]
        now = get_last_time()
        timestamp = now.timestamp()
        if new_start is None:
            # By default, we fetch the data from the last 2 years
            new_start = timestamp - 3600 * 24 * 365 * 2
        if new_end is None:
            # Fetch the data until now
            new_end = timestamp
        if new_start > new_end:
            return
        
        # print(f"Downloading {symbol} new_start={get_readable_time(new_start)} new_end={get_readable_time(new_end)}.")
        # print(f"Fetching {symbol} old_start={get_readable_time(old_start)} old_end={get_readable_time(old_end)}.")
        
        def loop_download(start_time, end_time):
            if start_time > end_time:
                return
            print(f"=> Downloading {symbol} candles from {get_readable_time(start_time)} to {get_readable_time(end_time)}.")
            period_end = end_time
            while period_end >= start_time:
                period_begin = max(period_end - 3600 * 24 * 30, start_time)
                candles = self._download_candles(symbol, 1, period_begin, period_end)
                if "t" not in candles:
                    break
                stock_candle_db.update_multiple_candles(symbol, candles, "1m")
                period_end = candles["t"][0] - 1
        
        if old_start is not None:
            # [C, D] -> [A, [C, D], B]
            new_start = min(new_start, old_start)
            new_end = max(new_end, old_end)
            loop_download(new_start, old_start - 60)
            loop_download(old_end + 60, new_end)
        else:
            loop_download(new_start, new_end)
    
    def update_recent_candles(self, symbol, resolutions="all"):
        # Fetch the newest candles
        self.download_candles(symbol)
        # Only compute the market time candels
        if resolutions == "all":
            resolutions = ["30m", "1h", "2h", "3h", "4h", "1d"]
        self.compute_candles_for_different_resolutions(symbol, resolutions)
        
    def query_candles_of_different_resolutions(self, symbol, num=200, last_time=None):
        ret = {}
        splits = STOCK_SPLITS["data"].get(symbol, [])
        for split_i in splits:
            split_i["date"] = datetime.strptime(split_i["date"], "%Y-%m-%d").timestamp()
        split_idx = 0
        factor = 1
        splits = sorted(splits, key=lambda _: _["date"], reverse=True)
        begin_time = get_begining_of_day(last_time)
        for resolution in ["30m", "1h", "2h", "3h", "4h", "1d"]:
            last_time = get_last_time(resolution).timestamp()
            begin_of_next_period = last_time + time_to_seconds(resolution)
            # one_minute_candles = stock_candle_db.query_candles(symbol, begin_of_next_period, candle_type="1m")
            results = stock_candle_db.query_the_latest_candle(symbol, num=num, candle_type=resolution, last_time=last_time)
            results = process_database_results(results)
            # Forward Adjusted Price
            # Consider Split & Cash Dividend
            try:
                for i in reversed(range(len(results["t"]))):
                    if split_idx < len(splits) and results["t"][i] < splits[split_idx]["date"]:
                        factor *= splits[split_idx]["fromFactor"] / splits[split_idx]["toFactor"]
                        results["o"][i] *= factor
                        results["h"][i] *= factor
                        results["l"][i] *= factor
                        results["c"][i] *= factor
                ret[resolution] = results
            except Exception:
                pass
        return ret
    
    def validate_candles(self, symbol):
        for resolution in ["1m", "30m", "1h", "2h", "3h", "4h", "1d"]:
            candles = stock_candle_db.query_candles(symbol, candle_type=resolution)
            timestamp = [candle.timestamp for candle in candles]
            assert len(timestamp) == len(set(timestamp)), f"Stock {symbol} has duplicated {resolution} candles."

    def get_recent_signals(self, symbol, num_days=2):
        self.update_recent_candles(symbol)
        period_end = time.time()
        
        now = get_ny_time(period_end)
        last_date = np.busday_offset(now.strftime('%Y-%m-%d'), -num_days, roll='backward')
        last_date = last_date.astype(datetime)
        delta_seconds = (now.date() - last_date).total_seconds()
        period_start = period_end - delta_seconds
        
        resolutions = ["30m", "1h", "2h", "3h", "4h", "1d"]
        data = self.query_candles_of_different_resolutions(symbol)
        signals = {}
        for resolution in resolutions:
            signals[resolution] = compute_vegas_channel_and_signal(data[resolution])
        buy_signals = {}
        for resolution in resolutions:
            if resolution not in data:
                continue
            t = data[resolution]["t"]
            buy_signal = signals[resolution]["buy_signal"]
            buy_signal = [t[i] for i, flag in enumerate(buy_signal) if flag and period_start <= t[i]]
            if len(buy_signal) > 0:
                buy_signals[resolution] = int(buy_signal[-1])
        return buy_signals

    def get_all_existing_signals(self, symbol):
        # For analysis
        resolutions = ["30m", "1h", "2h", "3h", "4h", "1d"]
        data = self.query_candles_of_different_resolutions(symbol, num=None)
        period_start = data["1d"]["t"][30]
        signals = {}
        for resolution in resolutions:
            # print(resolution, len(data[resolution]["t"]))
            signals[resolution] = compute_vegas_channel_and_signal(data[resolution])
        buy_signals = {}
        for resolution in resolutions:
            t = data[resolution]["t"]
            buy_signal = signals[resolution]["buy_signal"]
            buy_signal = [t[i] for i, flag in enumerate(buy_signal) if flag and period_start <= t[i]]
            if len(buy_signal) > 0:
                buy_signals[resolution] = buy_signal
        return buy_signals

    def calculate_realized_volatility(self, prices, window=21, annual_factor=252):
        """
        Calculate Realized Volatility (RV) using log returns.

        :param prices: Series or list, daily closing prices of the asset
        :param window: int, rolling window size (default is 21 days)
        :param annual_factor: int, annualization factor (default is 252 trading days)
        :return: Series, realized volatility
        """
        if isinstance(prices, list):
            prices = pd.Series(prices)
        # Compute log returns
        log_returns = np.log(prices / prices.shift(1))
        
        # Compute rolling realized volatility
        rv = log_returns.rolling(window=window).apply(lambda x: np.sqrt(np.sum(x**2)), raw=True)
        
        # Annualized realized volatility
        rv_annualized = rv * np.sqrt(annual_factor / window)
        return rv_annualized


def update_new_data():
    symbols_by_sectors = load(str(livermore_root / 'data/remapped_coarse_selection.json'))
    symbols = []
    for key, value in symbols_by_sectors.items():
        symbols += value
    print(len(symbols))
    for symbol in tqdm(symbols):
        # symbol, new_start=None, new_end=None, second_round=False)
        five_year = 3600 * 24 * 365 * 2
        # engine.download_candles(symbol, new_start=int(time.time() - five_year), new_end=get_last_time().timestamp())
        engine.update_recent_candles(symbol)
        # engine.validate_candles(symbol)


if __name__ == '__main__':    
    profiles = load(str(livermore_root / 'data/large_companies_20250206.json'))
    symbols_by_sectors = load(str(livermore_root / 'data/remapped_coarse_selection.json'))
    lingfeng_selections = load(str(livermore_root / 'data/selected_sotcks.json'))
    lingfeng_selections = list(chain(*lingfeng_selections.values()))
    symbols_to_sector = {}
    for name, value in symbols_by_sectors.items():
        for item in value:
            symbols_to_sector[item] = name
    symbols = list(symbols_to_sector.keys())

    today = datetime.now()
    # formatted_date = today.strftime('%Y%m%d')
    formatted_date = "20250206"
    engine = FinnhubEngine(api_key="cu9bivpr01qnf5nmlh8gcu9bivpr01qnf5nmlh90")
    

    # engine.update_stock_splits(symbols)
    # alls_opportunities = {}
    # for symbol in tqdm(symbols):
    #     opportunities = engine.get_recent_signals(symbol)
    #     if len(opportunities) > 0:
    #         alls_opportunities[symbol] = opportunities
    # dump(alls_opportunities, str(livermore_root / 'data/tmp/all_opportunities.json'), indent=2)
    # print(len(alls_opportunities))
    # exit(0)
    
    alls_opportunities = load(str(livermore_root / 'data/tmp/all_opportunities.json'))
    PREVIOUS_SIGNAL = {}
    count0 = count1 = 0
    for symbol, signals in alls_opportunities.items():
        if len(signals) == 0:
            continue
        indices = ["30m", "1h", "2h", "3h", "4h", "1d"]
        is_strong = sum([_ in ["1h", "2h", "3h", "4h", "1d"] for _ in signals]) >= 3
        best_signal = max([indices.index(_) for _ in signals])
        if not (symbol in lingfeng_selections or is_strong):
            continue
        if symbol in lingfeng_selections:
            count0 += 1
        elif is_strong:
            count1 += 1
        previous_signal = PREVIOUS_SIGNAL.get(symbol, None)
        if previous_signal is not None:
            previous_best, previous_signal, timestamp = previous_signal["best"], previous_signal["signal"], previous_signal["timestamp"]
            # Skip if the same signals were sent within the last 2 days, because the last appeared signal may be in two days.
            if len(signals) <= len(previous_signal) and best_signal <= previous_best and (datetime.now() - timestamp).days < 2:
                continue
        # PREVIOUS_SIGNAL[symbol] = {"best": best_signal, "signal": signals, "timestamp": datetime.now()}
        # dump(PREVIOUS_SIGNAL, livermore_root / 'data/previous_send.json', indent=2)
        latest_time = get_readable_time(max(list(signals.values())))
        sector_name = symbols_to_sector[symbol]
        # print(f"Send signal for {symbol} to channel {sector_name} with {list(signals.keys())} at {latest_time}.")
        
        # exit(0)
            
    print(count0, count1)
    exit(0)
    
    
    
    
    # symbol = "AAPL"
    # session = requests.Session()
    # session.params = {'token': "cu9bivpr01qnf5nmlh8gcu9bivpr01qnf5nmlh90"}
    # params = {'symbol': symbol}
    # QUOTE_URL = "https://finnhub.io/api/v1/stock/offerings"
    # response = session.get(QUOTE_URL, params=params)
    # response.raise_for_status()
    # print(response.json())

    
    # url = "https://finnhub.io/api/v1/stock/offerings?symbol=TSLA&token="
    # response = requests.get(url)
    # data = response.json()
    # print(response)
    # print(engine.finnhub_client.stock_splits('TSLA', "2000-01-01", "2025-01-01"))
    # print(engine.finnhub_client.stock_basic_dividends('TSLA'))
    # exit(0)
    
    
    # print(engine.get_recent_signals("COO"))
    exit(0)
    
    # fetch_stock_splits()
    # exit(0)

    # timestamp = 1731508200
    # print(engine.download_stock_candles("AAPL", 1, timestamp, timestamp + 3600 * 1.0))
    # check_days()
    # scan_all_options()
    # scan_all_opotunities()
    # compute_all_opportunities()
    # update_new_data()
    # get_recent_signals()
    
    #  ["%y-%m-%d", "%Y-%m-%d", "%Y.%m.%d", "%y.%m.%d"]
    # symbol = "INTC"
    # expiration = "2025-02-21"
    # options = json.loads(engine.get_option_chain(symbol, expiration))
    # print(len(options))
    # embed()
    # dump(options, str(livermore_root / 'data/tmp/options.json'), indent=2)
    # options = load(str(livermore_root / 'data/tmp/options.json'))
    
    exit(0)
    
    
    # data = load(str(livermore_root / 'data/existing_opportunities.json'))
    # for symbol, item in data.items():
    #     for resolution, value in item.items():
    #         value["num"] = len(value["buy_signal"])
    #         print(resolution, value["num"], len(value["buy_signal"]))
    # dump(data, str(livermore_root / 'data/existing_opportunities_test.json'), indent=2)
    # exit(0)
    
    # for resolution in ["30m", "1h", "2h", "3h", "4h", "1d"]:
    #     print(f"Delete {resolution}")
        # stock_candle_db.delete_all_candles_by_candle_type(resolution)
    # engine.update_recent_candles("AAPL")
    
    
    # symbols_by_sectors = load(str(livermore_root / 'data/coarse_selection.json'))
    # symbols = []
    # for key, value in symbols_by_sectors.items():
    #     symbols += value
    # for symbol in symbols:
    #     engine.update_recent_candles(symbol)
    exit(0)
    # engine.validate_candles("AAPL")
    # st = time.time()
    # data = engine.compute_all_resolutions("AAPL", num=200)
    # print(time.time() - st)
    # print(data["30m"].keys())
    # print(data["1h"].keys())
    # exit(0)
    
    # for resolution in ["30m", "1h", "2h", "3h", "4h", "1d"]:
    #     for item in data[resolution]["t"][:5]:
    #         print(get_readable_time(item))
    #     print()
    # exit(0)
    resolution = "1d"
    # print(len(data[resolution]["t"]))
    
    signals = compute_vegas_channel_and_signal(data[resolution])
    image = plot_stock_candles(data[resolution], "AAPL", signals=signals, kline_type=resolution) #, filename=livermore_root / "data/tmp/test.png")
    # print(type(image))
    # exit(0)
    
    image = plot_multiple_stock_candles(data, "AAPL", filename=livermore_root / "data/tmp/test.png")
    