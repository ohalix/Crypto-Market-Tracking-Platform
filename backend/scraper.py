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
    """获取全球市场行情 - 优先使用缓存数据确保显示正常"""
    # 先加载缓存数据
    cached = load_data('markets_cache')
    
    result = {
        'indices': {},
        'core': {},
        'last_updated': datetime.now().isoformat()
    }
    
    # 如果有缓存，先使用缓存数据作为基础
    if cached:
        if 'indices' in cached:
            result['indices'] = cached['indices'].copy()
        if 'core' in cached:
            result['core'] = cached['core'].copy()
    
    # 尝试从 Yahoo 获取最新数据（只更新成功的）
    for key, info in INDICES.items():
        data = get_yahoo_price(info['symbol'])
        # 只更新价格有效的数据（change_pct 不为 0 或者是指数）
        if data and data['price'] > 0 and (data['change_pct'] != 0 or key in ['SP500', 'DOW', 'NASDAQ']):
            result['indices'][key] = {
                'name': info['name'],
                **data
            }
    
    for key, info in CORE_INDICATORS.items():
        data = get_yahoo_price(info['symbol'])
        # 只更新价格有效的数据
        if data and data['price'] > 0 and data['change_pct'] != 0:
            result['core'][key] = {
                'name': info['name'],
                **data
            }
    
    # 保存到缓存
    if result['indices'] or result['core']:
        import json
        filepath = os.path.join(DATA_DIR, 'markets_cache.json')
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
    
    return result


def get_crypto_prices():
    """获取加密货币价格（CoinGecko）"""
    try:
        url = 'https://api.coingecko.com/api/v3/simple/price'
        params = {
            'ids': 'bitcoin,ethereum,solana,ripple',
            'vs_currencies': 'usd',
            'include_24hr_change': 'true'
        }
        
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        return {
            'BTC': {'price': data['bitcoin']['usd'], 'change_pct': data['bitcoin'].get('usd_24h_change', 0)},
            'ETH': {'price': data['ethereum']['usd'], 'change_pct': data['ethereum'].get('usd_24h_change', 0)},
            'SOL': {'price': data['solana']['usd'], 'change_pct': data['solana'].get('usd_24h_change', 0)},
            'XRP': {'price': data['ripple']['usd'], 'change_pct': data['ripple'].get('usd_24h_change', 0)},
            'last_updated': datetime.now().isoformat()
        }
    except Exception as e:
        print(f"获取加密货币价格失败: {e}")
        return None


def scrape_farside_etf(coin='btc'):
    """从 Farside 抓取 ETF 数据"""
    url = f'https://farside.co.uk/{coin}/'
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        soup = BeautifulSoup(response.text, 'lxml')
        tables = soup.find_all('table')
        
        if len(tables) < 2:
            return None
        
        target_table = tables[1]
        result = {'headers': [], 'daily_data': [], 'summary': {}}
        
        # 解析表头
        header_row = target_table.find('thead')
        if header_row:
            headers = header_row.find_all('th')
            result['headers'] = [h.get_text(strip=True) for h in headers]
        
        # 解析数据
        tbody = target_table.find('tbody')
        if tbody:
            rows = tbody.find_all('tr')
            
            for row in rows:
                cells = row.find_all('td')
                if len(cells) > 0:
                    row_data = [c.get_text(strip=True) for c in cells]
                    date_str = row_data[0]
                    
                    if date_str in ['Total', 'Average', 'Maximum', 'Minimum']:
                        result['summary'][date_str] = row_data
                    else:
                        try:
                            data_row = {'date': date_str}
                            
                            if coin == 'btc':
                                data_row.update({
                                    'blackrock': parse_value(row_data[1]),
                                    'fidelity': parse_value(row_data[2]),
                                    'bitwise': parse_value(row_data[3]),
                                    'ark': parse_value(row_data[4]),
                                    'invesco': parse_value(row_data[5]),
                                    'franklin': parse_value(row_data[6]),
                                    'valkyrie': parse_value(row_data[7]),
                                    'vaneck': parse_value(row_data[8]),
                                    'wtree': parse_value(row_data[9]),
                                    'grayscale_gb': parse_value(row_data[10]),
                                    'grayscale_btc': parse_value(row_data[11]),
                                    'total': parse_value(row_data[12])
                                })
                            elif coin == 'eth':
                                data_row.update({
                                    'blackrock': parse_value(row_data[1]),
                                    'fidelity': parse_value(row_data[2]),
                                    'bitwise': parse_value(row_data[3]),
                                    'shares21': parse_value(row_data[4]),
                                    'vaneck': parse_value(row_data[5]),
                                    'invesco': parse_value(row_data[6]),
                                    'franklin': parse_value(row_data[7]),
                                    'grayscale_et': parse_value(row_data[8]),
                                    'grayscale_eth': parse_value(row_data[9]),
                                    'total': parse_value(row_data[10])
                                })
                            elif coin == 'sol':
                                # SOL 数据结构类似 ETH
                                data_row.update({
                                    'blackrock': parse_value(row_data[1]),
                                    'fidelity': parse_value(row_data[2]),
                                    'bitwise': parse_value(row_data[3]),
                                    'shares21': parse_value(row_data[4]),
                                    'vaneck': parse_value(row_data[5]),
                                    'invesco': parse_value(row_data[6]),
                                    'franklin': parse_value(row_data[7]),
                                    'grayscale_sol': parse_value(row_data[8]),
                                    'total': parse_value(row_data[9])
                                })
                            
                            result['daily_data'].append(data_row)
                        except (IndexError, ValueError):
                            continue
        
        result['last_updated'] = datetime.now().isoformat()
        return result
        
    except Exception as e:
        print(f"抓取 {coin} ETF 失败: {e}")
        return None


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
    if coin in ['btc', 'eth', 'sol']:
        new_data = scrape_farside_etf(coin)
    elif coin == 'xrp':
        new_data = scrape_sosovalue_xrp()
    else:
        return False, f"不支持 {coin}"
    
    if new_data and len(new_data.get('daily_data', [])) > 0:
        filepath = os.path.join(DATA_DIR, f'{coin}_etf_data.json')
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(new_data, f, ensure_ascii=False, indent=2)
        return True, f"{coin.upper()}: 更新成功"
    
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
        'btc_etf': load_data('btc'),
        'eth_etf': load_data('eth'),
        'sol_etf': load_data('sol'),
        'xrp_etf': load_data('xrp'),
    }


if __name__ == '__main__':
    # 测试
    print("测试全球市场数据...")
    markets = get_global_markets()
    print(f"获取了 {len(markets['indices'])} 个股指, {len(markets['core'])} 个核心指标")
    
    print("\n测试加密货币价格...")
    crypto = get_crypto_prices()
    print(crypto)
