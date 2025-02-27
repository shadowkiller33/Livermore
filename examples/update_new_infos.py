from mmengine import dump, load
from tqdm import tqdm

from livermore import livermore_root
from livermore.finnhub_engine import FinnhubEngine
from livermore.misc import get_last_time
import time


def update_new_data():
    symbols_by_sectors = load(str(livermore_root / 'data/lingfeng_symbols.json'))
    symbols = []
    for key, value in symbols_by_sectors.items():
        symbols += value
    print(len(symbols))
    
    for symbol in tqdm(symbols):
        oldest_time = 3600 * 24 * 365 * 2
        try:
            signals = engine.get_recent_signals(symbol)
        except Exception as e:
            print(symbol)
    

if __name__ == "__main__":
    engine = FinnhubEngine(api_key="cu9bivpr01qnf5nmlh8gcu9bivpr01qnf5nmlh90")
    
    update_new_data()
