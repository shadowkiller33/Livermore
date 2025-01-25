import numpy as np
from scipy.stats import norm
import dataclasses


def black_scholes_price(S, K, T, r, sigma, option_type='call', q=0.0):
    """
    Calculate the Black-Scholes option price for European call or put options.

    Parameters:
    - S : float
        Current stock price (can be the target price you speculate).
    - K : float
        Strike price of the option.
    - T : float
        Time to maturity in years.
    - r : float
        Annual risk-free interest rate (as a decimal, e.g., 0.05 for 5%).
    - sigma : float
        Volatility of the underlying stock (as a decimal, e.g., 0.2 for 20%).
    - option_type : str, optional
        Type of the option: 'call' or 'put'. Default is 'call'.
    - q : float, optional
        Dividend yield (as a decimal). Default is 0.0.

    Returns:
    - price : float
        The Black-Scholes price of the option.
    """
    # Calculate d1 and d2 parameters
    d1 = (np.log(S / K) + (r - q + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)

    # delta = norm.cdf(d1)
    # print(delta)
    if option_type.lower() == 'call':
        # Calculate call option price
        price = (S * np.exp(-q * T) * norm.cdf(d1)) - (K * np.exp(-r * T) * norm.cdf(d2))
    elif option_type.lower() == 'put':
        # Calculate put option price
        price = (K * np.exp(-r * T) * norm.cdf(-d2)) - (S * np.exp(-q * T) * norm.cdf(-d1))
    else:
        raise ValueError("option_type must be 'call' or 'put'")
    
    return price


def black_scholes_probability_ITM(S, K, T, r, sigma, option_type='call', q=0.0):
    d2 = (np.log(S / K) + (r - q - 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
    if option_type.lower() == 'call':
        probability_ITM = norm.cdf(d2)
    elif option_type.lower() == 'put':
        probability_ITM = norm.cdf(-d2)
    else:
        raise ValueError("option_type must be 'call' or 'put'")
    return probability_ITM


def calculate_reward_ratio(S, K, T, r, sigma, option_type='call', q=0.0, 
                          current_option_price=None, S_low=None):
    """
    Calculates the Reward-Risk Ratio incorporating a target loss stock price.
    
    Parameters:
    - S: Current stock price
    - K: Strike price
    - T: Time to maturity (in years)
    - r: Risk-free interest rate
    - sigma: Volatility of the underlying asset
    - option_type: 'call' or 'put'
    - q: Dividend yield
    - current_option_price: Current market price of the option
    - S_low: Target loss stock price (estimated lower bound of stock price)
    
    Returns:
    - reward_risk_ratio: The computed Reward-Risk Ratio
    """
    if current_option_price is None or S_low is None:
        raise ValueError("Both current_option_price and S_low must be provided.")
    
    # Estimated option price from the model
    estimated_price = black_scholes_price(S, K, T, r, sigma, option_type, q)
    
    # Potential Profit
    potential_profit = estimated_price - current_option_price
    
    # Probability ITM
    probability_ITM = black_scholes_probability_ITM(S, K, T, r, sigma, option_type, q)
    
    # Calculate Probability of Loss
    if option_type.lower() == 'call':
        # For call options: C_T <= L implies S_T <= S_low
        K_prime = S_low  # Treat S_low as the stock price
        d2_prime = (np.log(S / K_prime) + (r - q - 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
        probability_Loss = norm.cdf(d2_prime)
        # Option price at S_low using Black-Scholes
        option_price_at_S_low = black_scholes_price(S_low, K, T, r, sigma, option_type, q)
    elif option_type.lower() == 'put':
        # For put options: P_T <= L implies S_T >= S_low
        K_prime = S_low  # Treat S_low as the stock price
        if K_prime <= 0:
            raise ValueError("S_low must be positive.")
        d2_prime = (np.log(S / K_prime) + (r - q - 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
        probability_Loss = 1 - norm.cdf(d2_prime)
        # Option price at S_low using Black-Scholes
        option_price_at_S_low = black_scholes_price(S_low, K, T, r, sigma, option_type, q)
    else:
        raise ValueError("option_type must be 'call' or 'put'")
    
    # Potential Risk
    potential_risk = current_option_price - option_price_at_S_low

    # Expected Reward and Expected Risk
    expected_reward = potential_profit * probability_ITM
    expected_risk = potential_risk * probability_Loss
    

    reward_risk_ratio = expected_reward / expected_risk
    reward_ratio = expected_reward / current_option_price
    risk_ratio = expected_risk / current_option_price
    return reward_risk_ratio, reward_ratio, risk_ratio

