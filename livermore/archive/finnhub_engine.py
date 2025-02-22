import requests
import os
import time
import pandas as pd
import pytz
import finnhub
import retrying
import numpy as np
import bisect

from mmengine import dump, load
from pathlib import Path
from datetime import datetime, time as dt_time
from collections import defaultdict
from IPython import embed
from tqdm import tqdm, trange
from zoneinfo import ZoneInfo

from livermore.misc import get_readable_time, get_ny_time, time_to_seconds, get_last_time, plot_stock_candles, plot_multiple_stock_candles
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


class FinnhubEngine:
    def __init__(self, api_key=API_KEY):
        self.finnhub_client = finnhub.Client(api_key=api_key)

    @retrying.retry(stop_max_attempt_number=None, wait_fixed=10)
    def get_stock_quote(self, symbol):
        return self.finnhub_client.quote(symbol)

    @retrying.retry(stop_max_attempt_number=None, wait_fixed=10)
    def get_option_chain(self, symbol, expiration):
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
            expiration = expiration.time()
        return self.finnhub_client.option_chain(symbol=symbol, expiration=expiration)

    @retrying.retry(stop_max_attempt_number=None, wait_fixed=10)
    def download_stock_candles(self, symbol, resolution, start_time, end_time=None):
        assert resolution in [1, 5, 15, 30, 60, 'D', 'W', 'M']
        start_time = int(start_time)
        if end_time is None:
            end_time = get_last_time() # Get the last minute of the current time
        else:
            end_time = int(end_time)
        ret = self.finnhub_client.stock_candles(symbol, resolution, start_time, end_time)
        ret.pop("s")
        # if "t" in ret and len(ret["t"]) > 0:
        #     indices = sorted(range(len(ret["t"])), key=lambda x: ret["t"][x])
        #     ret = {key: [ret[key][i] for i in indices] for key in ret if key != "s"}
        return ret
    
    def get_stock_symbols(self):
        return self.finnhub_client.stock_symbols('US')
    
    @retrying.retry(stop_max_attempt_number=None, wait_fixed=10)
    def get_company_profile(self, symbol):
        return self.finnhub_client.company_profile2(symbol=symbol)
    
    def compute_stock_candles_of_a_interval(self, one_minute_data, start_time, resolution="1h"):
        if isinstance(resolution, str):
            resolution = time_to_seconds(resolution)
        else:
            assert isinstance(resolution, int)
        slots = []
        for i in range(len(one_minute_data["t"])):
            if start_time <= one_minute_data["t"][i] < start_time + resolution:
                slots.append({key: value[i] for key, value in one_minute_data.items()})
        slots = sorted(slots, key=lambda x: x["t"])
        h = max([slot["h"] for slot in slots])
        l = min([slot["l"] for slot in slots])
        v = sum([slot["v"] for slot in slots])
        return {"c": slots[-1]["c"], "h": h, "l": l, "o": slots[0]["o"], "t": start_time, "v": v}
    
    def compute_stock_candles_of_a_resolution(self, one_minute_data, resolution="1h"):
        # assert False, "时间slot的计算有bug,应该每天从9:30开始"
        st = time.time()
        
        one_minute_data.pop("s", None)
        indices = sorted(range(len(one_minute_data["t"])), key=lambda x: one_minute_data["t"][x])
        one_minute_data = {key: [one_minute_data[key][i] for i in indices] for key in one_minute_data}
        time_slots = one_minute_data["t"]
        
        begin_time = get_ny_time(time_slots[0])
        resolution = resolution.lower()
        assert resolution[-1] in ["m", "h", "d"]
        if resolution[-1] in ["h", "d"]:
            if resolution[-1] == "d":
                assert resolution == "1d"
            begin_time = begin_time.replace(hour=9, minute=30)
        else:
            assert resolution[-1] == "m" and resolution != "1m"
            begin_time = begin_time.replace(minute=0)
            
        delta_time = pd.Timedelta(resolution)
    
        st = time.time()
        day_start, day_end = dt_time(9, 30), dt_time(16, 0)
        ret = defaultdict(list)
        i = 0
        while i < len(time_slots):
            while i < len(time_slots) and begin_time > get_ny_time(time_slots[i]):
                i +=1 
            end_time = begin_time + delta_time
            # print(begin_time, end_time)
            itme = defaultdict(list)
            while i < len(time_slots) and begin_time <= get_ny_time(time_slots[i]) < end_time:
                ny_slot = get_ny_time(time_slots[i])
                day_time = ny_slot.time()
                if not (day_start < day_time < day_end):
                    i += 1
                    continue
                for key in one_minute_data:
                    if key == "s":
                        continue
                    itme[key].append(one_minute_data[key][i])
                i += 1
            if len(itme["c"]) > 0:
                ret["c"].append(itme["c"][-1])
                ret["h"].append(max(itme["h"]))
                ret["l"].append(min(itme["l"]))
                ret["o"].append(itme["o"][0])
                ret["t"].append(int(begin_time.timestamp()))
                ret["v"].append(sum(itme["v"]))
            
            # To handle the summer time and winter time
            if end_time.time() >= day_end:
                end_time = get_ny_time(end_time + pd.Timedelta("1d")).replace(hour=9, minute=30)
            elif end_time.time() < day_start:
                end_time = get_ny_time(end_time).replace(hour=9, minute=30)
            begin_time = end_time
            
        return dict(ret)
    
    def compute_resolution(self, symbol, resolutions):
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
            # st = time.time()
            candles = stock_candle_db.query_candles(symbol, start_time, end_time, candle_type="1m")
            start_time, end_time = get_ny_time(start_time), get_ny_time(end_time)
            
            def compute_resolution(resolution):
                if resolution != "1d":
                    return
                nonlocal candles, start_time, end_time
                ret = defaultdict(list)
                delta_time = pd.Timedelta(resolution)
                assert delta_time <= one_day
                idx = 0
                # print(f"Computing {resolution} {symbol} candles from {get_readable_time(start_time)} to {get_readable_time(end_time)} with {len(candles)} one-minute candle.")

                day = start_time.replace(hour=9, minute=30)
                """
                1679923800 2023-03-27 09:30 20939057
                1731508200 2024-11-13 09:30 1358577
                """
                times = [get_ny_time(1679923800), get_ny_time(1731508200)]
                
                while day <= end_time:
                    day = day.astimezone(ZoneInfo("America/New_York"))
                    if day.weekday() >= 5:
                        day = (day + one_day).replace(hour=9, minute=30)
                        continue
                    
                    period_begin = day.replace(hour=9, minute=30)
                    # 2023-02-14 09:30
                    # print(period_begin)
                    
                    # if period_begin == times[0]:
                    #     print("==>", times[0], period_begin)
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
                    # print("=>", begin_idx, idx, "|", get_readable_time(candles[begin_idx].timestamp), "|", get_readable_time(candles[idx].timestamp), "|", get_readable_time(period_begin), "|", get_readable_time(period_end))
                    # for i in range(begin_idx, idx):
                    #     print(i, get_readable_time(candles[i].timestamp), candles[i].timestamp, period_begin.timestamp(), get_readable_time(period_begin.timestamp()), get_readable_time(period_end.timestamp()), period_end.weekday())
                    # print("-" * 20)
                    if idx >= len(candles):
                        break
                    
                    # print(get_readable_time(period_begin.timestamp()), get_readable_time(period_end.timestamp()))
                    # print(get_readable_time(candles[idx].timestamp))
                    # print(day_end, get_readable_time(end_time))
                    # print(get_readable_time(period_begin), get_readable_time(period_end), idx)
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
                        """
                        if period_begin == times[0]:
                            print(get_readable_time(period_begin), get_readable_time(candles[idx - 1].timestamp), get_readable_time(candles[idx].timestamp))
                            
                            print(open_price, close_price, high, low, vol, period_count, candles[idx - 1].timestamp)
                            
                            print(stock_candle_db.query_candles(symbol, times[0].timestamp(), times[0].timestamp() + 3600 * 0.5, candle_type="1m"))
                            print(self.fetch_candles(symbol, times[0].timestamp(), times[0].timestamp() + 3600 * 0.5))
                            print(begin_idx, idx, get_readable_time(candles[begin_idx].timestamp), get_readable_time(candles[idx].timestamp))
                            print(times[0].weekday(), times[1].weekday())
                            tmp = [i for i, _ in enumerate(candles) if times[0].timestamp() <= _.timestamp < times[0].timestamp() + 3600 * 0.5]
                            print(tmp)
                            embed()
                            # exit(0)
                        # """
                        
                        # print(begin_idx, idx, idx - begin_idx, period_count, get_readable_time(period_begin), "|", get_readable_time(period_end), vol, get_readable_time(candles[begin_idx].timestamp), "|", get_readable_time(candles[idx].timestamp))
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
                    # print(resolution, day_count)
                    
                    # print(get_readable_time(start_time), get_readable_time(end_time))
                    # print(get_readable_time(day), count, resolution, vol)
                    # print(count, resolution, get_readable_time(day), get_readable_time(period_begin), get_readable_time(period_end), get_readable_time(end_time))
                    # break
                    day = (day + one_day).replace(hour=9, minute=30)
                if len(ret["t"]) > 0:
                    stock_candle_db.update_multiple_candles(symbol, dict(ret), resolution)
                
                # print(len(ret))
            for resolution in resolutions:
                compute_resolution(resolution)
            # print(len(ret))
            # exit(0)
        
        if min_tn is not None:
            # print(get_readable_time(min_t1), get_readable_time(max_t1))
            # print(min_tn, max_tn, resolution)
            # print(get_readable_time(min_t1), get_readable_time(max_t1))
            # exit(0)
            print(f"We already have multi-resolution {symbol} candles from {get_readable_time(min_tn)} to {get_readable_time(max_tn)}.")
        if min_tn is not None:
            min_t1 = min(min_tn, min_t1)
            max_t1 = max(max_tn, max_t1)
            
            # Recompute the incomplete candles
            loop_compute(min_t1, min_tn + time_to_seconds(resolution))
            loop_compute(max_tn - time_to_seconds(resolution), max_t1)
        else:
            loop_compute(min_t1, max_t1)
    
    def fetch_candles(self, symbol, new_start=None, new_end=None):
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
        
        print(f"Fetching {symbol} new_start={get_readable_time(new_start)} new_end={get_readable_time(new_end)}.")
        # print(f"Fetching {symbol} old_start={get_readable_time(old_start)} old_end={get_readable_time(old_end)}.")
        
        def loop_fetch(start_time, end_time):
            if start_time > end_time:
                return
            print(f"=> Downloading {symbol} candles from {get_readable_time(start_time)} to {get_readable_time(end_time)}.")
            period_end = end_time
            while period_end >= start_time:
                period_begin = max(period_end - 3600 * 24 * 30, start_time)
                candles = self.download_stock_candles(symbol, 1, period_begin, period_end)
                if "t" not in candles:
                    break
                stock_candle_db.update_multiple_candles(symbol, candles, "1m")
                period_end = candles["t"][0] - 1
        
        if old_start is not None:
            # [C, D] -> [A, [C, D], B]
            new_start = min(new_start, old_start)
            new_end = max(new_end, old_end)
            loop_fetch(new_start, old_start - 60)
            loop_fetch(old_end + 60, new_end)
        else:
            loop_fetch(new_start, new_end)
    
    def update_recent_candles(self, symbol, resolution="all"):
        # Fetch the newest candles
        self.fetch_candles(symbol)
        # Only compute the market time candels
        if resolution == "all":
            self.compute_resolution(symbol, ["30m", "1h", "2h", "3h", "4h", "1d"])
        else:
            self.compute_resolution(symbol, resolution)
        # print("Finished updating the recent candles.")
        
    def compute_all_resolutions(self, symbol, num=200):
        def process_data(dataset):
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
        
        ret = {}
        for resolution in ["30m", "1h", "2h", "3h", "4h", "1d"]:
            ret[resolution] =  process_data(stock_candle_db.query_the_latest_candle(symbol, num=num, candle_type=resolution))
        return ret
    
    def validate_candles(self, symbol):
        for resolution in ["1m", "30m", "1h", "2h", "3h", "4h", "1d"]:
            candles = stock_candle_db.query_candles(symbol, candle_type=resolution)
            timestamp = [candle.timestamp for candle in candles]
            assert len(timestamp) == len(set(timestamp)), f"Stock {symbol} has duplicated {resolution} candles."

    # @retrying.retry(stop_max_attempt_number=None, wait_fixed=10)
    # def get_etf_profile(self, symbol):
    #     return self.finnhub_client.etfs_sector_exp(symbol)
    
    
