
<h1 align="center" style="margin: 0 auto 0 auto;"> 
   <img width="32" src="https://lookatwallstreet.notion.site/image/https%3A%2F%2Fprod-files-secure.s3.us-west-2.amazonaws.com%2F0472a71b-02f2-43f2-b650-2ae94ae1fb5b%2Fc0e93390-aca9-4f7a-8b36-8a66ec8d925f%2F%25E5%25BE%25AE%25E4%25BF%25A1%25E6%2588%25AA%25E5%259B%25BE_20240930173619.png?table=block&id=1296853c-146c-8096-bb90-d38181edfea5&spaceId=0472a71b-02f2-43f2-b650-2ae94ae1fb5b&width=600&userId=&cache=v2" alt="logo" >  
   Livermore: Your FIRE assistant
</h1>

## 1. Setup and start the discord service
1. Clone this repo and go the root of the repo.
2. Install the package `livermore` directly by running
```
pip install -e .
```
3. Download the database file from: 
```
https://mega.nz/file/zmhnhCZa#fP92EJzHRSHMx_I9vhSbseQnSyTRus-H32Aa49L4R8g
```
4. Move the databse to `livermore/data/database/stock_candles.db`. The database only contains the data from 2023 to 2025.02.21. The `discord_engine` can automatically fetch the newest data.
5. Go to the project root directory and run the following command to start the discord engine:
```
python livermore/discord_engine.py
```

## 2. Introduction to the `finhub_engine` and `discord_engine` [TBD]


## 3. Other Tools [TBD]
- call_reward_risk.py: used to analyze reward/risk ratio of a **BUY Call** action. It's based on Black-Scholes model, given a target upper and lower bound price. Need to model the volality with more advanced way.

- trend.py: not started. will be used to analyze historical data for buy/sell signal and price range prediction.


- trader.py: not started. will be used to retrieve option price in real time and provide real time update for different strategies.

