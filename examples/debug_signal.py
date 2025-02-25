from mmengine import dump, load

import numpy as np
import pandas as pd
import bisect, time
from datetime import datetime

from livermore.misc import get_readable_time, get_ny_time, time_to_seconds, get_last_time, process_database_results, plot_stock_candles, plot_multiple_stock_candles
from livermore.stock_candle_database import stock_candle_db
from livermore.signal_utils import compute_vegas_channel_and_signal
from livermore.finnhub_engine import FinnhubEngine
from livermore import livermore_root
from collections import defaultdict
from copy import deepcopy
from tqdm import tqdm
from itertools import chain


def debug_plot():
    pass



if __name__ == "__main__":
    # period_end = time.time()
    # now = get_ny_time(period_end)
    # last_date = np.busday_offset(now.strftime('%Y-%m-%d'), -1, roll='backward')
    # last_date = last_date.astype(datetime)
    # delta_seconds = (now.date() - last_date).total_seconds()
    
    
    # print(now, delta_seconds  / 3600 / 24)
    # print(np.busday_offset(now.strftime('%Y-%m-%d'), -2, roll='backward'))
    # exit(0)
    
    
    # formatted_date = "20250206"
    engine = FinnhubEngine(api_key="cu9bivpr01qnf5nmlh8gcu9bivpr01qnf5nmlh90")
    # print(engine.get_recent_signals("NKE", num_days=16))
    
    symbol = "YANG"
    data = engine.query_candles_of_different_resolutions(symbol, num=200)
    image = plot_multiple_stock_candles(data, symbol, filename="tmp.png")
    image.close()