def save_all_existing_symbols():
    if (livermore_root / 'data/stock_symbols.json').exists():
        symbols = load(str(livermore_root / 'data/stock_symbols.json'))
    else:
        engine = FinnhubEngine()
        symbols = engine.get_stock_symbols()
    
    ret = []
    for item in symbols:
        if item["currency"] != "USD" or item["type"] != "Common Stock" or item["mic"] == "OOTC":
            continue
        ret.append(item)
    print("Total number of stock symbols: ", len(ret))
    dump(ret, str(livermore_root / 'data/stock_symbols.json'), indent=2)


def save_all_company_profiles():
    engine = FinnhubEngine()
    symbols = load(str(livermore_root / 'data/stock_symbols.json'))
    try:
        profiles = load(str(livermore_root / f'data/company_profiles_{formatted_date}.json'))
    except:
        profiles = {}
    for i in trange(len(symbols)):
        if symbols[i]["symbol"] in profiles: # and len(profiles[symbols[i]["symbol"]]) > 0:
            continue
        profile = engine.get_company_profile(symbols[i]["symbol"])
        profiles[symbols[i]["symbol"]] = profile
        if i % 50 == 0:
            dump(profiles, str(livermore_root / f'data/company_profiles_{formatted_date}.json'), indent=2)
    dump(profiles, str(livermore_root / f'data/company_profiles_{formatted_date}.json'), indent=2)


