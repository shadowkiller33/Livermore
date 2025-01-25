# heston_volatility.py

import QuantLib as ql
import numpy as np
from scipy.interpolate import interp1d
import logging

# Setup logging for this module
logging.basicConfig(level=logging.INFO)  # Set to DEBUG for detailed logs
logger = logging.getLogger(__name__)

def create_volatility_surface(strikes, volatilities):
    """
    Create an interpolation function for implied volatility based on strike prices.
    
    Parameters:
    - strikes: List or array of strike prices.
    - volatilities: List or array of implied volatilities corresponding to the strikes.
    
    Returns:
    - interp_func: A callable interpolation function for implied volatility.
    """
    # Sort the strikes and volatilities
    sorted_indices = np.argsort(strikes)
    sorted_strikes = np.array(strikes)[sorted_indices]
    sorted_vols = np.array(volatilities)[sorted_indices]
    
    # Handle duplicate strikes by averaging volatilities
    unique_strikes, inverse_indices = np.unique(sorted_strikes, return_inverse=True)
    averaged_vols = np.array([sorted_vols[inverse_indices == i].mean() for i in range(len(unique_strikes))])
    
    # Create an interpolation function
    interp_func = interp1d(unique_strikes, averaged_vols, kind='cubic', fill_value="extrapolate")
    return interp_func

def calibrate_heston_model(S, K_list, time_to_maturity, r, q, IV_list, option_type='call'):
    """
    Calibrates the Heston model parameters to fit market option prices.
    
    Parameters:
    - S (float): Current stock price.
    - K_list (list of float): List of strike prices.
    - exp_date (ql.Date): Expiration date.
    - r (float): Risk-free interest rate.
    - q (float): Dividend yield.
    - option_prices (list or np.ndarray): Array of option prices corresponding to K_list.
    - option_type (str): 'call' or 'put'.
    
    Returns:
    - heston_model (HestonModel): The calibrated Heston model.
    - calibrated_params (dict): Dictionary containing calibrated parameters.
    """
    logger.info("Starting Heston model calibration...")
    
    # Define QuantLib settings
    todays_date = ql.Date.todaysDate()
    ql.Settings.instance().evaluationDate = todays_date
    logger.info(f"Today's Date set to: {todays_date}")
    
    # Initial guesses for Heston parameters
    initial_vol = 0.2
    v0 = initial_vol ** 2
    kappa = 1.5
    theta = initial_vol ** 2
    sigma = 0.3
    rho = -0.5
    # v0 = 0.01; kappa = 0.2; theta = 0.02; rho = -0.75; sigma = 0.5;

    # Create Yield Term Structures
    risk_free_curve = ql.YieldTermStructureHandle(
        ql.FlatForward(todays_date, r, ql.Actual365Fixed())
    )
    dividend_curve = ql.YieldTermStructureHandle(
        ql.FlatForward(todays_date, q, ql.Actual365Fixed())
    )
    
    # Create Heston Process
    heston_process = ql.HestonProcess(
        risk_free_curve,
        dividend_curve,
        ql.QuoteHandle(ql.SimpleQuote(S)),
        v0,
        kappa,
        theta,
        sigma,
        rho
    )
    
    # Create Heston Model
    heston_model = ql.HestonModel(heston_process)
    # Define a calendar using QuantLib's built-in enumeration
    calendar = ql.UnitedStates(m=1)
    logger.info(f"Calendar set to: {calendar.name()}")
    
    # Create HestonModelHelper objects for each option
    option_helpers = []

    for K, IV in zip(K_list, IV_list):
        # Create a helper for each IV and strike
        
        period = ql.Period(int(time_to_maturity * 365), ql.Days)
        helper = ql.HestonModelHelper(
            period,
            calendar,
            float(S),
            float(K),
            ql.QuoteHandle(ql.SimpleQuote(IV)),
            risk_free_curve,
            dividend_curve,
            # 1  # RelativePriceError
        )
        helper.setPricingEngine(ql.AnalyticHestonEngine(heston_model))
        option_helpers.append(helper)

    # Keep a reference to option_helpers to prevent garbage collection
    # heston_model.helpers = option_helpers
    
    # Calibrate the model using the helpers
    optimization_method = ql.LevenbergMarquardt()
    end_criteria = ql.EndCriteria(1000, 100, 1.0e-8,1.0e-8, 1.0e-8)
    
    try:
        logger.info("Starting calibration process...")
        heston_model.calibrate(option_helpers, optimization_method, end_criteria)
        logger.info("Calibration successful.")
    except Exception as e:
        logger.error(f"Calibration failed: {e}")
        raise RuntimeError(f"Calibration failed: {e}")
    
    # Extract calibrated parameters
    calibrated_params = {
        'kappa': heston_model.params()[0],
        'theta': heston_model.params()[1],
        'sigma': heston_model.params()[2],
        'rho': heston_model.params()[3],
        'v0': heston_model.params()[4]
    }
    theta, kappa, sigma, rho, v0 = heston_model.params()
    calibrated_params = {
        'theta': heston_model.theta(),
        'kappa': heston_model.kappa(),
        'sigma': heston_model.sigma(),
        'rho': heston_model.rho(),
        'v0': heston_model.v0()
    }

    print ("\ntheta = %f, kappa = %f, sigma = %f, rho = %f, v0 = %f" % (theta, kappa, sigma, rho, v0))
    avg = 0.0
    # print ("%15s %15s %15s %20s" % (
    #     "Strikes", "Market Value",
    #     "Model Value", "Relative Error (%)"))
    # print ("="*70)
    for i, opt in enumerate(option_helpers):
        err = (opt.modelValue()/opt.marketValue() - 1.0)
        # print ("%15.2f %14.5f %15.5f %20.7f " % (
        #     K_list[i], opt.marketValue(),
        #     opt.modelValue(),
        #     100.0*(opt.modelValue()/opt.marketValue() - 1.0)))
        avg += abs(err)
    avg = avg*100.0/len(option_helpers)
    # print ("-"*70)
    print ("Average Abs Error (%%) : %5.3f" % (avg))
    
    return heston_model, calibrated_params