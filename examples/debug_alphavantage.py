# import yfinance as yf
import pandas as pd
import requests
from mmengine import load, dump
from IPython import embed
from pathlib import Path


__this_folder__ = Path(__file__).parent
KEY = "5UL0AI6HXG5QFSCB"
folder = __this_folder__.parent / "livermore"
ETF_folder = folder / "data" / "ETF"


# url = 'https://www.alphavantage.co/query?function=ETF_PROFILE&symbol=QQQ&apikey=demo'
# r = requests.get(url)
# data = r.json()
# dump(data, ETF_folder / "qqq.json", indent=2)


# url = 'https://www.alphavantage.co/query?function=ETF_PROFILE&symbol=SPY&apikey=5UL0AI6HXG5QFSCB'
# r = requests.get(url)
# data = r.json()
# dump(data, ETF_folder / "spy.json", indent=2)

ETF = [
    "IWM",
    "XLP",
    "XLRE",
    "XLV",
    "XLI",
    "XLF",
    "XLC",
    "XLE",
    "XLK",
    "XLU",
    "XLB",
    "XLF",
    "XLY",
    "ITB",
    "XHB",
    "IYZ",
    "SOXX",
    "ITA",
    "KBE",
    "KRE"
]
for etf in ETF:
    url = f'https://www.alphavantage.co/query?function=ETF_PROFILE&symbol={etf}&apikey={KEY}'
    r = requests.get(url)
    data = r.json()
    dump(data, ETF_folder / f"{etf}.json", indent=2)
    print(etf)

exit(0)



# print(folder, ETF_folder, ETF_folder.exists())
# exit(0)

# url = 'https://www.alphavantage.co/query?function=HISTORICAL_OPTIONS&symbol=IBM&apikey=demo'
# r = requests.get(url)
# data = r.json()

# replace the "demo" apikey below with your own key from https://www.alphavantage.co/support/#api-key
# url = 'https://www.alphavantage.co/query?function=CRYPTO_INTRADAY&symbol=ETH&market=USD&interval=5min&apikey=demo'

# url = 'https://www.alphavantage.co/query?function=ETF_PROFILE&symbol=QQQ&apikey=demo'
# r = requests.get(url)
# data = r.json()
# dump(data, ETF_folder / "qqq.json", indent=2)


# url = 'https://www.alphavantage.co/query?function=ETF_PROFILE&symbol=SPY&apikey=5UL0AI6HXG5QFSCB'
# r = requests.get(url)
# data = r.json()
# dump(data, ETF_folder / "spy.json", indent=2)

url = 'https://www.alphavantage.co/query?function=OVERVIEW&symbol=IBM&apikey=demo'
r = requests.get(url)
data = r.json()

print(data)

embed()
