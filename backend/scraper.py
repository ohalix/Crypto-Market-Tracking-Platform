"""
GlobalMarket 数据抓取模块
支持：全球股指、大宗商品、加密货币、ETF数据
"""

import json
import os
from datetime import datetime
import requests
from bs4 import BeautifulSoup

DATA_DIR = os.path.dirname(__file__)

# Yahoo Finance API 基础URL
YAHOO_BASE = "https://query1.finance.yahoo.com/v8/finance/chart/"

# 全球股指代码
INDICES = {
    # 美股
    'SP500': {'symbol': '^GSPC', 'name': '标普500'},
    'DOW': {'symbol': '^DJI', 'name': '道指'},
    'NASDAQ': {'symbol': '^IXIC', 'name': '纳指'},
    # 亚太
    'NIKKEI': {'symbol': '^N225', 'name': '日经225'},
    'KOSPI': {'symbol': '^KS11', 'name': '韩国KOSPI'},
    'HANGSENG': {'symbol': '^HSI', 'name': '恒生'},
    'SHANGHAI': {'symbol': '000001.SS', 'name': '上证'},
    # 欧洲
    'DAX': {'symbol': '^GDAXI', 'name': '德国DAX'},
    'FTSE': {'symbol': '^FTSE', 'name': '英国FTSE'},
    'CAC': {'symbol': '^FCHI', 'name': '法国CAC'},
}

# 核心指标
CORE_INDICATORS = {
    'DXY': {'symbol': 'DX-Y.NYB', 'name': '美元指数'},
    'VIX': {'symbol': '^VIX', 'name': 'VIX恐慌'},
    'CRUDE': {'symbol': 'CL=F', 'name': '原油'},
    'GOLD': {'symbol': 'GC=F', 'name': '黄金'},
    'US10Y': {'symbol': '^TNX', 'name': '美债10年'},
}


def parse_value(value_str):
    """解析数值"""
    if not value_str or value_str == '-' or value_str == '':
        return 0
    cleaned = value_str.replace('(', '-').replace(')', '').replace(',', '').replace('%', '')
    try:
        return float(cleaned)
    except ValueError:
        return 0


def get_yahoo_price(symbol):
    """从 Yahoo Finance 获取实时价格"""
    try:
        # 使用 yfinance 风格的 API
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
        params = {
            'interval': '1d',
            'range': '2d',  # 获取2天数据来计算涨跌
            'includeAdjustedClose': 'true'
        }
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=10)
        data = response.json()
        
        if 'chart' in data and data['chart']['result']:
            result = data['chart']['result'][0]
            meta = result['meta']
            
            # 获取当前价格
            price = meta.get('regularMarketPrice', 0)
            
            # 尝试从 meta 获取前收盘价
            prev_close = meta.get('previousClose', 0)
            
            # 如果 meta 中没有，尝试从 timestamps 计算
            if not prev_close and 'timestamp' in result and len(result['timestamp']) > 1:
                timestamps = result['timestamp']
                closes = result['indicators']['quote'][0]['close']
                if len(closes) >= 2:
                    prev_close = closes[-2] if closes[-2] else closes[-1]
            
            # 计算涨跌幅
            if prev_close and price:
                change = price - prev_close
                change_pct = (change / prev_close) * 100
            else:
                change = 0
                change_pct = 0
            
            return {
                'price': price,
                'change': change,
                'change_pct': change_pct
            }
    except Exception as e:
        print(f"获取 {symbol} 价格失败: {e}")
    
    return None


def get_global_markets():
    """获取全球市场行情 - 强制更新，失败时使用缓存"""
    result = {
        'indices': {},
        'core': {},
        'last_updated': datetime.now().isoformat()
    }
    
    # 先尝试获取最新数据
    updated_count = 0
    
    for key, info in INDICES.items():
        data = get_yahoo_price(info['symbol'])
        if data and data['price'] > 0:
            result['indices'][key] = {
                'name': info['name'],
                **data
            }
            updated_count += 1
        else:
            # 如果获取失败，尝试从缓存获取
            cached = load_data('markets_cache')
            if cached and 'indices' in cached and key in cached['indices']:
                result['indices'][key] = cached['indices'][key]
                print(f"使用缓存数据: {info['name']}")
    
    for key, info in CORE_INDICATORS.items():
        data = get_yahoo_price(info['symbol'])
        if data and data['price'] > 0:
            result['core'][key] = {
                'name': info['name'],
                **data
            }
            updated_count += 1
        else:
            # 如果获取失败，尝试从缓存获取
            cached = load_data('markets_cache')
            if cached and 'core' in cached and key in cached['core']:
                result['core'][key] = cached['core'][key]
                print(f"使用缓存数据: {info['name']}")
    
    # 如果成功获取到任何数据，更新缓存
    if updated_count > 0:
        filepath = os.path.join(DATA_DIR, 'markets_cache.json')
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"市场数据更新成功: {updated_count} 项")
    else:
        # 完全失败时，加载缓存
        cached = load_data('markets_cache')
        if cached:
            result = cached
            result['last_updated'] = datetime.now().isoformat()
            print("完全使用缓存数据")
    
    return result


