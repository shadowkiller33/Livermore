from mmengine import dump, load
from tqdm import tqdm

from livermore import livermore_root
from livermore.finnhub_engine import FinnhubEngine
from livermore.misc import get_last_time
import time


if __name__ == "__main__":
    engine = FinnhubEngine(api_key="cu9bivpr01qnf5nmlh8gcu9bivpr01qnf5nmlh90")
    # print(engine.finnhub_client.crypto_candles('BINANCE:BTC', 'D', 1590988249, 1591852249))
    # print(engine.finnhub_client.bond_price('US912810TD00', 1590988249, 1649099548))
    # print(engine.finnhub_client.price_target('AAPL'))
    # print(engine.finnhub_client.stock_investment_theme('financialExchangesData'))
    
    # print(engine.finnhub_client.financials_reported(symbol='AAPL', freq='annual'))
    # print(engine.finnhub_client.company_earnings('TSLA', limit=5))
    # print(engine.finnhub_client.company_basic_financials('AAPL', 'all'))