def scan_all_company_profiles():
    engine = FinnhubEngine()
    symbols = load(str(livermore_root / 'data/stock_symbols.json'))
    for i in trange(len(symbols)):
        profile = engine.get_company_profile(symbols[i]["symbol"])


def save_forex_info():
    profiles = load(str(livermore_root / f'data/company_profiles_{formatted_date}.json'))
    currencies = defaultdict(int)
    for symbol, profile in profiles.items():
        if len(profile) == 0:
            continue
        if profile["currency"] != profile["estimateCurrency"]:
            continue
        currencies[profile["currency"]] += 1
    
    from currency_converter import CurrencyConverter
    c = CurrencyConverter()
    currencies_map = {}
    for currency in currencies:
        try:
            currencies_map[currency] = c.convert(1, currency, 'USD') 
        except:
            currencies_map[currency] = 0
    dump(currencies_map, str(livermore_root / f'data/currencies_map_{formatted_date}.json'), indent=2)


def scan_all_large_stocks(threshold=10):  # Market Cap >= 10B USD
    currency_map = load(str(livermore_root / f'data/currencies_map_{formatted_date}.json'))
    profiles = load(str(livermore_root / f'data/company_profiles_{formatted_date}.json'))
    large_companies = []
    industry_count = defaultdict(int)
    market_value = {}
    for symbol, profile in profiles.items():
        if len(profile) == 0:
            continue
        if profile["exchange"] in ["INDONESIA STOCK EXCHANGE"]:
            continue
        # if profile["exchange"] not in ["NEW YORK STOCK EXCHANGE, INC.", "NASDAQ NMS - GLOBAL MARKET"]:
        #     continue
        marketCapitalization = profile["marketCapitalization"]
        market_cap = marketCapitalization * currency_map[profile["currency"]] / 1000
        if profile["marketCapitalization"] in market_value:
            continue
        market_value[profile["marketCapitalization"]] = 1
        if market_cap > threshold:
            large_companies.append([symbol, market_cap])
            industry_count[profile["finnhubIndustry"]] += 1
    print(dict(large_companies))
    print(f"Total number of large companies: {len(large_companies)}/{len(profiles)}.")
    large_companies = sorted(large_companies, key=lambda x: x[1], reverse=True)
    dump(large_companies, str(livermore_root / f'data/large_companies_{formatted_date}.json'), indent=2)


