from mmengine import dump, load
from tqdm import tqdm

from livermore import livermore_root
from livermore.finnhub_engine import FinnhubEngine
from livermore.misc import get_last_time, dump_pkl
from collections import defaultdict
import time, pickle


def update_basic_data(overwrite=True):
    history_folder = livermore_root / 'data/history_data'
    ret = {}
    for symbol in tqdm(sorted(set(symbols) | set(etfs))):
        # print(symbol)
        # filename = history_folder / f"{symbol}.json"
        # if filename.exists() and not overwrite:
        #     continue
        ret[symbol] = {
            "sector": symbol_to_sector[symbol],
            "etf_ratios": symbol_to_etf[symbol],
            "profile": engine.get_company_profile(symbol),
            "basic_financials": engine.get_company_basic_financials(symbol),
            "earnings": engine.get_company_earnings(symbol),
            "financials": engine.get_financials_reported(symbol),
        }
    dump_pkl(ret, livermore_root / "data/stock_infos.pkl")
    # dump(ret, livermore_root / "stock_infos.pkl", indent=2, ensure_ascii=False) 
    

def detect_etf_symbols(symbols):
    symbols = sorted(set(symbols))
    filename = livermore_root / 'data/stock_symbols.json'
    stocks = load(filename)
    stocks = {_["symbol"]: _ for _ in stocks}
    print(len(stocks))
    type_count = defaultdict(int)
    etf_by_sectors = defaultdict(list)
    etfs = []
    for symbol in symbols:
        assert symbol in stocks
        if stocks[symbol]["type"] == "ETP":
            for sector in symbol_to_sector[symbol]:
                etf_by_sectors[sector].append(symbol)
            etfs.append(symbol)
        type_count[stocks[symbol]["type"]] += 1
    dump(dict(etf_by_sectors), livermore_root / 'data/etf_by_sectors.json', indent=2)
    return etfs


if __name__ == "__main__":
    engine = FinnhubEngine(api_key="cu9bivpr01qnf5nmlh8gcu9bivpr01qnf5nmlh90")
    finnhub_client = engine.finnhub_client
    
    symbols_by_sectors = load(str(livermore_root / 'data/lingfeng_symbols.json'))
    symbols = []
    symbol_to_sector = defaultdict(list)
    for key, value in symbols_by_sectors.items():
        symbols += value
        for symbol in value:
            symbol_to_sector[symbol].append(key)
    etfs = detect_etf_symbols(symbols)
    
    symbols = sorted(set(symbols) - set(etfs))
    print(len(symbols), len(set(etfs)))

    symbol_to_etf = defaultdict(list)
    # etf_symbols = []
    for etf_filename in (livermore_root / 'data/ETF').glob("*.json"):
        etf_data = load(etf_filename)["holdings"]
        etf_name = etf_filename.name.split(".")[0]
        coverage = 0
        for item in etf_data:
            symbol = item["symbol"]
            weight = item["weight"]
            symbol_to_etf[symbol].append((etf_name, weight))
            if symbol in symbols:
                coverage += 1
        if len(etf_data) == 0:
            continue
        print(etf_name, coverage, len(etf_data), coverage / len(etf_data))
    print(len(symbol_to_etf), len(set(symbols) - set(symbol_to_etf.keys())))
    for symbol in symbols:
        if symbol not in symbol_to_etf:
            print(symbol)
    update_basic_data()
    