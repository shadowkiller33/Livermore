# black_scholes.py

import numpy as np, math
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
    # Black-Scholes d1 and d2
    d1 = (math.log(S / K) + (r - q + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    if option_type == "call":
        price = S * math.exp(-q * T) * norm.cdf(d1) - K * math.exp(-r * T) * norm.cdf(d2)
        delta = norm.cdf(d1)
    elif option_type == "put":
        price = K * math.exp(-r * T) * norm.cdf(-d2) - S * math.exp(-q * T) * norm.cdf(-d1)
        delta = -norm.cdf(-d1)
    else:
        raise ValueError("Invalid option type. Choose 'call' or 'put'.")

    # Greeks Calculation
    gamma = norm.pdf(d1) / (S * sigma * math.sqrt(T))
    vega = S * norm.pdf(d1) * math.sqrt(T) / 100
    theta = (-S * norm.pdf(d1) * sigma / (2 * math.sqrt(T)) 
             - r * K * math.exp(-r * T) * norm.cdf(d2 if option_type == "call" else -d2)) / 365
    rho = (K * T * math.exp(-r * T) * norm.cdf(d2 if option_type == "call" else -d2)) / 100

    return {
        "price": float(round(price, 5)),
        "delta": float(round(delta, 5)),
        "gamma": float(round(gamma, 5)),
        "vega": float(round(vega, 5)),
        "theta": float(round(theta, 5)),
        "rho": float(round(rho, 5)),
    }


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
