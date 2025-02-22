import requests
import os
import time
import pandas as pd
import pytz
import finnhub
import retrying
import numpy as np

from mmengine import dump, load
from pathlib import Path
from datetime import datetime, time as dt_time
from collections import defaultdict
from IPython import embed
from tqdm import tqdm, trange

from livermore.misc import get_readable_time, get_ny_time, time_to_seconds
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

    def get_stock_quote(self, symbol):
        return self.finnhub_client.quote(symbol)

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
    def get_stock_candles(self, symbol, resolution, start_time, end_time):
        assert resolution in [1, 5, 15, 30, 60, 'D', 'W', 'M']
        start_time = int(start_time)
        end_time = int(end_time)
        ret = self.finnhub_client.stock_candles(symbol, resolution, start_time, end_time)
        if "t" in ret and len(ret["t"]) > 0:
            indices = sorted(range(len(ret["t"])), key=lambda x: ret["t"][x])
            ret = {key: [ret[key][i] for i in indices] for key in ret}
        return ret
    
    def compute_stock_candles_of_a_interval(self, one_minute_data, start_time, resolution="1H"):
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
    
    def compute_stock_candles_of_a_resolution(self, one_minute_data, resolution="1H", working_hours_only=True):
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
        print(time.time() - st, pd.Timedelta(resolution))
    
        st = time.time()
        start_time = dt_time(9, 30)
        end_time = dt_time(16, 0)
        ret = defaultdict(list)
        i = 0
        while i < len(time_slots) and begin_time > get_ny_time(time_slots[i]):
            i +=1 
        while i < len(time_slots):
            end_time = begin_time + pd.Timedelta(resolution)
            # print(begin_time, i, pd.Timedelta(resolution))
            itme = defaultdict(list)
            while i < len(time_slots) and begin_time <= get_ny_time(time_slots[i]) < end_time:
                
                if working_hours_only:
                    ny_slot = get_ny_time(time_slots[i])
                    if ny_slot.weekday() >= 5 or not (dt_time(9, 30) < ny_slot.time() < dt_time(16, 0)):
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
            begin_time = end_time
        print(time.time() - st)
        return dict(ret)

    def get_stock_symbols(self):
        return self.finnhub_client.stock_symbols('US')
    
    @retrying.retry(stop_max_attempt_number=None, wait_fixed=10)
    def get_company_profile(self, symbol):
        return self.finnhub_client.company_profile2(symbol=symbol)
    
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


def clean_up_data():
    data = load(livermore_root / 'data/history_data' / "AAPL.json")
    ret = defaultdict(list)
    for item in data:
        for key in item:
            if key == "s":
                continue
            ret[key].extend(item[key])
    print(len(ret["t"]))
    dump(ret, livermore_root / 'data/processed_data' / "AAPL.json", indent=2)


if __name__ == '__main__':
    today = datetime.now()
    # formatted_date = today.strftime('%Y%m%d')
    formatted_date = "20250206"
    engine = FinnhubEngine(api_key="cu9bivpr01qnf5nmlh8gcu9bivpr01qnf5nmlh90")
    clean_up_data()
    
    # collect_all_symbol_history_info()
    
    # print(engine.get_option_chain('SPY', "25.2.21"))
    # print(get_ny_time())
    # scan_all_large_stocks()
    # exit(0)
    # filename = livermore_root / 'data/history_data' / "AAPL.json"
    # check_existing_symbols()
    # tmp1 = engine.get_stock_candles('SPY', 1, time.time() - 3600 * 24 * 30, time.time())
    
    # scan_all_company_profiles()
    # check_compute_stock_candles_of_a_interval()
    # tmp, tmp2 = load(filename)
    
    
    # print(tmp)
    # print(tmp2)
    
    exit(0)
    
    
    # engine = FinnhubEngine(api_key="cui4os9r01qooddtd9l0cui4os9r01qooddtd9lg")

    # print(get_ny_time())
    # symbols = load(str(livermore_root / 'data/stock_symbols.json'))
    
    # save_all_existing_symbols()
    
    # save_forex_info()
    # scan_all_large_stocks()
    # check_existing_symbols()
    # check_channel_ids()
    exit(0)
    
    
    quote = engine.get_stock_quote('AAPL')

    # for historical data, need subscription (48$ per month) from Finnhub
    historical_data = engine.get_historical_prices('NVDA', resolution='D', count=100)
    print(historical_data)

    # option_chain = engine.get_option_chain('AAPL', '2023-01-20')
    # print(option_chain)