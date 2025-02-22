from mmengine import dump, load

from livermore.misc import get_readable_time, get_ny_time, time_to_seconds, get_last_time, process_database_results, plot_stock_candles, plot_multiple_stock_candles
from livermore.stock_candle_database import stock_candle_db
from livermore.signal_utils import compute_vegas_channel_and_signal
from livermore import livermore_root


def check_compute_stock_candles_of_a_interval():
    tmp = engine.get_stock_candles('AAPL', 1, time.time() - 3600 * 24 * 30, time.time())
    tmp2 = engine.get_stock_candles('AAPL', "D", time.time() - 3600 * 24 * 30, time.time())
    tmp.pop("s")
    tmp2.pop("s")
    error = 0
    for i in trange(len(tmp2["t"])):
        res = engine.compute_stock_candles_of_a_interval(tmp, tmp2["t"][i], "H")
        if res != {key: value[i] for key, value in tmp2.items()}:
            error += 1
    print("Error rate", error / len(tmp2["t"]))


def collect_all_symbol_history_info():
    important_symbols_data = load(str(livermore_root / 'data/selected_sotcks.json'))
    important_symbols = []
    for key, value in important_symbols_data.items():
        important_symbols += value
    print(len(important_symbols))
    symbols = load(str(livermore_root / 'data/large_companies_20250206.json'))
    symbols = [_[0] for _ in symbols]
    print(len(symbols))
    symbols = sorted(set(symbols + important_symbols))
    print(len(symbols))
    
    time_stamp = int(time.time())
    for symbol in tqdm(symbols):
        if (livermore_root / f'data/history_data/{symbol}.json').exists():
            continue
        end_time = time_stamp
        ret = []
        for i in range(25):
            begin_time = end_time - 3600 * 24 * 30
            candles = engine.get_stock_candles(symbol, 1, begin_time, end_time)
            try:
                end_time = candles["t"][0] - 1
                ret.append(candles)
            except:
                break
        print(symbol, get_readable_time(end_time))
        dump(ret, str(livermore_root / f'data/history_data/{symbol}.json'), indent=2)


def prepare_existing_data():
    symbols_by_sectors = load(str(livermore_root / 'data/coarse_selection.json'))
    symbols = []
    for key, value in symbols_by_sectors.items():
        symbols += value
    print(len(symbols))
    exit(0)
    
    for symbol in tqdm(symbols):
        filename = livermore_root / f'data/history_data/{symbol}.json'
        data = load(filename)
        ret = defaultdict(list)
        for item in data:
            for key in item:
                if key == "s":
                    continue
                ret[key].extend(item[key])
        assert len(ret["t"]) == len(set(ret["t"]))
        symbol = filename.stem
        # engine.update_recent_candles(symbol)
        # print(symbol)
        engine.update_all_resolutions(symbol)
        # exit(0)


def reduce_stock_list():
    important_symbols_data = load(str(livermore_root / 'data/selected_sotcks.json'))
    # print(important_symbols_data)
    important_symbols = []
    for key, value in important_symbols_data.items():
        important_symbols += value
    print(len(important_symbols))
    
    profiles = load(str(livermore_root / f'data/company_profiles_{formatted_date}.json'))
    
    symbol_by_sectors = defaultdict(list)
    large_amount_of_data = []
    tqdm_obj = tqdm(sorted((livermore_root / 'data/history_data').glob("*.json")))
    for filename in tqdm_obj:
        data = load(filename)
        symbol = filename.stem
        ret = defaultdict(list)
        for item in data:
            for key in item:
                if key == "s":
                    continue
                ret[key].extend(item[key])
        if len(ret["t"]) > 10000:
            large_amount_of_data.append(symbol)
            category = profiles[symbol]["finnhubIndustry"] if symbol in profiles else "ETF"
            symbol_by_sectors[category].append(symbol)
        elif symbol in important_symbols_data:
            print("Small data", symbol, len(ret["t"]))
        tqdm_obj.set_postfix_str(f"{len(large_amount_of_data)}")
    print(len(large_amount_of_data))
    symbol_by_sectors = dict(symbol_by_sectors)
    dump(symbol_by_sectors, str(livermore_root / 'data/coarse_selection.json'), indent=2)