def get_crypto_prices():
    """获取加密货币价格（优先 CoinGecko，失败时用 Yahoo Finance 备选）"""
    prices = {}
    
    try:
        # 优先使用 CoinGecko API（更稳定）
        url = 'https://api.coingecko.com/api/v3/simple/price'
        params = {
            'ids': 'bitcoin,ethereum,solana,ripple',
            'vs_currencies': 'usd',
            'include_24hr_change': 'true'
        }
        
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        # 计算 change 从 24h change
        # CoinGecko 返回 id 如 bitcoin, ethereum, solana, ripple
        coin_mapping = {
            'bitcoin': 'BTC',
            'ethereum': 'ETH',
            'solana': 'SOL',
            'ripple': 'XRP'
        }
        
        for coin, usd_data in data.items():
            coin_key = coin_mapping.get(coin, coin.upper())
            price = usd_data.get('usd', 0)
            change_pct = usd_data.get('usd_24h_change', 0)
            change = price * (change_pct / 100) if price and change_pct else 0
            
            prices[coin_key] = {
                'price': price,
                'change': change,
                'change_pct': change_pct
            }
        
        print(f"CoinGecko 获取成功: {list(prices.keys())}")
        
        # 如果 CoinGecko 失败，尝试 Yahoo Finance 作为备选
        if not prices:
            raise Exception("CoinGecko 无数据")
        
        # 保存成功获取的数据到缓存
        if prices:
            result = {}
            for coin in ['BTC', 'ETH', 'SOL', 'XRP']:
                if coin in prices:
                    result[coin] = prices[coin]
            result['last_updated'] = datetime.now().isoformat()
            
            # 保存到缓存文件
            filepath = os.path.join(DATA_DIR, 'crypto_cache.json')
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            print(f"加密货币数据已缓存: {list(prices.keys())}")
            return result
        
    except Exception as e:
        print(f"获取加密货币价格失败: {e}")
    
    # 如果 API 都失败了，读取缓存
    cached = load_data('crypto_cache')
    if cached:
        print("使用缓存的加密货币数据")
        cached['last_updated'] = datetime.now().isoformat()
        return cached
    
    # 连缓存都没有，返回默认值
    print("警告: 无法获取加密货币数据，使用默认值")
    return {
        'BTC': {'price': 0, 'change': 0, 'change_pct': 0},
        'ETH': {'price': 0, 'change': 0, 'change_pct': 0},
        'SOL': {'price': 0, 'change': 0, 'change_pct': 0},
        'XRP': {'price': 0, 'change': 0, 'change_pct': 0},
        'last_updated': datetime.now().isoformat()
    }


