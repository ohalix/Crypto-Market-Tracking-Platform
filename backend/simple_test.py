#!/usr/bin/env python3
"""
简化测试 - 只测试数据抓取功能
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from scraper import get_crypto_prices, get_global_markets, auto_update_etf
from datetime import datetime

def main():
    print("CryptoMarket 数据抓取测试")
    print("=" * 50)
    
    # 测试加密货币
    print("\n1. 加密货币价格:")
    crypto = get_crypto_prices()
    for coin in ['BTC', 'ETH', 'SOL', 'XRP']:
        if coin in crypto:
            data = crypto[coin]
            price = data.get('price', 0)
            change = data.get('change_pct', 0)
            print(f"  {coin}: ${price:,.2f} ({change:+.2f}%)")
    
    # 测试市场数据
    print("\n2. 市场数据:")
    markets = get_global_markets()
    print(f"  股指: {len(markets.get('indices', {}))} 个")
    print(f"  核心指标: {len(markets.get('core', {}))} 个")
    
    print("\n3. 核心指标详情:")
    for key in ['CRUDE', 'GOLD', 'DXY', 'VIX', 'US10Y']:
        if key in markets.get('core', {}):
            data = markets['core'][key]
            print(f"  {data['name']}: {data['price']} ({data['change_pct']:+.2f}%)")
    
    # 测试 ETF 更新（可选）
    print("\n4. ETF 更新测试:")
    success, msg = auto_update_etf('btc')
    print(f"  {msg}")
    
    print("\n✅ 测试完成！")
    print(f"当前时间: {datetime.now()}")

if __name__ == "__main__":
    main()