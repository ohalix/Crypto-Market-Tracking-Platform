# GlobalMarket

Real-Time Global Financial Market Monitoring Platform

## Features

- **Core Indicators**: US Dollar Index, VIX Fear Index, Crude Oil, Gold, US 10-Year Treasury Yield
- **Global Stock Indices**: S&P 500, Dow Jones, Nasdaq, Nikkei 225, Korea KOSPI, Hang Seng, Shanghai Composite, Germany DAX, UK FTSE, France CAC
- **Cryptocurrencies**: Real-time prices for BTC, ETH, SOL, XRP
- **ETF Data**: Fund flow tracking for BTC, ETH, SOL, XRP ETFs

## Data Sources

- Yahoo Finance (global indices, commodities)
- CoinGecko (cryptocurrency prices)
- Farside (BTC/ETH/SOL ETFs)
- SosoValue (XRP ETF)

## Run Locally

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```

Access http://localhost:8000⁠�


## Deployment
Automatic deployment via Railway