def check_existing_symbols():
    data = load(str(livermore_root / 'data/selected_sotcks.json'))
    mapping = load(str(livermore_root / f'data/company_profiles_{formatted_date}.json'))
    currency_map = load(str(livermore_root / f'data/currencies_map_{formatted_date}.json'))
    profiles = load(str(livermore_root / f'data/company_profiles_{formatted_date}.json'))
    small_rate = []
    total_count = []
    ETFS = defaultdict(list)
    etf_symbols = {}
    for sector in data:
        for symbol in data[sector]:
            if symbol not in mapping:
                ETFS[sector].append(symbol)
                print(symbol)
                # get_stock_candles('SPY', 1, time.time() - 3600 * 24 * 30, time.time())
                # etf_symbols[symbol] = engine.get_stock_candles(symbol, 1, time.time() - 3600 * 24 * 30, time.time())
            else:
                profile = profiles[symbol]
                marketCapitalization = profile["marketCapitalization"]
                market_cap = marketCapitalization * currency_map[profile["currency"]] / 1000
                print(symbol, mapping[symbol]["finnhubIndustry"], sector, market_cap)
                small_rate.append(market_cap < 10)
            total_count.append(symbol)
    print(len(small_rate), len(total_count), len(small_rate) / len(total_count), np.mean(small_rate))
    print(dict(ETFS))
    dump(etf_symbols, str(livermore_root / f'data/etf_profiles_{formatted_date}.json'), indent=2)
    