def check_days():
    # Some days are missing...
    for resolution in ["1m", "1d"]:
        days1 = stock_candle_db.query_candles("AAPL", candle_type=resolution)
        days2 = stock_candle_db.query_candles("GOOG", candle_type=resolution)
        
        time1 = [day.timestamp for day in days1]
        time2 = [day.timestamp for day in days2]
        print("AAPL", len(time1), len(set(time1)))
        if len(time1) > 0:
            print("AAPL", get_readable_time(time1[0]), get_readable_time(time1[-1]))
        print("GOOG", len(time2), len(set(time2)))
        print("GOOG", get_readable_time(time2[0]), get_readable_time(time2[-1]))
    
    exit(0)    
    # for resolution in ["30m", "1h", "2h", "3h", "4h", "1d"]:
    #     print(f"Delete {resolution}")
    stock_candle_db.delete_candles("AAPL", candle_type="1d")
    engine.update_recent_candles("AAPL")
    
    # def download_stock_candles(self, symbol, resolution, start_time, end_time=None):
    
    # stocks = engine.download_stock_candles("GOOG", 1, 1679923800, 1679923800 + 3600 * 12)
    # print(stocks)
    # stocks = stock_candle_db.query_candles("GOOG", 1679923800, 1679923800 + 3600 * 12, candle_type="1m")
    # print(len(stocks))
    # exit(0)
    
    for i in range(min(len(days1), len(days2))):
        if days1[i].timestamp != days2[i].timestamp:
            print(get_ny_time(days1[i].timestamp), get_ny_time(days1[i].timestamp).weekday(), get_ny_time(days2[i].timestamp), get_ny_time(days2[i].timestamp).weekday())
    # exit(0)
    for day in days2:
        if day.timestamp not in time1:
            print("Not in AAPL", day.timestamp, get_ny_time(day.timestamp),  get_ny_time(day.timestamp).weekday(), day.volume)
    for day in days1:
        if day.timestamp not in time2:
            print("Not in GOOG", day.timestamp, get_ny_time(day.timestamp), get_ny_time(day.timestamp).weekday(), day.volume)


if __name__ == '__main__':
    # import finnhub
    # finnhub_client = finnhub.Client(api_key="cu9bivpr01qnf5nmlh8gcu9bivpr01qnf5nmlh90")    
    today = datetime.now()
    # formatted_date = today.strftime('%Y%m%d')
    formatted_date = "20250206"
    engine = FinnhubEngine(api_key="cu9bivpr01qnf5nmlh8gcu9bivpr01qnf5nmlh90")

    # timestamp = 1731508200
    # print(engine.download_stock_candles("AAPL", 1, timestamp, timestamp + 3600 * 1.0))
    # check_days()
    # scan_all_options()
    # scan_all_opotunities()
    compute_all_opportunities()
    
    # data = load(str(livermore_root / 'data/existing_opportunities.json'))
    # for symbol, item in data.items():
    #     for resolution, value in item.items():
    #         value["num"] = len(value["buy_signal"])
    #         print(resolution, value["num"], len(value["buy_signal"]))
    # dump(data, str(livermore_root / 'data/existing_opportunities_test.json'), indent=2)
    # exit(0)
    
    # for resolution in ["30m", "1h", "2h", "3h", "4h", "1d"]:
    #     print(f"Delete {resolution}")
        # stock_candle_db.delete_all_candles_by_candle_type(resolution)
    # engine.update_recent_candles("AAPL")
    
    
    # symbols_by_sectors = load(str(livermore_root / 'data/coarse_selection.json'))
    # symbols = []
    # for key, value in symbols_by_sectors.items():
    #     symbols += value
    # for symbol in symbols:
    #     engine.update_recent_candles(symbol)
    exit(0)
    # engine.validate_candles("AAPL")
    # st = time.time()
    # data = engine.fetch_all_resolutions("AAPL", num=200)
    # print(time.time() - st)
    # print(data["30m"].keys())
    # print(data["1h"].keys())
    # exit(0)
    
    # for resolution in ["30m", "1h", "2h", "3h", "4h", "1d"]:
    #     for item in data[resolution]["t"][:5]:
    #         print(get_readable_time(item))
    #     print()
    # exit(0)
    resolution = "1d"
    # print(len(data[resolution]["t"]))
    
    signals = compute_vegas_channel_and_signal(data[resolution])
    image = plot_stock_candles(data[resolution], "AAPL", signals=signals, kline_type=resolution) #, filename=livermore_root / "data/tmp/test.png")
    # print(type(image))
    # exit(0)
    
    image = plot_multiple_stock_candles(data, "AAPL", filename=livermore_root / "data/tmp/test.png")
    