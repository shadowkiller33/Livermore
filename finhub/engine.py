import requests
from dotenv import load_dotenv
import os
import time
import pandas as pd

# Finnhub API Key
load_dotenv()
API_KEY = os.getenv("FIN_TOKEN")

# Finnhub Option Chain Endpoint

OPTION_CHAIN_URL = "https://finnhub.io/api/v1/stock/option-chain"
QUOTE_URL = "https://finnhub.io/api/v1/quote"
HISTORICAL_PRICE_URL = "https://finnhub.io/api/v1/stock/candle"


class FinnhubEngine:
    def __init__(self, api_key=API_KEY):
        self.api_key = api_key
        self.session = requests.Session()
        self.session.params = {'token': self.api_key}

    def get_stock_quote(self, symbol):
        """
        Retrieve real-time quote for a given stock symbol.
        
        Parameters:
        - symbol (str): Stock ticker symbol.
        
        Returns:
        - dict: Real-time quote data.
        """
        params = {'symbol': symbol}
        response = self.session.get(QUOTE_URL, params=params)
        response.raise_for_status()
        return response.json()
    
    def get_historical_prices(self, symbol, resolution='D', count=100):
        """
        Retrieve historical stock prices.
        
        Parameters:
        - symbol (str): Stock ticker symbol.
        - resolution (str): Time resolution (1, 5, 15, 30, 60, D, W, M).
        - count (int): Number of data points.
        
        Returns:
        - pd.DataFrame: Historical price data.
        """
        end_time = int(time.time())
        start_time = end_time - count * 86400  # Approximate for daily data
        params = {
            'symbol': symbol,
            'resolution': resolution,
            'from': start_time,
            'to': end_time
        }
        response = self.session.get(HISTORICAL_PRICE_URL, params=params)
        response.raise_for_status()
        data = response.json()
        if data['s'] != 'ok':
            raise ValueError(f"Error fetching historical data: {data.get('s')}")
        df = pd.DataFrame({
            't': pd.to_datetime(data['t'], unit='s'),
            'o': data['o'],
            'h': data['h'],
            'l': data['l'],
            'c': data['c'],
            'v': data['v']
        })
        return df

    def get_option_chain(self, symbol, expiration):
        """
        Retrieve option chain for a given stock symbol and expiration date.
        
        Parameters:
        - symbol (str): Stock ticker symbol.
        - expiration (str): Expiration date in 'YYYY-MM-DD' format.
        
        Returns:
        - dict: Option chain data.
        """
        params = {'symbol': symbol, 'expiration': expiration}
        response = self.session.get(OPTION_CHAIN_URL, params=params)
        response.raise_for_status()
        return response.json()['data']
    

    


# test API engine
if __name__ == '__main__':
    engine = FinnhubEngine()
    quote = engine.get_stock_quote('AAPL')

    # for historical data, need subscription (48$ per month) from Finnhub
    # historical_data = engine.get_historical_prices('AAPL', resolution='D', count=100)
    # print(historical_data)

    option_chain = engine.get_option_chain('AAPL', '2023-01-20')
    print(option_chain)