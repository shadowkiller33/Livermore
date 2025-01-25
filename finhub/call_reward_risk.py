import requests
from dotenv import load_dotenv
import os
import time
import numpy as np
import pandas as pd
from datetime import datetime
from utils import black_scholes_price, black_scholes_probability_ITM
from utils import calculate_reward_ratio

# Finnhub API Key
load_dotenv()
API_KEY = os.getenv("FIN_TOKEN")

# Finnhub Option Chain Endpoint
OPTION_CHAIN_URL = "https://finnhub.io/api/v1/stock/option-chain"

RISK_FREE_RATE = 0.0463  # using current treasure found 10 year yield
# Function to retrieve option data
def get_option_data(symbol):
    params = {
        "symbol": symbol,
        "token": API_KEY
    }
    response = requests.get(OPTION_CHAIN_URL, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Error: {response.status_code}, {response.text}")



def compute_reward_risk(calls, target_price, risk_price, time_to_mature):
    """
        calls: {'contractName': 'AAPL250124C00100000', 'contractSize': 'REGULAR', 'contractPeriod': 'WEEKLY', 'currency': 'USD', 'type': 'CALL', 'inTheMoney': 'TRUE', 'lastTradeDateTime': '2025-01-20 00:12:42', 'expirationDate': '2025-01-24', 'strike': 100, 'lastPrice': 122.15, 'bid': 122.3, 'ask': 123.75, 'change': 122.15, 'changePercent': 0, 'volume': 1, 'openInterest': 4, 'impliedVolatility': 690.64, 'delta': 0.992, 'gamma': 0.0003, 'theta': -0.8927, 'vega': 0.0025, 'rho': 0.0026, 'theoretical': 123.03, 'intrinsicValue': -100.63, 'timeValue': 0, 'updatedAt': '2025-01-24 19:31:48', 'daysBeforeExpiration': 0}
    """
    strike_arr = []
    cur_price_arr = []
    iv_arr = []

    for i in range(len(calls)):
        call = calls[i]
        strike_price = call['strike']
        current_price = call['lastPrice'] # use last price as estimated price
        if current_price == 0 or call['volume'] < 1000:
            # too small to be considered
            continue
        strike_arr.append(strike_price)
        cur_price_arr.append(current_price)
        iv_arr.append(call['impliedVolatility'])
    strike_arr = np.array(strike_arr)
    cur_price_arr = np.array(cur_price_arr)
    iv_arr = np.array(iv_arr) / 100


    reward_risk_ratio, reward_ratio, risk_ratio = calculate_reward_ratio(
        S=target_price,
        S_low=risk_price,
        K=strike_arr,
        T=time_to_mature,
        r=RISK_FREE_RATE,
        sigma=iv_arr,
        option_type='call',
        current_option_price=cur_price_arr
    )
   
    return {
        'strike': strike_arr,
        'current_price': cur_price_arr,
        'reward_ratio': reward_ratio,
        'risk_ratio': risk_ratio,
        'reward//risk': reward_risk_ratio,
    }



symbol = "NVDA"
upperbound = 150
lowerbound = 138

try:
    option_data = get_option_data("NVDA")['data']  # Replace "AAPL" with your desired stock symbol

    for i in range(len(option_data)):
        cur_option = option_data[i]
        exp_date = cur_option['expirationDate']
        # compute time to maturality in years
        time_to_mature = (datetime.strptime(exp_date, "%Y-%m-%d") - datetime.now()).days + 1
        if time_to_mature < 7:
            continue

        time_to_mature = time_to_mature / 365
        option_contracts = cur_option['options']
        calls = option_contracts['CALL']
        # puts = option_contracts['PUT']
        result = compute_reward_risk(calls, upperbound, lowerbound, time_to_mature)
    
        # construct a dataframe to display the results above, with columns = ['strike', 'current_price', 'estimated_price', 'reward_rate']
        print("====================================")
        print(f"Option expiring on {exp_date}")
        df = pd.DataFrame(result)
        print(df)


        if i > 4:
            # only consider option exp within 1month
            break


except Exception as e:
    print(e)
    exit(0)