import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from engine import FinnhubEngine  # using your existing engine

# Use a Seaborn theme for a more modern aesthetic.
sns.set_theme(style="whitegrid")

def analyze_option_chain(symbol, output_path='temp_plot.png'):
    engine = FinnhubEngine()
    
    # Retrieve the option chain data from Finnhub API.
    try:
        # option_chain_data = engine.get_option_chain(symbol, expiration)
        option_chain_data = engine.get_option_chain(symbol)
    except Exception as e:
        print(f"Error retrieving option chain data: {e}")
        return

    # Plot the next three option chain distributions
    chains_to_plot = option_chain_data[:3]
    num_chains = len(chains_to_plot)
    
    # Create a figure with one subplot per option chain.
    fig, axs = plt.subplots(num_chains, 1, figsize=(12, 6 * num_chains))
    if num_chains == 1:
        axs = [axs]
    
    for idx, chain in enumerate(chains_to_plot):
        ax = axs[idx]
        
        # Extract overall stats for display in the subplot title.
        overall_call_volume = chain.get('callVolume')
        overall_put_volume = chain.get('putVolume')
        overall_volume_ratio = chain.get('putCallVolumeRatio')
        overall_call_open_interest = chain.get('callOpenInterest')
        overall_put_open_interest = chain.get('putOpenInterest')
        overall_open_interest_ratio = chain.get('putCallOpenInterestRatio')
        chain_expiration = chain.get('expirationDate')
        
        # Extract the options lists for calls and puts.
        try:
            call_list = chain['options']['CALL']
            put_list = chain['options']['PUT']
        except KeyError as e:
            print(f"Missing options data in chain {idx}: {e}")
            continue

        # Convert lists to DataFrames.
        call_df = pd.DataFrame(call_list)
        put_df = pd.DataFrame(put_list)

        # Ensure 'strike' and 'volume' columns are numeric.
        for col in ['strike', 'volume']:
            if col in call_df.columns:
                call_df[col] = pd.to_numeric(call_df[col], errors='coerce')
            if col in put_df.columns:
                put_df[col] = pd.to_numeric(put_df[col], errors='coerce')

        # Drop rows with missing values in 'strike' or 'volume' and sort by strike.
        call_df.dropna(subset=['strike', 'volume'], inplace=True)
        put_df.dropna(subset=['strike', 'volume'], inplace=True)
        call_df.sort_values('strike', inplace=True)
        put_df.sort_values('strike', inplace=True)

        # Filter out strikes with very small volume.
        call_threshold = 0.05 * call_df['volume'].max() if not call_df.empty else 0
        put_threshold = 0.05 * put_df['volume'].max() if not put_df.empty else 0
        call_df_filtered = call_df[call_df['volume'] >= call_threshold].copy()
        put_df_filtered = put_df[put_df['volume'] >= put_threshold].copy()

        # Compute weighted mean strike price for calls and puts.
        if call_df_filtered['volume'].sum() > 0:
            mean_strike_call = (call_df_filtered['strike'] * call_df_filtered['volume']).sum() / call_df_filtered['volume'].sum()
        else:
            mean_strike_call = np.nan

        if put_df_filtered['volume'].sum() > 0:
            mean_strike_put = (put_df_filtered['strike'] * put_df_filtered['volume']).sum() / put_df_filtered['volume'].sum()
        else:
            mean_strike_put = np.nan

        print(f"Chain {idx+1} (Expiration {chain_expiration}):")
        print(f"  Weighted mean strike (Call): {mean_strike_call:.2f}")
        print(f"  Weighted mean strike (Put): {mean_strike_put:.2f}")

        # Merge the filtered DataFrames on 'strike'.
        merged_df = pd.merge(call_df_filtered[['strike', 'volume']], 
                             put_df_filtered[['strike', 'volume']], 
                             on='strike', 
                             how='outer', 
                             suffixes=('_call', '_put'))
        merged_df.fillna(0, inplace=True)
        merged_df.sort_values('strike', inplace=True)
        
        # Plot the call and put volumes as grouped bar charts.
        x = merged_df['strike'].values
        width = 0.4  # Width of each bar
        
        ax.bar(x - width/2, merged_df['volume_call'], width=width, color='blue', alpha=0.7, label='Call Volume')
        ax.bar(x + width/2, merged_df['volume_put'], width=width, color='red', alpha=0.7, label='Put Volume')
        
        ax.set_xlabel("Strike Price")
        ax.set_ylabel("Volume")
        # Format the call/put ratio as a percentage with 1 decimal.
        vol_ratio_percent = overall_volume_ratio * 100 if overall_volume_ratio is not None else 0
        title = (f"{symbol} Option Volume Distribution\nExpiration: {chain_expiration}\n"
                 f"Overall Vol Ratio (Put/Call): {vol_ratio_percent:.1f}%, "
                 f"Open Interest Ratio (Put/Call): {overall_open_interest_ratio:.1f}%")
        ax.set_title(title)
        
        # Dynamically set x-ticks so that they are not too wide or narrow.
        if not merged_df.empty:
            min_strike = merged_df['strike'].min()
            max_strike = merged_df['strike'].max()
            # Compute a reasonable tick step (about 10 ticks)
            tick_range = max_strike - min_strike
            tick_step = max(1, np.ceil(tick_range / 10))
            xticks = np.arange(min_strike, max_strike + tick_step, tick_step)
            ax.set_xticks(xticks)
            ax.set_xticklabels([str(int(tick)) for tick in xticks], rotation=45, ha='right')
        else:
            ax.set_xticks([])

        # Mark the weighted mean strike prices with vertical lines.
        if not np.isnan(mean_strike_call):
            ax.axvline(mean_strike_call, color='blue', linestyle='--', linewidth=1.5,
                       label=f'Call Mean Strike ({mean_strike_call:.1f})')
        if not np.isnan(mean_strike_put):
            ax.axvline(mean_strike_put, color='red', linestyle='--', linewidth=1.5,
                       label=f'Put Mean Strike ({mean_strike_put:.1f})')
        
        # Instead of arrow annotations, simply display text for the max call and put strike.
        if not merged_df.empty and merged_df['volume_call'].max() > 0:
            idx_max_call = merged_df['volume_call'].idxmax()
            strike_max_call = merged_df.loc[idx_max_call, 'strike']
            # Place the text in the top-left corner of the subplot.
            ax.text(0.02, 0.95, f"Max Call Strike: {strike_max_call}",
                    transform=ax.transAxes, ha='left', va='top', color='blue', fontsize=10)
        
        if not merged_df.empty and merged_df['volume_put'].max() > 0:
            idx_max_put = merged_df['volume_put'].idxmax()
            strike_max_put = merged_df.loc[idx_max_put, 'strike']
            # Place the text in the top-right corner of the subplot.
            ax.text(0.98, 0.95, f"Max Put Strike: {strike_max_put}",
                    transform=ax.transAxes, ha='right', va='top', color='red', fontsize=10)
        
        ax.legend()

    plt.tight_layout()
    # plt.show()
    plt.savefig(output_path, dpi=300)
    plt.close(fig)
    return output_path

# For standalone testing
def main():
    symbol = 'SPY'
    analyze_option_chain(symbol, output_path=f'{symbol}_option_chains.png')

if __name__ == "__main__":
    main()