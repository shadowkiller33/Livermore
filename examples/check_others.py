from mmengine import dump, load
from tqdm import tqdm

from livermore import livermore_root
from livermore.finnhub_engine import FinnhubEngine
from livermore.misc import get_last_time
import time


if __name__ == "__main__":
    engine = FinnhubEngine(api_key="cu9bivpr01qnf5nmlh8gcu9bivpr01qnf5nmlh90")
    finnhub_client = engine.finnhub_client
    # print(engine.finnhub_client.crypto_candles('BINANCE:BTC', 'D', 1590988249, 1591852249))
    # print(engine.finnhub_client.bond_price('US912810TD00', 1590988249, 1649099548))
    # print(engine.finnhub_client.price_target('AAPL'))
    # print(engine.finnhub_client.stock_investment_theme('financialExchangesData'))
    # print(finnhub_client.financials('AAPL', 'bs', 'annual'))
    
    # print(engine.finnhub_client.financials_reported(symbol='AAPL', freq='quarterly')) Get financials as reported. This data is available for bulk download on Kaggle SEC Financials database.
    # print(engine.finnhub_client.company_earnings('TSLA') # Get company historical quarterly earnings surprise going back to 2000.
    # print(engine.finnhub_client.company_basic_financials('AAPL', 'all'))  # Get company basic financials such as margin, P/E ratio, 52-week high/low etc.
    exit(0)