def check_channel_ids():
    data = load(str(livermore_root / 'data/discord_channels.json'))
    content = """SEMI_CONDUCTOR=1333613478685970554
CRYPTO=1333613521891495998
BIG_TECH=1333613598450384987
AI_SOFTWARE=1333613642431594527
SPY_QQQ_IWM=1333613691110821888
FINANCE=1333613735604125737
BIO_MED=1333613812309557319
VOL=1333613896623198298
TLT_TMF=1333614021915574304
ENERGY=1333614121886683207
SPACE=1335393219491528736
ROBO=1335519046291947542
SOCIAL=1335519117079351337
DEFENSE=1335519181931679834
NUCLEAR=1335519259971031050
SMALL_AI=1335393054563237938
SHORT_EFT=1335393145739018240
FOOD=1333614367979077705
DRONE=1335519455475662848
SPORTS=1335519528355893258
FASHION=1335519593002958921
TRAVEL=1335519666705141840
AUTO_DRIVE=1335519725287112725
CN=1335519802265047161"""
    for key, item in data.items():
        print(key, item)
        assert f"{key}={item}" in content


def check_compute_stock_candles_of_a_interval():
    tmp = engine.get_stock_candles('AAPL', 1, time.time() - 3600 * 24 * 30, time.time())
    tmp2 = engine.get_stock_candles('AAPL', "D", time.time() - 3600 * 24 * 30, time.time())
    tmp.pop("s")
    tmp2.pop("s")
    error = 0
    for i in trange(len(tmp2["t"])):
        res = engine.compute_stock_candles_of_a_interval(tmp, tmp2["t"][i], "H")
        if res != {key: value[i] for key, value in tmp2.items()}:
            error += 1
    print("Error rate", error / len(tmp2["t"]))
    

