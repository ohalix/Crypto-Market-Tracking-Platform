import requests

# 测试带 headers 的 farside
print("=== Farside with headers ===")
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
}

try:
    r = requests.get('https://farside.co.uk/btc/', headers=headers, timeout=30)
    print(f"Status: {r.status_code}")
    print(f"Content length: {len(r.text)}")
    if r.status_code == 200:
        # 检查是否有表格
        if '<table' in r.text:
            print("✓ 找到表格")
        else:
            print("✗ 没有表格")
except Exception as e:
    print(f"Farside 失败: {e}")

# 测试 Yahoo Finance ETF
print("\n=== Yahoo Finance ETF ===")
import json

symbols = ['IBIT', 'FBTC', 'ARKB']
for sym in symbols:
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}"
        params = {'interval': '1d', 'range': '5d'}
        r = requests.get(url, params=params, headers=headers, timeout=10)
        data = r.json()
        if 'chart' in data and data['chart']['result']:
            meta = data['chart']['result'][0]['meta']
            print(f"{sym}: ${meta.get('regularMarketPrice', 'N/A')}")
    except Exception as e:
        print(f"{sym} 失败: {e}")
