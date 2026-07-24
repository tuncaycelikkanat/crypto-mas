import json

with open('data/backtests/fe05f742-88a0-4d46-8a5d-08afa3ef798f/market_data.json', 'r') as f:
    market_data = json.load(f)

if 'XRPUSDT' in market_data and len(market_data['XRPUSDT']) > 0:
    sample = market_data['XRPUSDT'][0]
    print(sample)
