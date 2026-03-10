#!/usr/bin/env python3
"""
测试修复后的 CryptoMarket 功能
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from scraper import get_crypto_prices, get_global_markets, auto_update_etf
from datetime import datetime

def test_crypto_prices():
    print("=== 测试加密货币价格 ===")
    crypto = get_crypto_prices()
    
    print(f"数据更新时间: {crypto.get('last_updated', '未知')}")
    
    for coin in ['BTC', 'ETH', 'SOL', 'XRP']:
        if coin in crypto:
            data = crypto[coin]
            price = data.get('price', 0)
            change = data.get('change_pct', 0)
            print(f"{coin}: ${price:,.2f} ({change:+.2f}%)")
        else:
            print(f"{coin}: 无数据")
    
    print()

def test_market_data():
    print("=== 测试市场数据 ===")
    markets = get_global_markets()
    
    print(f"数据更新时间: {markets.get('last_updated', '未知')}")
    print(f"股指数量: {len(markets.get('indices', {}))}")
    print(f"核心指标: {len(markets.get('core', {}))}")
    
    print("\n核心指标详情:")
    core_keys = ['CRUDE', 'GOLD', 'DXY', 'VIX', 'US10Y']
    for key in core_keys:
        if key in markets.get('core', {}):
            data = markets['core'][key]
            name = data.get('name', key)
            price = data.get('price', 0)
            change = data.get('change_pct', 0)
            print(f"{name}: {price} ({change:+.2f}%)")
    
    print()

def test_etf_update():
    print("=== 测试 ETF 更新 ===")
    # 测试 BTC ETF 更新
    success, msg = auto_update_etf('btc')
    print(f"BTC ETF 更新: {msg}")
    
    # 检查文件是否存在
    import json
    btc_file = os.path.join(os.path.dirname(__file__), 'btc_etf_data.json')
    if os.path.exists(btc_file):
        with open(btc_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print(f"BTC ETF 数据行数: {len(data.get('daily_data', []))}")
    print()

def test_main_logic():
    print("=== 测试主逻辑 ===")
    from main import should_update_etf
    
    # 测试时间判断逻辑
    print(f"当前时间: {datetime.now()}")
    print(f"是否需要更新 ETF: {should_update_etf()}")
    print()

if __name__ == "__main__":
    print("CryptoMarket 修复测试")
    print("=" * 50)
    
    test_crypto_prices()
    test_market_data()
    test_etf_update()
    test_main_logic()
    
    print("测试完成！")