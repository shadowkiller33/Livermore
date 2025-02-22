import pandas as pd

def compute_ema(df: pd.DataFrame, lookback: int, price_column: str = 'c') -> pd.Series:
    """
    Compute the Exponential Moving Average (EMA) for a specified price column in a DataFrame.

    Parameters:
    - df (pd.DataFrame): DataFrame containing historical stock data.
    - lookback (int): The lookback period for calculating the EMA.
    - price_column (str): The column name for the price data (default is 'c' for closing price).

    Returns:
    - pd.Series: A pandas Series containing the EMA values.
    """
    if price_column not in df.columns:
        raise ValueError(f"Column '{price_column}' does not exist in the DataFrame.")

    ema = df[price_column].ewm(span=lookback, adjust=False).mean()
    return ema


if __name__ == "__main__":
    kline_data_example = [
        # (open, close, high, low)
        (100.0, 101.0, 102.0, 99.0),
        (101.5, 102.2, 103.0, 100.5),
        (102.2, 101.7, 103.6, 101.0),
        (101.2, 103.5, 105.0, 100.8),
        (103.2, 102.8, 104.0, 102.0),
        (102.9, 103.1, 103.6, 101.2),
        (103.0, 102.0, 103.4, 101.5),
        (103.4, 120.5, 102.2, 103.4),
        (119, 139.8, 141.0, 118.5),
        (129, 150.1, 117.5, 153.0),
    ]
    df = pd.DataFrame(kline_data_example, columns=['o', 'c', 'h', 'l'])
    print(df)
    out = compute_ema(df, lookback=5)
    print(out)