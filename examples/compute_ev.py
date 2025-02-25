from mmengine import dump, load
from datetime import datetime

import numpy as np
import pandas as pd
import bisect

from livermore.misc import get_readable_time, get_ny_time, time_to_seconds, get_last_time, process_database_results, plot_stock_candles, plot_multiple_stock_candles
from livermore.finnhub_engine import FinnhubEngine
from livermore.stock_candle_database import stock_candle_db
from livermore.signal_utils import compute_vegas_channel_and_signal
from livermore import livermore_root
from collections import defaultdict
from copy import deepcopy
from tqdm import tqdm
from itertools import chain


def find_good_signals(symbol, signals, candles, max_percentail=90):
    # There are 3 in 1d, 4h, 3h, 2h, 1h signals
    timstamp_to_signals = {}
    good_resolutions = ["1d", "4h", "3h", "2h", "1h"]
    for resolution in good_resolutions:
        if resolution not in signals:
            continue
        for signal in signals[resolution]:
            signal = int(signal)
            if signal not in timstamp_to_signals:
                timstamp_to_signals[signal] = []
            timstamp_to_signals[signal].append(resolution)
    timestamps = sorted(timstamp_to_signals.keys())
    # print(len(timestamps))
    # print(sum([len(value) for value in timstamp_to_signals.values()]))
    time_30m = candles["t"]
    prices_30m = candles["c"]
    
    def get_price_between_time(start_time, end_time):
        # We want to get the price between start_time and end_time, the time should be in [start_time, end_time)!
        start_index = bisect.bisect_left(time_30m, start_time)
        end_index = bisect.bisect_left(time_30m, end_time)
        return prices_30m[start_index:end_index]
    
    st = end = 0
    period = 3600 * 24
    signals_in_period = defaultdict(list)
    good_opportunities = []
    last_signal = None
    for i in range(len(timestamps)):
        now = get_ny_time(timestamps[i])
        last_date = np.busday_offset(now.strftime('%Y-%m-%d'), -1, roll='backward')
        last_date = last_date.astype(datetime)
        delta_seconds = (now.date() - last_date).total_seconds()
        st_period = timestamps[i] - delta_seconds
        while st < i and timestamps[st] < st_period:
            for signal in timstamp_to_signals[timestamps[st]]:
                signals_in_period[signal].remove(timestamps[st])
            st += 1
        for signal in timstamp_to_signals[timestamps[i]]:
            signals_in_period[signal].append(timestamps[i])
            # while end < len(timestamps) and timestamps[end] < timestamps[i] + end_period:
        #     for signal in timstamp_to_signals[timestamps[end]]:
        #         signals_in_period[signal].append(timestamps[end])
        #     end += 1
        num_signals = {key: len(value) for key, value in signals_in_period.items() if len(value) > 0}
        num_good_signals = {key: value for key, value in num_signals.items() if key in good_resolutions}
        if len(num_good_signals) < 3 and not ("1d" in num_good_signals or "4h" in num_good_signals):
            continue
        max_timestamp_after_signals = max([max(value) for value in signals_in_period.values() if len(value) > 0])
        # print(len(num_good_signals), num_signals, max_timestamp_after_signals)
        
        for resolution in reversed(good_resolutions):
            if resolution not in num_signals or len(signals_in_period[resolution]) == 0:
                continue
            prices_resolutions = []
            for timestamp in signals_in_period[resolution]:
                prices = get_price_between_time(timestamp, timestamp + time_to_seconds(resolution))
                prices_resolutions.append(max(prices))
            avg_buy_prices = np.mean(prices_resolutions)    
            break
        
        revenue = {}
        for waiting_time in [7, 14, 21]:
            prices_in_two_weeks = get_price_between_time(max_timestamp_after_signals, max_timestamp_after_signals + 3600 * 24 * waiting_time)
            best_sell_price = np.percentile(prices_in_two_weeks, max_percentail)
            revenue[waiting_time] = float(round((best_sell_price - avg_buy_prices) / avg_buy_prices * 100, 2))
        if last_signal is not None and (get_ny_time(timestamps[i]) - get_ny_time(last_signal)).total_seconds() < 3600 * 24:
            continue
        last_signal = timestamps[i]
        # print(symbol, get_readable_time(timestamps[i]), len(num_signals), sorted(num_signals.keys()), len(num_good_signals), revenue)
        good_opportunities.append({
            "readable_time": get_readable_time(timestamps[i]),
            "timestamp": timestamps[i],
            "num_signals": len(num_signals),
            "num_good_signals": len(num_good_signals),
            "signals_in_period": deepcopy({key: value for key, value in signals_in_period.items() if len(value) > 0}),
            "revenue": revenue
        })
    return good_opportunities


