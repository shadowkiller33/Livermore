
<h1 align="center" style="margin: 0 auto 0 auto;"> 
   <img width="32" src="https://lookatwallstreet.notion.site/image/https%3A%2F%2Fprod-files-secure.s3.us-west-2.amazonaws.com%2F0472a71b-02f2-43f2-b650-2ae94ae1fb5b%2Fc0e93390-aca9-4f7a-8b36-8a66ec8d925f%2F%25E5%25BE%25AE%25E4%25BF%25A1%25E6%2588%25AA%25E5%259B%25BE_20240930173619.png?table=block&id=1296853c-146c-8096-bb90-d38181edfea5&spaceId=0472a71b-02f2-43f2-b650-2ae94ae1fb5b&width=600&userId=&cache=v2" alt="logo" >  
   Livermore: Your FIRE assistant
</h1>

## 1. Step by Step Setup:
1. Install MooMoo/Futu OpenD: https://www.moomoo.com/download/OpenAPI
   
2. Install requirements: run the command under root directory:
```
pip install -r requirements.txt
```
3. Login to MooMoo/Futu OpenD, setup the port number to `11111`, which should be the same as `MOOMOOOPEND_PORT` in `Trading/TradingBOT.py`.

4. Check all the settings in `TradingBOT.py`, following the instructions in the project setup section.

5. Go to the project root directory and run in CMD:
```
python bot.py --token YOUR_DISCORD_BOT_TOKEN
```



##### Discord Server for trading:

### Stock Strategy Analysis with Finnhub API

### Setup Your Env

go to finnhub to request a free API at: https://finnhub.io/

save the api as FIN_TOKEN=xxx in `.env` file at current directory (under /finhub)

### Setup


- call_reward_risk.py: used to analyze reward/risk ratio of a **BUY Call** action. It's based on Black-Scholes model, given a target upper and lower bound price. Need to model the volality with more advanced way.

- trend.py: not started. will be used to analyze historical data for buy/sell signal and price range prediction.


- trader.py: not started. will be used to retrieve option price in real time and provide real time update for different strategies.

