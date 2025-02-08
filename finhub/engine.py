import requests
from dotenv import load_dotenv
import os
import time
import pandas as pd
import pytz
from datetime import datetime, time as dt_time
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
        if resolution in ['D', 'W', 'M']:
            # For daily, weekly, monthly data, calculate start_time accordingly
            if resolution == 'D':
                delta = count * 86400  # 1 day in seconds
            elif resolution == 'W':
                delta = count * 604800  # 1 week in seconds
            elif resolution == 'M':
                delta = count * 2629746  # 1 month in seconds (approximate)
            start_time = end_time - delta
        else:
            # For intra-day data, calculate based on resolution
            # Assuming 'count' represents the number of intervals
            seconds_per_interval = int(resolution) * 60  # e.g., 1 -> 60 seconds
            delta = count * seconds_per_interval
            start_time = end_time - delta

        if resolution not in ['D', 'W', 'M']:
            # need to request in for loop of 2week interval
            two_week_interval = 604800 * 4
            total_intervals = (count * int(resolution) * 60) // two_week_interval + 1
            data_frames = []
            for i in range(total_intervals):
                # Calculate the start and end times for each interval
                start_time = end_time - two_week_interval
                if start_time < 0:
                    start_time = 0  # Ensure start_time is not negative

                params = {
                    'symbol': symbol,
                    'resolution': resolution,
                    'from': start_time,
                    'to': end_time,
                    'token': self.api_key
                }

                response = self.session.get(HISTORICAL_PRICE_URL, params=params)
                response.raise_for_status()
                data = response.json()

                if data['s'] != 'ok':
                    raise ValueError(f"Error fetching historical data: {data.get('s')}")

                df = pd.DataFrame({
                    't': pd.to_datetime(data['t'], unit='s', utc=True),
                    'o': data['o'],
                    'h': data['h'],
                    'l': data['l'],
                    'c': data['c'],
                    'v': data['v']
                })

                if not df.empty:
                    df = self._filter_regular_trading_hours(df)
                    data_frames.append(df)

                # Update the end_time for the next batch
                end_time = start_time - 1  # Subtract 1 second to prevent overlap

                # Respect API rate limits
                # time.sleep(1)  # Adjust based on your subscription's rate limit
            df = pd.concat(data_frames).sort_values('t_et')            
        else:
            params = {
                'symbol': symbol,
                'resolution': resolution,
                'from': start_time,
                'to': end_time,
                'token': self.api_key
            }
            response = self.session.get(HISTORICAL_PRICE_URL, params=params)
            response.raise_for_status()
            data = response.json()
            if data['s'] != 'ok':
                raise ValueError(f"Error fetching historical data: {data.get('s')}")

            df = pd.DataFrame({
                't': pd.to_datetime(data['t'], unit='s', utc=True),
                'o': data['o'],
                'h': data['h'],
                'l': data['l'],
                'c': data['c'],
                'v': data['v']
            })        
        return df


    def _filter_regular_trading_hours(self, df):
        """
        Filters the DataFrame to include only data within regular trading hours (9:30 AM to 4:00 PM ET)
        and ensures the timestamps are in US/Eastern timezone.
        
        Parameters:
        - df (pd.DataFrame): DataFrame with a timezone-aware 't' column in UTC.
        
        Returns:
        - pd.DataFrame: Filtered DataFrame within regular trading hours in US/Eastern timezone.
        """
        # Define Eastern Time timezone
        eastern = pytz.timezone('US/Eastern')
    
        # Convert UTC timestamps to Eastern Time
        # Ensure 't' is datetime and timezone-aware
        if not pd.api.types.is_datetime64_any_dtype(df['t']):
            df['t'] = pd.to_datetime(df['t'], utc=True)
        else:
            if df['t'].dt.tz is None:
                df['t'] = df['t'].dt.tz_localize('UTC')
            else:
                df['t'] = df['t'].dt.tz_convert('UTC')
        
        # Create a new column 't_et' with Eastern Time
        df['t_et'] = df['t'].dt.tz_convert(eastern)

        # Set 't_et' as the new index
        df.set_index('t_et', inplace=True)

        # Define regular trading hours in Eastern Time
        market_open = dt_time(9, 30)
        market_close = dt_time(15, 30)

        # Filter data within trading hours
        filtered_df = df.between_time(market_open, market_close)

        # Optionally, drop the original UTC timestamp if not needed
        # This will leave the index in Eastern Time
        filtered_df = filtered_df.drop(columns=['t'], errors='ignore')

        # Optionally, rename the index to 't' for consistency
        filtered_df.index.name = 't_et'  # or 't' if preferred

        return filtered_df


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
        data = response.json()['data']
        filtered_data = [option for option in data if option.get('expirationDate') == expiration]
        return filtered_data
    

    


# test API engine
if __name__ == '__main__':
    engine = FinnhubEngine()
    quote = engine.get_stock_quote('AAPL')

    # for historical data, need subscription (48$ per month) from Finnhub
    historical_data = engine.get_historical_prices('NVDA', resolution='D', count=100)
    print(historical_data)

    # option_chain = engine.get_option_chain('AAPL', '2023-01-20')
    # print(option_chain)