if __name__ == "__main__":
    formatted_date = "20250206"
    engine = FinnhubEngine(api_key="cu9bivpr01qnf5nmlh8gcu9bivpr01qnf5nmlh90")
    
    lingfeng_selections = load(str(livermore_root / 'data/selected_sotcks.json'))
    lingfeng_selections = list(chain(*lingfeng_selections.values()))
    symbols_by_sectors = load(str(livermore_root / 'data/coarse_selection.json'))
    currency_map = load(str(livermore_root / f'data/currencies_map_{formatted_date}.json'))
    company_profiles = load(str(livermore_root / f'data/company_profiles_{formatted_date}.json'))
    opportunities = load(str(livermore_root / 'data/existing_opportunities.json'))
    
    symbols = []
    for name, value in symbols_by_sectors.items():
        symbols += value
    symbols = sorted(symbols, key=lambda x: 1E20 if x not in company_profiles else company_profiles[x]["marketCapitalization"] * currency_map[company_profiles[x]["currency"]] / 1000, reverse=True)
    
    opportunities = {}
    win_rate_by_sector, avg_revenue_by_sector = defaultdict(list), defaultdict(list)
    win_rate_by_signal, avg_revenue_by_signal = defaultdict(list), defaultdict(list)
    win_rate_by_month, avg_revenue_by_month = defaultdict(list), defaultdict(list)
    total_revenue, total_win_rate = [], []
    
    
    for symbol in tqdm(symbols):
        # if symbol != "YANG":
        #     continue
        # print(symbol)
        candles = engine.query_candles_of_different_resolutions(symbol, num=None, last_time=None)["30m"]
        signals = engine.get_all_existing_signals(symbol)
        symbol_opportunitiy = find_good_signals(symbol, signals, candles)
        opportunities[symbol] = {
            "sector": company_profiles[symbol]["finnhubIndustry"] if symbol in company_profiles else "ETF",
            "opportunities": symbol_opportunitiy
        }
    # exit(0)
    dump(opportunities, str(livermore_root / 'data/existing_opportunities.json'), indent=2)
    
    opportunities = load(str(livermore_root / 'data/existing_opportunities.json'))
    name_mapping = {
        "Tech": ["Technology", "Semiconductors", "Communications", "Telecommunication"],
        "Bio": ["Health Care", "Biotechnology", "Life Sciences Tools & Services", "Pharmaceuticals"],
        "Finance": ["Financial Services", "Banking", "Insurance"],
        "Utilities": ["Energy", "Utilities"],
        "Industrials": ["Aerospace & Defense", "Machinery", "Electrical Equipment", "Auto Components", "Automobiles"],
        "Retail": ["Retail", "Consumer products", "Textiles, Apparel & Luxury Goods", "Food Products", "Beverages"],
        "Real Estate": ["Real Estate", "Construction", "Building", "Commercial Services & Supplies"],
        "Transportation": ["Logistics & Transportation", "Road & Rail", "Trading Companies & Distributors", "Airlines"],
        "Entertainment": ["Media", "Hotels, Restaurants & Leisure"],
        "Materials": ["Chemicals", "Packaging", "Metals & Mining"],
        "ETF": ["ETF"],
        "Others": ["Tobacco", "Diversified Consumer Services", "Industrial Conglomerates", "Distributors", "Professional Services", ]
    }
    invsere_mapping = {}
    for key, value in name_mapping.items():
        for item in value:
            invsere_mapping[item] = key
    trash_company = lingfeng_count = 0
    ratio = 0
    current_month = get_ny_time(get_last_time()).strftime("%Y-%m")
    recent_opportunity = []
    
    for symbol in opportunities:
        symbol_opportunitiy = opportunities[symbol]["opportunities"]
        sector = invsere_mapping[opportunities[symbol]["sector"]]
        if len(symbol_opportunitiy) == 0:
            continue
        
        revenue = [max(item["revenue"].values()) for item in symbol_opportunitiy]
        win_rate = [max(item["revenue"].values()) > 0 for item in symbol_opportunitiy]
        if max(revenue) < 5 or np.mean(revenue) < 0:
            trash_company += 1
            continue
        if symbol in lingfeng_selections:
            lingfeng_count += 1
        
        for item in symbol_opportunitiy:
            timestamp = get_ny_time(item["timestamp"]).strftime("%Y-%m")
            item_revenue = max(item["revenue"].values())
            win_rate_by_month[timestamp].append(item_revenue > 0)
            avg_revenue_by_month[timestamp].append(item_revenue)
            if timestamp == current_month:
                recent_opportunity.append([item["readable_time"], symbol, item["signals_in_period"], item["revenue"]])
        
        for item in symbol_opportunitiy:
            signals_in_period = item["signals_in_period"]
            signal = tuple(sorted(signals_in_period.keys()))
            win_rate_by_signal[signal].append(max(item["revenue"].values()) > 0)
            avg_revenue_by_signal[signal].append(max(item["revenue"].values()))
        
        win_rate_by_sector[sector].extend(win_rate)
        avg_revenue_by_sector[sector].extend(revenue)
        
        total_revenue.extend(revenue)
        total_win_rate.extend(win_rate)
    
    recent_opportunity = sorted(recent_opportunity, key=lambda x: x[0])
    for item in recent_opportunity:
        # print(item[-1])
        # if item[-1]["7"] > 5:
        print(*item)
    exit(0)
        
        
    np.set_printoptions(precision=2, suppress=True)
    print("Non Trash Company:", len(opportunities) - trash_company, "10B Ration:", 1 - trash_company / len(opportunities), "Lingfeng Selections:", lingfeng_count, lingfeng_count / len(lingfeng_selections))
    print(f"Average - {len(total_revenue)} - RV: {np.mean(total_revenue):.2f}, Win Rate: {np.mean(total_win_rate):.2f}")
    for sector in win_rate_by_sector:
        print(f"{sector} - {len(win_rate_by_sector[sector])} - RV: {np.mean(avg_revenue_by_sector[sector]):.2f}, Win Rate: {np.mean(win_rate_by_sector[sector]):.2f}")
    for signal in sorted(win_rate_by_signal.keys()):
        print(f"{signal} - {len(avg_revenue_by_signal[signal])} - RV: {np.mean(avg_revenue_by_signal[signal]):.2f}, Win Rate: {np.mean(win_rate_by_signal[signal]):.2f}")
    for month in sorted(win_rate_by_month.keys()):
        print(f"{month} - {len(win_rate_by_month[month])} - RV: {np.mean(avg_revenue_by_month[month]):.2f}, Win Rate: {np.mean(win_rate_by_month[month]):.2f}")        