def collect_all_symbol_history_info():
    important_symbols_data = load(str(livermore_root / 'data/selected_sotcks.json'))
    important_symbols = []
    for key, value in important_symbols_data.items():
        important_symbols += value
    print(len(important_symbols))
    symbols = load(str(livermore_root / 'data/large_companies_20250206.json'))
    symbols = [_[0] for _ in symbols]
    print(len(symbols))
    symbols = sorted(set(symbols + important_symbols))
    print(len(symbols))
    
    time_stamp = int(time.time())
    for symbol in tqdm(symbols):
        if (livermore_root / f'data/history_data/{symbol}.json').exists():
            continue
        end_time = time_stamp
        ret = []
        for i in range(25):
            begin_time = end_time - 3600 * 24 * 30
            candles = engine.get_stock_candles(symbol, 1, begin_time, end_time)
            try:
                end_time = candles["t"][0] - 1
                ret.append(candles)
            except:
                break
        print(symbol, get_readable_time(end_time))
        dump(ret, str(livermore_root / f'data/history_data/{symbol}.json'), indent=2)


def prepare_existing_data():
    symbols_by_sectors = load(str(livermore_root / 'data/coarse_selection.json'))
    symbols = []
    for key, value in symbols_by_sectors.items():
        symbols += value
    print(len(symbols))
    exit(0)
    
    for symbol in tqdm(symbols):
        filename = livermore_root / f'data/history_data/{symbol}.json'
        data = load(filename)
        ret = defaultdict(list)
        for item in data:
            for key in item:
                if key == "s":
                    continue
                ret[key].extend(item[key])
        assert len(ret["t"]) == len(set(ret["t"]))
        symbol = filename.stem
        # engine.update_recent_candles(symbol)
        # print(symbol)
        engine.update_all_resolutions(symbol)
        # exit(0)


def update_new_data():
    symbols_by_sectors = load(str(livermore_root / 'data/coarse_selection.json'))
    symbols = []
    for key, value in symbols_by_sectors.items():
        symbols += value
    print(len(symbols))
    
    for symbol in tqdm(symbols):
        # symbol, new_start=None, new_end=None, second_round=False)
        five_year = 3600 * 24 * 365 * 5
        engine.fetch_candles(symbol, new_start=int(time.time() - five_year), new_end=get_last_time())
        engine.validate_candles(symbol, "1m")
        exit(0)
        # engine.update_all_resolutions(symbol)


def reduce_stock_list():
    important_symbols_data = load(str(livermore_root / 'data/selected_sotcks.json'))
    # print(important_symbols_data)
    important_symbols = []
    for key, value in important_symbols_data.items():
        important_symbols += value
    print(len(important_symbols))
    
    profiles = load(str(livermore_root / f'data/company_profiles_{formatted_date}.json'))
    
    symbol_by_sectors = defaultdict(list)
    large_amount_of_data = []
    tqdm_obj = tqdm(sorted((livermore_root / 'data/history_data').glob("*.json")))
    for filename in tqdm_obj:
        data = load(filename)
        symbol = filename.stem
        ret = defaultdict(list)
        for item in data:
            for key in item:
                if key == "s":
                    continue
                ret[key].extend(item[key])
        if len(ret["t"]) > 10000:
            large_amount_of_data.append(symbol)
            category = profiles[symbol]["finnhubIndustry"] if symbol in profiles else "ETF"
            symbol_by_sectors[category].append(symbol)
        elif symbol in important_symbols_data:
            print("Small data", symbol, len(ret["t"]))
        tqdm_obj.set_postfix_str(f"{len(large_amount_of_data)}")
    print(len(large_amount_of_data))
    symbol_by_sectors = dict(symbol_by_sectors)
    dump(symbol_by_sectors, str(livermore_root / 'data/coarse_selection.json'), indent=2)