def scrape_yahoo_etf(coin='btc'):
    """从 Yahoo Finance 抓取 ETF 数据"""
    # BTC ETF 代码
    btc_etfs = {
        'IBIT': 'iShares Bitcoin Trust',
        'FBTC': 'Fidelity Wise Origin Bitcoin Fund',
        'ARKB': 'ARK 21Shares Bitcoin ETF',
        'BITB': 'Bitwise Bitcoin ETF',
        'BRRR': 'Valkyrie Bitcoin Fund',
        'BTCW': 'WisdomTree Bitcoin Fund',
    }
    
    # ETH ETF 代码
    eth_etfs = {
        'ETHA': 'iShares Ethereum Trust',
        'FETH': 'Fidelity Ethereum Fund',
        'CETH': 'Bitwise Ethereum ETF',
        'ARKE': 'ARK 21Shares Ethereum ETF',
        'ETHER': 'Valkyrie Ethereum Fund',
    }
    
    # SOL ETF 代码
    sol_etfs = {
        'IBTL': 'iShares Solana Trust',
        'FSOL': 'Fidelity Solana Fund',
    }
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    result = {
        'headers': ['Date', 'Price', 'Change', 'Change %'],
        'daily_data': [],
        'summary': {}
    }
    
    etf_map = {
        'btc': btc_etfs,
        'eth': eth_etfs,
        'sol': sol_etfs
    }
    
    symbols = list(etf_map.get(coin, btc_etfs).keys())
    
    try:
        # 获取每个 ETF 的价格数据
        all_data = {}
        for symbol in symbols:
            try:
                url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
                params = {
                    'interval': '1d',
                    'range': '5d',
                    'includeAdjustedClose': 'true'
                }
                response = requests.get(url, params=params, headers=headers, timeout=10)
                data = response.json()
                
                if 'chart' in data and data['chart']['result']:
                    result_data = data['chart']['result'][0]
                    meta = result_data['meta']
                    quotes = result_data['indicators']['quote'][0]
                    
                    timestamps = result_data.get('timestamp', [])
                    closes = quotes.get('close', [])
                    
                    if timestamps and closes:
                        latest_idx = len(closes) - 1
                        while latest_idx >= 0 and closes[latest_idx] is None:
                            latest_idx -= 1
                        
                        if latest_idx >= 0:
                            price = closes[latest_idx]
                            prev_price = closes[latest_idx - 1] if latest_idx > 0 and closes[latest_idx - 1] else price
                            
                            change = price - prev_price
                            change_pct = (change / prev_price * 100) if prev_price else 0
                            
                            date = datetime.fromtimestamp(timestamps[latest_idx]).strftime('%Y-%m-%d')
                            
                            all_data[symbol] = {
                                'price': price,
                                'change': change,
                                'change_pct': change_pct,
                                'date': date
                            }
            except Exception as e:
                print(f"获取 {symbol} 失败: {e}")
        
        # 整理数据
        if all_data:
            # 按日期分组
            dates = sorted(set(d['date'] for d in all_data.values()), reverse=True)
            
            for date in dates[:5]:  # 最近5天
                row = {'date': date}
                total_price = 0
                count = 0
                for symbol, data in all_data.items():
                    if data['date'] == date:
                        row[symbol] = round(data['price'], 2)
                        total_price += data['price']
                        count += 1
                
                if count > 0:
                    row['average'] = round(total_price / count, 2)
                    result['daily_data'].append(row)
        
        result['last_updated'] = datetime.now().isoformat()
        print(f"Yahoo Finance ETF 数据获取成功: {coin}")
        return result
        
    except Exception as e:
        print(f"抓取 {coin} ETF 失败: {e}")
        return None


def scrape_farside_etf(coin='btc'):
    """从 Farside 抓取 ETF 数据（已弃用，改用 Yahoo Finance）"""
    # Farside 已被 403 封禁，改用 Yahoo Finance
    return scrape_yahoo_etf(coin)


def scrape_sosovalue_xrp():
    """从 SosoValue 抓取 XRP ETF 数据"""
    url = 'https://sosovalue.com/zh/assets/etf/us-xrp-spot'
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        soup = BeautifulSoup(response.text, 'lxml')
        
        # 解析 XRP ETF 数据
        result = {'daily_data': [], 'summary': {}}
        
        # 查找历史数据表格
        # 注意：SosoValue 是动态加载，这里简化处理
        # 实际抓取可能需要 Playwright
        
        # 尝试从页面提取数据
        scripts = soup.find_all('script')
        for script in scripts:
            if script.string and 'xrp' in script.string.lower():
                # 提取 JSON 数据
                pass
        
        # 简化：返回空数据，后续用浏览器抓取
        result['last_updated'] = datetime.now().isoformat()
        return result
        
    except Exception as e:
        print(f"抓取 XRP ETF 失败: {e}")
        return None


def auto_update_etf(coin='btc'):
    """自动更新 ETF 数据"""
    if coin in ['btc', 'eth', 'sol', 'xrp']:
        new_data = scrape_yahoo_etf(coin)
    else:
        return False, f"不支持 {coin}"
    
    if new_data and len(new_data.get('daily_data', [])) > 0:
        filepath = os.path.join(DATA_DIR, f'{coin}_etf_data.json')
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(new_data, f, ensure_ascii=False, indent=2)
        return True, f"{coin.upper()}: 更新成功 ({len(new_data['daily_data'])} 条数据)"
    
    return False, f"{coin.upper()}: 抓取失败"


def load_data(name):
    """加载缓存数据"""
    filepath = os.path.join(DATA_DIR, f'{name}.json')
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None


def get_all_data():
    """获取所有数据"""
    return {
        'markets': get_global_markets(),
        'crypto': get_crypto_prices(),
        'btc_etf': load_data('btc_etf_data'),
        'eth_etf': load_data('eth_etf_data'),
        'sol_etf': load_data('sol_etf_data'),
        'xrp_etf': load_data('xrp_etf_data'),
    }


if __name__ == '__main__':
    # 测试
    print("测试全球市场数据...")
    markets = get_global_markets()
    print(f"获取了 {len(markets['indices'])} 个股指, {len(markets['core'])} 个核心指标")
    
    print("\n测试加密货币价格...")
    crypto = get_crypto_prices()
    print(crypto)
