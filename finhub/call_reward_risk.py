# call_reward_risk.py

import logging
from datetime import datetime
from pricing_models.heston_volatility import calibrate_heston_model, create_volatility_surface
from engine import FinnhubEngine
import pandas as pd
import numpy as np
import QuantLib as ql
import time 
from prettytable import PrettyTable

# Setup logging
logging.basicConfig(
    filename='reward_risk_evaluator.log',  # Log to a file for persistence
    filemode='a',
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Define parameters
RISK_FREE_RATE = 0.0463  # Current treasury found 10-year yield
SYMBOL = "NVDA"
UPPER_BOUND = 150
LOWER_BOUND = 138
FILTER_THRESHOLD = 0.1 # only consider options within 10% of the current stock price

SYMBOL = "AAPL"
UPPER_BOUND = 230
LOWER_BOUND = 220

# call_reward_risk.py

# ... [existing imports and setup] ...

class RewardRiskEvaluator:
    def __init__(self, symbol, upperbound, lowerbound):
        self.symbol = symbol
        self.upperbound = upperbound
        self.lowerbound = lowerbound
        self.finnhub = FinnhubEngine()
        self.vol_surface = None
        self.heston_model = None
        self.calibrated_params = None

    def assess_option_pricing(self):
        current_stock_price = self.get_current_stock_price()
        self.stock_price = current_stock_price
        # Retrieve the full option chain
        options_data = self.finnhub.get_option_chain(self.symbol, '')
        if not options_data:
            logger.error("No option data found.")
            return

        # Extract unique expiration dates from the options data
        expiration_dates = sorted(list({option['expirationDate'] for option in options_data}))
        logger.info(f"Found {len(expiration_dates)} unique expiration dates.")

        # Select the first four expiration dates
        next_four_expirations = expiration_dates[:4]
        logger.info(f"Next four expiration dates: {next_four_expirations}")

        for i, exp_date in enumerate(next_four_expirations):
            logger.info(f"Processing options for expiration date: {exp_date}")

            # Filter options for the current expiration date
            filtered_options = [opt for opt in options_data if opt['expirationDate'] == exp_date]

            if not filtered_options:
                logger.warning(f"No options found for expiration date {exp_date}. Skipping.")
                continue

            # Separate calls
            calls = [opt['options']['CALL'] for opt in filtered_options][0]
            if not calls:
                logger.warning(f"No call options found for expiration date {exp_date}. Skipping.")
                continue

            # Extract strikes, market prices, and implied volatilities
            strikes = []
            market_prices = []
            IV = []

            min_strike, max_strike = current_stock_price * 0.8, current_stock_price * 1.2
            for call in calls:
                strike_price = call['strike']
                market_price = call['lastPrice']  # Use last price as estimated option price
                volume = call['volume']
                implied_vol = call.get('impliedVolatility')  # Assuming API provides this as a percentage
                if market_price == 0 or volume < 10 or (strike_price < min_strike or strike_price > max_strike):
                    # Skip options with zero price, low volume, or missing IV
                    continue
                strikes.append(strike_price)
                market_prices.append(market_price)
                IV.append(implied_vol / 100)  # Convert percentage to decimal

            if not strikes:
                logger.info(f"No valid call options found for expiration date {exp_date}. Skipping.")
                continue

            # Calculate time to maturity in years
            market_prices = np.array(market_prices)
            strikes = np.array(strikes)
            todays_date = ql.Date.todaysDate()
   
            year, month, day = map(int, exp_date.split("-"))
            ql_expiration_date = ql.Date(day, month, year)
            time_to_maturity = ql.Actual365Fixed().yearFraction(todays_date, ql_expiration_date)
            if time_to_maturity <= 0:
                logger.warning(f"Expiration date {exp_date} is in the past. Skipping.")
                continue

            # Calibrate Heston model
            try:
                self.heston_model, self.calibrated_params = calibrate_heston_model(
                    S=current_stock_price,
                    K_list=strikes,
                    time_to_maturity=time_to_maturity,
                    r=RISK_FREE_RATE,
                    q=0,  # Assuming no dividends
                    IV_list=IV,
                    option_type='call'
                )
                logger.info(f"Calibrated Heston Parameters for {exp_date}: {self.calibrated_params}")
            except Exception as e:
                logger.error(f"Failed to calibrate Heston model for {exp_date}: {e}")
                exit(0)
                # continue

            # using upper and lowerbound to calculate reward/risk ratio given the calibrated Heston model
            self.calculate_reward_risk(strikes, market_prices.tolist(), ql_expiration_date)
            time.sleep(5)  # Avoid rate limiting


    def calculate_reward_risk(self, strike_prices, option_prices, exp_date):
        """
        Calculate the reward and risk of the call buying strategy based on the
        calibrated Heston model, using the upper and lower bounds for stock prices.
        
        Returns:
        - dict: A dictionary with reward, risk, and reward/risk ratio.
        """

        def _estimate_option_price(stock_price, strike_price, risk_free_curve, dividend_curve, v0, kappa, theta, sigma, rho):
            """
            Estimate the option price using the calibrated Heston model.
            """
            heston_process = ql.HestonProcess(
                risk_free_curve,
                dividend_curve,
                ql.QuoteHandle(ql.SimpleQuote(stock_price)),
                v0,
                kappa,
                theta,
                sigma,
                rho
            )
            heston_model = ql.HestonModel(heston_process)
            pricing_engine = ql.AnalyticHestonEngine(heston_model)
            european_option = ql.EuropeanOption(
                ql.PlainVanillaPayoff(ql.Option.Call, strike_price),
                ql.EuropeanExercise(exp_date)
            )
            european_option.setPricingEngine(pricing_engine)
            expected_option_pricing = european_option.NPV()
            return expected_option_pricing


        if not self.heston_model or not self.calibrated_params:
            logger.error("Heston model is not calibrated. Please calibrate before computing reward/risk.")
            return None

        # Extract calibrated parameters
        kappa = self.calibrated_params['kappa']
        theta = self.calibrated_params['theta']
        sigma = self.calibrated_params['sigma']
        rho = self.calibrated_params['rho']
        v0 = self.calibrated_params['v0']
        
        # Initialize QuantLib Heston Process with calibrated parameters
        todays_date = ql.Date.todaysDate()
        ql.Settings.instance().evaluationDate = todays_date

        risk_free_curve = ql.YieldTermStructureHandle(
            ql.FlatForward(todays_date, RISK_FREE_RATE, ql.Actual365Fixed())
        )
        dividend_curve = ql.YieldTermStructureHandle(
            ql.FlatForward(todays_date, 0, ql.Actual365Fixed())  # Assuming no dividends
        )
        # upperbound based Heston process
        results = []
        for strike_price, option_price in zip(strike_prices, option_prices):
            if abs(strike_price - self.stock_price) / self.stock_price > FILTER_THRESHOLD:
                # Skip options that are too far from the current stock price
                continue
            reward_price = _estimate_option_price(self.upperbound, strike_price, risk_free_curve, dividend_curve, v0, kappa, theta, sigma, rho)
            risk_price = _estimate_option_price(self.lowerbound, strike_price, risk_free_curve, dividend_curve, v0, kappa, theta, sigma, rho)
            
            reward_ratio = (reward_price - option_price) / option_price
            risk_ratio = (option_price - risk_price) / option_price
            # print all stats
            reward_risk_ratio = (reward_price - option_price) / (option_price - risk_price)
            results.append([strike_price, option_price, reward_price, risk_price, reward_ratio, risk_ratio, reward_risk_ratio])

        table = PrettyTable()
        table.field_names = ["Strike", "Cur Premium", "Reward Price", "Risk Price", "Reward Ratio", "Risk Ratio", "R/R Ratio"]

        # Add rows to the table
        for row in results:
            table.add_row([f"{row[0]:.2f}", f"{row[1]:.3f}", f"{row[2]:.2f}", f"{row[3]:.2f}", f"{row[4]:.2%}", f"{row[5]:.2%}", f"{row[6]:.2f}"])
        print(table)


    def compute_calibration_error(self, market_prices, model_prices):
        """
        Computes calibration error metrics between market prices and model prices.

        Parameters:
        - market_prices (np.ndarray): Market option prices
        - model_prices (np.ndarray): Model option prices

        Returns:
        - dict: Calibration error metrics (e.g., RMSE, MAE)
        """
        valid = ~np.isnan(model_prices)
        errors = market_prices[valid] - model_prices[valid]
        rmse = np.sqrt(np.mean(errors**2))
        mae = np.mean(np.abs(errors))
        return {'RMSE': rmse, 'MAE': mae}


    def get_current_stock_price(self):
        """
        Retrieve the current stock price for the specified symbol.

        Returns:
        - float: Current stock price
        """
        quote_data = self.finnhub.get_stock_quote(self.symbol)
        return quote_data['c']
    


# Example usage
if __name__ == "__main__":
    evaluator = RewardRiskEvaluator(SYMBOL, UPPER_BOUND, LOWER_BOUND)
    evaluator.assess_option_pricing()