def check_days():
    # Some days are missing...
    for resolution in ["1m", "1d"]:
        days1 = stock_candle_db.query_candles("AAPL", candle_type=resolution)
        days2 = stock_candle_db.query_candles("GOOG", candle_type=resolution)
        
        time1 = [day.timestamp for day in days1]
        time2 = [day.timestamp for day in days2]
        print("AAPL", len(time1), len(set(time1)))
        if len(time1) > 0:
            print("AAPL", get_readable_time(time1[0]), get_readable_time(time1[-1]))
        print("GOOG", len(time2), len(set(time2)))
        print("GOOG", get_readable_time(time2[0]), get_readable_time(time2[-1]))
    
    exit(0)    
    # for resolution in ["30m", "1h", "2h", "3h", "4h", "1d"]:
    #     print(f"Delete {resolution}")
    stock_candle_db.delete_candles("AAPL", candle_type="1d")
    engine.update_recent_candles("AAPL")
    
    # def download_stock_candles(self, symbol, resolution, start_time, end_time=None):
    
    # stocks = engine.download_stock_candles("GOOG", 1, 1679923800, 1679923800 + 3600 * 12)
    # print(stocks)
    # stocks = stock_candle_db.query_candles("GOOG", 1679923800, 1679923800 + 3600 * 12, candle_type="1m")
    # print(len(stocks))
    # exit(0)
    
    for i in range(min(len(days1), len(days2))):
        if days1[i].timestamp != days2[i].timestamp:
            print(get_ny_time(days1[i].timestamp), get_ny_time(days1[i].timestamp).weekday(), get_ny_time(days2[i].timestamp), get_ny_time(days2[i].timestamp).weekday())
    # exit(0)
    
    for day in days2:
        if day.timestamp not in time1:
            print("Not in AAPL", day.timestamp, get_ny_time(day.timestamp),  get_ny_time(day.timestamp).weekday(), day.volume)
            
            
    for day in days1:
        if day.timestamp not in time2:
            print("Not in GOOG", day.timestamp, get_ny_time(day.timestamp), get_ny_time(day.timestamp).weekday(), day.volume)
    exit(0)


def scan_all_opotunities():
    # Check this week and next week's options
    
    symbols_by_sectors = load(str(livermore_root / 'data/coarse_selection.json'))
    symbols = []
    for name, value in symbols_by_sectors.items():
        symbols += value
    
    for symbol in symbols:
        engine.update_all_resolutions(symbol)
    
        



def scan_all_options():
    symbols_by_sectors = load(str(livermore_root / 'data/coarse_selection.json'))
    symbols = []
    for name, value in symbols_by_sectors.items():
        symbols += value
        
    ret = []
    for symbol in symbols:
        pass
        

if __name__ == '__main__':
    # import finnhub
    # finnhub_client = finnhub.Client(api_key="cu9bivpr01qnf5nmlh8gcu9bivpr01qnf5nmlh90")    
    today = datetime.now()
    # formatted_date = today.strftime('%Y%m%d')
    formatted_date = "20250206"
    engine = FinnhubEngine(api_key="cu9bivpr01qnf5nmlh8gcu9bivpr01qnf5nmlh90")

    timestamp = 1731508200
    # print(engine.download_stock_candles("AAPL", 1, timestamp, timestamp + 3600 * 1.0))
    # check_days()
    # scan_all_options()
    scan_all_opotunities()
    exit(0)
    
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
    