import time
import pandas as pd

from mmengine import dump, load
from tqdm import tqdm
from datetime import datetime

from livermore import livermore_root
from livermore.finnhub_engine import FinnhubEngine
from livermore.misc import get_last_time


def fetch_stock_splits():
    today = datetime.now()
    formatted_date = today.strftime('%Y-%m-%d')
    ret = {}
    for symbol in tqdm(symbols):
        ret[symbol] = engine.get_stock_splits(symbol, '2000-01-01', formatted_date)
    dump(ret, str(livermore_root / 'data/stock_splits.json'), indent=2)


def check_stock_splits():
    data = load(livermore_root / 'data/stock_splits.json')["data"]
    # print(data)
    # exit(0)
    print(len(data))
    template = "%Y-%m-%d"
    now = datetime.now()
    period_begin = now - pd.DateOffset(years=2)
    for symbol, splits in data.items():
        # print(symbol, len(splits))
        for split in splits:
            # print(split)
            split_time = datetime.strptime(split["date"], template)
            one_day_before = split_time - pd.DateOffset(days=4)
            one_day_after = split_time + pd.DateOffset(days=1)
            if split_time > period_begin:
                old_prices = engine.stock_candle_db.query_candles(symbol, start_time=one_day_before.timestamp(), end_time=split_time.timestamp() - 1, candle_type="1m")
                new_prices = engine.stock_candle_db.query_candles(symbol, start_time=split_time.timestamp(), end_time=one_day_after.timestamp(), candle_type="1m")
                print(len(old_prices), [_.close_price for _ in old_prices][-10:])
                print(len(new_prices), [_.close_price for _ in new_prices][:10])
                exit(0)
                # exit(0)


if __name__ == "__main__":
    engine = FinnhubEngine(api_key="cu9bivpr01qnf5nmlh8gcu9bivpr01qnf5nmlh90")
    symbols_by_sectors = load(str(livermore_root / 'data/lingfeng_symbols.json'))
    symbols = []
    for name, value in symbols_by_sectors.items():
        symbols += value
    symbols = sorted(set(symbols))
    # print(engine.get_stock_splits("SOXX"))
    # exit(0)
    engine.update_stock_splits(symbols)
    # check_stock_splits()

