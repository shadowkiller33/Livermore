from dotenv import load_dotenv
import os
import requests
import time
from datetime import datetime

# Finnhub API Key
load_dotenv()
API_KEY = os.getenv("FIN_TOKEN")


# Endpoint URL
FINNHUB_URL = "https://finnhub.io/api/v1/stock/candle"

def get_historical_data(symbol, resolution, start_date, end_date):
    """
    Fetch historical stock data from Finnhub.
    
    :param symbol: Stock ticker (e.g., 'AAPL').
    :param resolution: Candlestick resolution (e.g., '1', 'D', 'W').
    :param start_date: Start date in 'YYYY-MM-DD' format.
    :param end_date: End date in 'YYYY-MM-DD' format.
    :return: JSON response containing OHLCV data.
    """
    # Convert dates to Unix timestamps
    start_timestamp = int(time.mktime(datetime.strptime(start_date, "%Y-%m-%d").timetuple()))
    end_timestamp = int(time.mktime(datetime.strptime(end_date, "%Y-%m-%d").timetuple()))
    
    # Prepare request parameters
    params = {
        "symbol": symbol,
        "resolution": resolution,
        "from": start_timestamp,
        "to": end_timestamp,
        "token": API_KEY
    }
    
    # Send GET request
    response = requests.get(FINNHUB_URL, params=params)
    
    # Check for a successful response
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Error: {response.status_code}, {response.text}")

# Example Usage
symbol = "AAPL"
resolution = "D"  # Daily data
start_date = "2023-01-01"
end_date = "2023-12-31"

try:
    data = get_historical_data(symbol, resolution, start_date, end_date)
    print(data)
except Exception as e:
    print(e)


