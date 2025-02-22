from mmengine import dump, load
from collections import defaultdict

from livermore.misc import get_readable_time, get_ny_time, time_to_seconds, get_last_time, process_database_results, plot_stock_candles, plot_multiple_stock_candles
from livermore.stock_candle_database import stock_candle_db
from livermore.signal_utils import compute_vegas_channel_and_signal
from livermore import livermore_root


def save_all_existing_symbols():
    """ Only keep US stocks """
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
    """ Save all company profiles """
    engine = FinnhubEngine()
    symbols = load(str(livermore_root / 'data/stock_symbols.json'))
    try:
        profiles = load(str(livermore_root / f'data/company_profiles_{formatted_date}.json'))
    except:
        profiles = {}
    for i in trange(len(symbols)):
        if symbols[i]["symbol"] in profiles:
            continue
        profile = engine.get_company_profile(symbols[i]["symbol"])
        profiles[symbols[i]["symbol"]] = profile
        if i % 50 == 0:
            dump(profiles, str(livermore_root / f'data/company_profiles_{formatted_date}.json'), indent=2)
    dump(profiles, str(livermore_root / f'data/company_profiles_{formatted_date}.json'), indent=2)


def save_forex_info():
    """ Save all forex info """
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
    """ Scan all large stocks """
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




def check_existing_stocks():
    """ Validate the exiting selected stocks by lingfeng """
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
    

if __name__ == "__main__":
    formatted_date = "20250206"
    symbols_by_sectors = load(str(livermore_root / 'data/coarse_selection.json'))
    symbols = []
    for name, value in symbols_by_sectors.items():
        symbols += value
    
    name_mapping = {
        "Tech": ["Technology", "Semiconductors", "Communications", "Telecommunication"],
        "Bio": ["Health Care", "Biotechnology", "Life Sciences Tools & Services", "Pharmaceuticals"],
        "Finance": ["Financial Services", "Banking", "Insurance"],
        "Utilities": ["Energy", "Utilities"],
        "Industrials": ["Aerospace & Defense", "Machinery", "Electrical Equipment", "Auto Components", "Automobiles"],
        "Retail": ["Retail", "Consumer products", "Textiles, Apparel & Luxury Goods", "Food Products", "Beverages"],
        "Real Estate": ["Real Estate", "Construction", "Building", "Commercial Services & Supplies"],
        "Transportation": ["Logistics & Transportation", "Road & Rail", "Trading Companies & Distributors", "Airlines"],
        "Entertainment": ["Media", "Hotels, Restaurants & Leisure"],
        "Materials": ["Chemicals", "Packaging", "Metals & Mining"],
        "ETF": ["ETF"],
        "Others": ["Tobacco", "Diversified Consumer Services", "Industrial Conglomerates", "Distributors", "Professional Services", ]
    }
    invsere_mapping = {}
    for key, value in name_mapping.items():
        for item in value:
            invsere_mapping[item] = key
    # assert set(invsere_mapping) == set(symbols_by_sectors), set(symbols_by_sectors) - set(invsere_mapping)
    
    remapped_symbols = defaultdict(list)
    for name, value in symbols_by_sectors.items():
        for symbol in value:
            remapped_symbols[invsere_mapping[name]].append(symbol)
    remapped_symbols = dict(remapped_symbols)
    print(len(remapped_symbols))
    dump(remapped_symbols, str(livermore_root / 'data/remapped_coarse_selection.json'), indent=2)
    # print(len(symbols), len(symbols_by_sectors))
    # profiles = load(str(livermore_root / f'data/large_companies_{formatted_date}.json'))
    # print(len(profiles), type(profiles))
    # exit(0)
    