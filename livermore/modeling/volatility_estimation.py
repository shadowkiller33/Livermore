import pandas as pd, numpy as np


def to_pd_series(prices):
    if isinstance(prices, list):
        prices = pd.Series(prices)
    return prices


def realized_volatility(data, window=20, period=252):
    close_prices = to_pd_series(data["c"])
    log_returns = np.log(close_prices / close_prices.shift(1))
    def compute_rv(log_returns):
        mean_log_return = np.mean(log_returns)
        return np.sqrt((1 / (window - 1)) * np.sum((log_returns - mean_log_return) ** 2) - (1 / (window * (window - 1))) * (np.sum(log_returns)) ** 2)
    rv = log_returns.rolling(window=window).apply(compute_rv, raw=True)
    return rv * np.sqrt(period)


def parkinson_volatility(data, window=20, period=252):
    high_prices = to_pd_series(data["h"])
    low_prices = to_pd_series(data["l"])
    log_range_squared = np.log(high_prices / low_prices) ** 2
    average_log_range_squared = log_range_squared.rolling(window=window).mean()
    return np.sqrt(average_log_range_squared / (4 * np.log(2)) * period)


def garman_klass_volatility(data, window=20, period=252):
    data = {k: to_pd_series(data[k]) for k in ["o", "c", "h", "l"]}
    
    log_hl = np.log(data["h"] / data["l"])
    log_co = np.log(data["c"] / data["o"])
    term1 = 0.5 * log_hl ** 2
    term2 = (2 * np.log(2) - 1) * log_co ** 2
    gk_volatility = np.sqrt((term1 - term2).rolling(window=window).mean())
    return gk_volatility * np.sqrt(period)


def roger_satchell_volatility(data, window=20, period=252):
    data = {k: to_pd_series(data[k]) for k in ["o", "c", "h", "l"]}
    log_hc = np.log(data["h"] / data["c"])
    log_ho = np.log(data["h"] / data["o"])
    log_lc = np.log(data["l"] / data["c"])
    log_lo = np.log(data["l"] / data["o"])
    rs_term = log_hc * log_ho + log_lc * log_lo
    rs_volatility = np.sqrt(rs_term.rolling(window=window).mean())
    return rs_volatility * np.sqrt(period)


def yang_zhang_volatility(data, window=20, period=252):
    data = {k: to_pd_series(data[k]) for k in ["o", "c", "h", "l"]}
    
    log_ho = np.log(data['h'] / data['o'])
    log_lo = np.log(data['l'] / data['o'])
    log_co = np.log(data['c'] / data['o'])
    log_oc = np.log(data['o'] / data['c'].shift(1))
    log_cc = np.log(data['c'] / data['c'].shift(1))

    rs = log_ho * (log_ho - log_co) + log_lo * (log_lo - log_co)
    close_vol = log_cc ** 2
    open_vol = log_oc ** 2

    window_rs = rs.rolling(window=window).mean()
    window_close_vol = close_vol.rolling(window=window).mean()
    window_open_vol = open_vol.rolling(window=window).mean()
    k = 0.34 / (1.34 + (window + 1) / (window - 1))
    yang_zhang_vol = np.sqrt(window_open_vol + k * window_close_vol + (1 - k) * window_rs)
    annualized_yang_zhang_vol = yang_zhang_vol * np.sqrt(252)

    return annualized_yang_zhang_vol
