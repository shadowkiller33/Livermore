from mmengine import dump, load

from livermore.misc import get_readable_time, get_ny_time, time_to_seconds, get_last_time, process_database_results, plot_stock_candles, plot_multiple_stock_candles
from livermore.stock_candle_database import stock_candle_db
from livermore.signal_utils import compute_vegas_channel_and_signal
from livermore import livermore_root


def scan_all_opotunities():
    # Check this week and next week's options
    ret = {}
    for symbol in tqdm(symbols):
        data, signals = {}, {}
        for resolution in resolutions:
            data[resolution] = process_database_results(stock_candle_db.query_candles(symbol, candle_type=resolution))
            signals[resolution] = compute_vegas_channel_and_signal(data[resolution])
        item = {}
        for resolution in resolutions:
            t = data[resolution]["t"]
            buy_signal = signals[resolution]["buy_signal"]
            item[resolution] = {
                "num": sum(buy_signal),
                "buy_signal": [t[i] for i, flag in enumerate(buy_signal) if flag],
            }
        ret[symbol] = item
    dump(ret, str(livermore_root / 'data/existing_opportunities.json'), indent=2)


def compute_all_opportunities():
    def check_all_signals(opportunity):
        base_times = opportunity["4h"]["buy_signal"]
        ret = []
        for base_4h in base_times:
            base_4h = get_ny_time(base_4h)
            base_all = []
            all_signal = True
            for resolution in ["1h", "2h", "3h"]:
                found = False
                for tt in opportunity[resolution]["buy_signal"]:
                    tt = get_ny_time(tt)
                    if tt - base_4h < pd.Timedelta("1d") and base_4h - tt < pd.Timedelta("1d"):
                        found = True
                        break
                if not found:
                    all_signal = False
                    break
            if all_signal:
                ret.append(base_4h)
        return ret
    avg_num = {}
    total_num = 0
    for sector_name, symbols in symbols_by_sectors.items():
        avg_num_sector = []
        best = [] 
        for symbol in symbols:
            opportunity = opportunities[symbol]
            tmp = check_all_signals(opportunity)
            avg_num_sector.append(len(tmp))
            total_num += len(tmp) > 0
        avg_num[sector_name] = np.mean(avg_num_sector)
    avg_num = dict(sorted(avg_num.items(), key=lambda x: x[1], reverse=True))
    for key, value in avg_num.items():
        print(key, value)


if __name__ == "__main__":
    symbols_by_sectors = load(str(livermore_root / 'data/coarse_selection.json'))
    currency_map = load(str(livermore_root / f'data/currencies_map_{formatted_date}.json'))
    company_profiles = load(str(livermore_root / f'data/company_profiles_{formatted_date}.json'))
    opportunities = load(str(livermore_root / 'data/existing_opportunities.json'))
    
    symbols = []
    for name, value in symbols_by_sectors.items():
        symbols += value
    symbols = sorted(symbols, key=lambda x: 1E20 if x not in company_profiles else company_profiles[x]["marketCapitalization"] * currency_map[company_profiles[x]["currency"]] / 1000, reverse=True)
    resolutions = ["30m", "1h", "2h", "3h", "4h", "1d"]
    compute_all_opportunities()
