from mmengine import dump, load
from collections import defaultdict
from datetime import datetime
from IPython import embed
from tqdm import tqdm, trange

import numpy as np
import pickle

from livermore import livermore_root
from livermore.finnhub_engine import FinnhubEngine
from livermore.misc import get_last_time, get_readable_time, dump_pkl


if __name__ == "__main__":
    engine = FinnhubEngine(api_key="cu9bivpr01qnf5nmlh8gcu9bivpr01qnf5nmlh90")
    symbols_by_sectors = load(str(livermore_root / 'data/lingfeng_symbols.json'))
    symbols = []
    symbol_to_sector = defaultdict(list)
    for key, value in symbols_by_sectors.items():
        symbols += value
    symbols = sorted(set(symbols))
    print(len(symbols))
    date = datetime.now().strftime('%Y-%m-%d')
    
    ret = {}
    for i in trange(len(symbols)):
        symbol = symbols[i]
        ret[symbol] = engine.get_option_chain(symbol, date)
        if ret[symbol] is None:
            ret.pop(symbol)
        if i % 100 == 0 or i == len(symbols) - 1:
            dump_pkl(ret, livermore_root / f'data/options/{date}.pkl')
