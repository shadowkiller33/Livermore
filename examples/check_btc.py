from mmengine import dump, load
from tqdm import tqdm

from livermore import livermore_root
from livermore.finnhub_engine import FinnhubEngine
from livermore.misc import get_last_time
import time


if __name__ == "__main__":
    engine = FinnhubEngine(api_key="cu9bivpr01qnf5nmlh8gcu9bivpr01qnf5nmlh90")
    # print(engine.finnhub_client.crypto_candles('BINANCE:BTC', 'D', 1590988249, 1591852249))
    print(engine.finnhub_client.bond_price('US912810TD00', 1590988249, 1649099548))

