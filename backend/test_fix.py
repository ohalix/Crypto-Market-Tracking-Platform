from scraper import get_crypto_prices, auto_update_etf

print("=== 测试加密货币 ===")
crypto = get_crypto_prices()
print(crypto)

print("\n=== 测试BTC ETF ===")
btc = auto_update_etf('btc')
print(btc)

print("\n=== 测试ETH ETF ===")
eth = auto_update_etf('eth')
print(eth)
