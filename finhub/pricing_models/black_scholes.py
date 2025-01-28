# black_scholes.py

import numpy as np
from scipy.stats import norm

def black_scholes_price(S, K, T, r, sigma, option_type='call', q=0):
    """
    Calculate Black-Scholes option price.
    
    Parameters:
    - S: Current stock price
    - K: Strike price
    - T: Time to maturity (in years)
    - r: Risk-free interest rate
    - sigma: Volatility
    - option_type: 'call' or 'put'
    - q: Dividend yield
    
    Returns:
    - Option price
    """
    S = np.array(S)
    K = np.array(K)
    T = np.array(T)
    sigma = np.array(sigma)
    
    d1 = (np.log(S / K) + (r - q + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    
    if option_type == 'call':
        price = S * np.exp(-q * T) * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
    elif option_type == 'put':
        price = K * np.exp(-r * T) * norm.cdf(-d2) - S * np.exp(-q * T) * norm.cdf(-d1)
    else:
        raise ValueError("option_type must be 'call' or 'put'")
    
    return price

def black_scholes_probability_ITM(S, K, T, r, sigma, option_type='call', q=0):
    """
    Calculate the probability that the option will be in the money at maturity.
    
    Parameters:
    - S: Current stock price
    - K: Strike price
    - T: Time to maturity (in years)
    - r: Risk-free interest rate
    - sigma: Volatility
    - option_type: 'call' or 'put'
    - q: Dividend yield
    
    Returns:
    - Probability ITM
    """
    d2 = (np.log(S / K) + (r - q - 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
    if option_type == 'call':
        probability = norm.cdf(d2)
    elif option_type == 'put':
        probability = norm.cdf(-d2)
    else:
        raise ValueError("option_type must be 'call' or 'put'")
    return probability

def calculate_reward_ratio(S, S_low, K, T, r, sigma, option_type='call', current_option_price=0):
    """
    Calculate Reward/Risk ratio for options.
    
    Parameters:
    - S: Current stock price
    - S_low: Lower target price (risk)
    - K: Strike price
    - T: Time to maturity
    - r: Risk-free rate
    - sigma: Volatility
    - option_type: 'call' or 'put'
    - current_option_price: Current option price
    
    Returns:
    - Tuple of (Reward/Risk ratio, Reward ratio, Risk ratio)
    """
    probability_ITM = black_scholes_probability_ITM(S, K, T, r, sigma, option_type, q=0)
    probability_ITM_low = black_scholes_probability_ITM(S_low, K, T, r, sigma, option_type, q=0)
    
    reward = (probability_ITM - probability_ITM_low) * 100  # Example scaling
    risk = probability_ITM_low * 100  # Example scaling
    
    reward_risk_ratio = reward / risk if risk != 0 else np.nan
    
    return reward_risk_ratio, reward, risk