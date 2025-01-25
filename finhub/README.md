### Stock Strategy Analysis with Finnhub API

### Setup Your Env

go to finnhub to request a free API at: https://finnhub.io/

save the api as FIN_TOKEN=xxx in `.env` file at current directory (under /finhub)

### Setup


- call_reward_risk.py: used to analyze reward/risk ratio of a **BUY Call** action. It's based on Black-Scholes model, given a target upper and lower bound price. Need to model the volality with more advanced way.

- trend.py: not started. will be used to analyze historical data for buy/sell signal and price range prediction.


- trader.py: not started. will be used to retrieve option price in real time and provide real time update for different strategies.

