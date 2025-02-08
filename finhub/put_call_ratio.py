import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from engine import FinnhubEngine  # using your existing engine

def get_nearest_friday():
    """
    Returns the nearest Friday date as a string in 'YYYY-MM-DD' format.
    If today is Friday and the current time is after 4:00 PM local time,
    then it returns the next Friday.
    """
    now = datetime.now()
    # Friday is weekday 4 (Monday is 0, Sunday is 6)
    days_ahead = 4 - now.weekday()
    if days_ahead < 0:
        days_ahead += 7
    # If today is Friday, check if current time is after 4:00 PM.
    if days_ahead == 0 and now.hour >= 16:
        days_ahead = 7
    nearest_friday = now + timedelta(days=days_ahead)
    return nearest_friday.strftime('%Y-%m-%d')


def analyze_option_chain(symbol, expiration, output_path='temp_plot.png'):
    engine = FinnhubEngine()
    
    # Retrieve the option chain data from Finnhub API.
    # The API returns a dictionary with overall stats and an "options" list for individual strikes.
    try:
        option_chain_data = engine.get_option_chain(symbol, expiration)
    except Exception as e:
        print(f"Error retrieving option chain data: {e}")
        return

    # If the returned data is wrapped in a list, extract the dictionary.
    if isinstance(option_chain_data, list) and len(option_chain_data) == 1:
        option_chain_data = option_chain_data[0]
    
    # Use the provided overall volumes and ratio directly.
    # option has keys: ['expirationDate', 'impliedVolatility', 'putVolume', 'callVolume', 'putCallVolumeRatio', 'putOpenInterest', 'callOpenInterest', 'putCallOpenInterestRatio', 'optionsCount', 'options']

    overall_call_volume = option_chain_data.get('callVolume')
    overall_put_volume = option_chain_data.get('putVolume')
    overall_volume_ratio = option_chain_data.get('putCallVolumeRatio')

    overall_call_open_interest = option_chain_data.get('callOpenInterest')
    overall_put_open_interest = option_chain_data.get('putOpenInterest')
    overall_open_interest_ratio = option_chain_data.get('putCallOpenInterestRatio')

    # print(f"Overall call volume: {overall_call_volume}")
    # print(f"Overall put volume: {overall_put_volume}")
    # print(f"Overall put/call volume ratio: {overall_volume_ratio}\n")
    # print(f"Overall call open interest: {overall_call_open_interest}")
    # print(f"Overall put open interest: {overall_put_open_interest}")
    # print(f"Overall put/call open interest ratio: {overall_open_interest_ratio}")

    # Extract the options list for the strike distribution.
    call_list = option_chain_data['options']['CALL']
    put_list = option_chain_data['options']['PUT']
    # dict_keys(['contractName', 'contractSize', 'contractPeriod', 'currency', 'type', 'inTheMoney', 'lastTradeDateTime', 'expirationDate', 'strike', 'lastPrice', 'bid', 'ask', 'change', 'changePercent', 'volume', 'openInterest', 'impliedVolatility', 'delta', 'gamma', 'theta', 'vega', 'rho', 'theoretical', 'intrinsicValue', 'timeValue', 'updatedAt', 'daysBeforeExpiration'])
    # Extract the option lists for the strike distribution.

    # Convert lists to DataFrames.
    call_df = pd.DataFrame(call_list)
    put_df = pd.DataFrame(put_list)

    # Convert 'strike' and 'volume' to numeric.
    for col in ['strike', 'volume']:
        if col in call_df.columns:
            call_df[col] = pd.to_numeric(call_df[col], errors='coerce')
        if col in put_df.columns:
            put_df[col] = pd.to_numeric(put_df[col], errors='coerce')

    # Drop rows with missing strike values and sort by strike.
    call_df.dropna(subset=['strike', 'volume'], inplace=True)
    put_df.dropna(subset=['strike', 'volume'], inplace=True)
    call_df.sort_values('strike', inplace=True)
    put_df.sort_values('strike', inplace=True)

    # Filter out strikes with very small volume.
    # Here, we filter out rows where volume is less than 10% of the maximum volume on that side.
    call_threshold = 0.05 * call_df['volume'].max()
    put_threshold = 0.05 * put_df['volume'].max()
    call_df_filtered = call_df[call_df['volume'] >= call_threshold].copy()
    put_df_filtered = put_df[put_df['volume'] >= put_threshold].copy()

    # Compute the weighted mean strike price for calls and puts.
    if call_df_filtered['volume'].sum() > 0:
        mean_strike_call = (call_df_filtered['strike'] * call_df_filtered['volume']).sum() / call_df_filtered['volume'].sum()
    else:
        mean_strike_call = np.nan

    if put_df_filtered['volume'].sum() > 0:
        mean_strike_put = (put_df_filtered['strike'] * put_df_filtered['volume']).sum() / put_df_filtered['volume'].sum()
    else:
        mean_strike_put = np.nan

    print(f"Weighted mean strike price (Call): {mean_strike_call:.2f}")
    print(f"Weighted mean strike price (Put): {mean_strike_put:.2f}")

    # Merge the filtered DataFrames on strike.
    merged_df = pd.merge(call_df_filtered[['strike', 'volume']], 
                         put_df_filtered[['strike', 'volume']], 
                         on='strike', 
                         how='outer', 
                         suffixes=('_call', '_put'))
    merged_df.fillna(0, inplace=True)
    merged_df.sort_values('strike', inplace=True)

    # Plot both call and put volumes on the same plot as a grouped bar chart.
    fig, ax = plt.subplots(figsize=(12, 6))
    
    x = merged_df['strike'].values
    width = 0.4  # Width of each bar

    bars_call = ax.bar(x - width/2, merged_df['volume_call'], width=width, color='blue', alpha=0.7, label='Call Volume')
    bars_put = ax.bar(x + width/2, merged_df['volume_put'], width=width, color='red', alpha=0.7, label='Put Volume')
    
    ax.set_xlabel("Strike Price")
    ax.set_ylabel("Volume")
    ax.set_title(f"{symbol} Option Volume Distribution for Expiration {expiration}\n"
                 f"Overall Volume Ratio (Put/Call): {overall_volume_ratio}\n"
                 f"Overall Open Interest Ratio (Put/Call): {overall_open_interest_ratio}")
    # Set x-ticks to be 5-spaced.
    min_strike = merged_df['strike'].min()
    max_strike = merged_df['strike'].max()
    # Create tick marks every 5 units. Adjust the start so it's a multiple of 5.
    tick_start = np.floor(min_strike / 5) * 5
    tick_end = np.ceil(max_strike / 5) * 5
    xticks = np.arange(tick_start, tick_end + 1, 5)
    ax.set_xticks(xticks)
    ax.set_xticklabels([str(int(tick)) for tick in xticks], rotation=45, ha='right')
    
    # Optionally, mark the weighted mean strike prices with vertical lines.
    ax.axvline(mean_strike_call, color='blue', linestyle='--', linewidth=1.5,
               label=f'Call Mean Strike ({mean_strike_call:.1f})')
    ax.axvline(mean_strike_put, color='red', linestyle='--', linewidth=1.5,
               label=f'Put Mean Strike ({mean_strike_put:.1f})')
    
    # Highlight the call strike with the largest call volume.
    if not merged_df.empty and merged_df['volume_call'].max() > 0:
        idx_max_call = merged_df['volume_call'].idxmax()
        strike_max_call = merged_df.loc[idx_max_call, 'strike']
        volume_max_call = merged_df.loc[idx_max_call, 'volume_call']
        ax.annotate(f"Max Call: {volume_max_call:.0f}\nat {strike_max_call}",
                    xy=(strike_max_call - width/2, volume_max_call),
                    xytext=(strike_max_call + 10, volume_max_call + max(merged_df['volume_call']) * 0.1),
                    arrowprops=dict(facecolor='blue', shrink=0.05),
                    fontsize=10, color='blue', ha='center')

    # Highlight the put strike with the largest put volume.
    if not merged_df.empty and merged_df['volume_put'].max() > 0:
        idx_max_put = merged_df['volume_put'].idxmax()
        strike_max_put = merged_df.loc[idx_max_put, 'strike']
        volume_max_put = merged_df.loc[idx_max_put, 'volume_put']
        ax.annotate(f"Max Put: {volume_max_put:.0f}\nat {strike_max_put}",
                    xy=(strike_max_put + width/2, volume_max_put),
                    xytext=(strike_max_put - 10, volume_max_put + max(merged_df['volume_put']) * 0.1),
                    arrowprops=dict(facecolor='red', shrink=0.05),
                    fontsize=10, color='red', ha='center')
    
    ax.legend()
    plt.tight_layout()
    # Save the plot to file.
    plt.savefig(output_path)
    plt.close(fig)
    return output_path




def main():
    # 4. Use SPY as the example symbol.
    symbol = 'NVDA'
    
    # Compute the nearest Friday for the option expiration date.
    expiration = get_nearest_friday()
    print(f"Using expiration date: {expiration}")
    
    analyze_option_chain(symbol, expiration)

if __name__ == "__main__":
    main()