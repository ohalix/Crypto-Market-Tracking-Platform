"""
GlobalMarket 数据抓取模块
支持：全球股指、大宗商品、加密货币、ETF资金流入数据
"""

import json
import os
from datetime import datetime
import requests
from bs4 import BeautifulSoup

DATA_DIR = os.path.dirname(__file__)

# 全球股指代码
INDICES = {
    'SP500': {'symbol': '^GSPC', 'name': '标普500'},
    'DOW': {'symbol': '^DJI', 'name': '道指'},
    'NASDAQ': {'symbol': '^IXIC', 'name': '纳指'},
    'NIKKEI': {'symbol': '^N225', 'name': '日经225'},
    'KOSPI': {'symbol': '^KS11', 'name': '韩国KOSPI'},
    'HANGSENG': {'symbol': '^HSI', 'name': '恒生'},
    'SHANGHAI': {'symbol': '000001.SS', 'name': '上证'},
    'DAX': {'symbol': '^GDAXI', 'name': '德国DAX'},
    'FTSE': {'symbol': '^FTSE', 'name': '英国FTSE'},
    'CAC': {'symbol': '^FCHI', 'name': '法国CAC'},
}

CORE_INDICATORS = {
    'DXY': {'symbol': 'DX-Y.NYB', 'name': '美元指数'},
    'VIX': {'symbol': '^VIX', 'name': 'VIX恐慌'},
    'CRUDE': {'symbol': 'CL=F', 'name': '原油'},
    'GOLD': {'symbol': 'GC=F', 'name': '黄金'},
    'US10Y': {'symbol': '^TNX', 'name': '美债10年'},
}

# ETF 配置
ETF_CONFIG = {
    'btc': {
        'name': 'Bitcoin',
        'farside_url': 'https://farside.co.uk/btc/',
        'headers': ['Date', 'Blackrock', 'Fidelity', 'Bitwise', 'Ark', 'Invesco', 'Franklin', 'Valkyrie', 'VanEck', 'WTree', 'Grayscale GB', 'Grayscale BTC', 'Total'],
        'field_map': {
            'Blackrock': 'blackrock',
            'Fidelity': 'fidelity', 
            'Bitwise': 'bitwise',
            'Ark': 'ark',
            'Invesco': 'invesco',
            'Franklin': 'franklin',
            'Valkyrie': 'valkyrie',
            'VanEck': 'vaneck',
            'WTree': 'wtree',
            'Grayscale GB': 'grayscale_gb',
            'Grayscale BTC': 'grayscale_btc',
            'Total': 'total'
        }
    },
    'eth': {
        'name': 'Ethereum',
        'farside_url': 'https://farside.co.uk/eth/',
        'headers': ['Date', 'Blackrock', 'Fidelity', 'Bitwise', '21Shares', 'VanEck', 'Invesco', 'Franklin', 'Grayscale ET', 'Grayscale ETH', 'Total'],
        'field_map': {
            'Blackrock': 'blackrock',
            'Fidelity': 'fidelity',
            'Bitwise': 'bitwise',
            '21Shares': 'shares21',
            'VanEck': 'vaneck',
            'Invesco': 'invesco',
            'Franklin': 'franklin',
            'Grayscale ET': 'grayscale_et',
            'Grayscale ETH': 'grayscale_eth',
            'Total': 'total'
        }
    },
    'sol': {
        'name': 'Solana',
        'farside_url': 'https://farside.co.uk/sol/',
        'headers': ['Date', 'Bitwise', 'VanEck1', 'VanEck2', 'VanEck3', 'Franklin', 'Grayscale', 'Total'],
        'field_map': {
            'Bitwise': 'bitwise',
            'VanEck1': 'vaneck1',
            'VanEck2': 'vaneck2',
            'VanEck3': 'vaneck3',
            'Franklin': 'franklin',
            'Grayscale': 'grayscale',
            'Total': 'total'
        }
    },
    'xrp': {
        'name': 'XRP',
        'farside_url': 'https://farside.co.uk/xrp/',  # Farside 没有 XRP 页面，会 fallback 到 SosoValue
        'sosovalue_url': 'https://sosovalue.com/assets/etf/us-xrp-spot',
        'headers': ['Date', 'Total'],  # XRP 只有总体数据
        'field_map': {
            'Total': 'total'
        }
    }
}


def parse_value(value_str):
    """解析数值，处理括号表示负数的情况"""
    if not value_str or value_str == '-' or value_str == '':
        return 0.0
    cleaned = value_str.replace('(', '-').replace(')', '').replace(',', '').replace('%', '').replace('+', '').replace('$', '').replace('M', '')
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def format_date(date_str):
    """统一日期格式为 'DD MMM YYYY'，如果不是有效日期则返回 None"""
    if not date_str:
        return None
    
    date_str = date_str.strip()
    
    # 过滤掉非日期行（如 Fee、Staking、Seed、Total、Average、Maximum、Minimum 等）
    non_date_keywords = ['fee', 'staking', 'seed', 'total', 'average', 'issuer', 'name', 'aum', 'maximum', 'minimum']
    if date_str.lower() in non_date_keywords:
        return None
    
    # 如果包含这些关键词，也过滤掉
    for keyword in non_date_keywords:
        if keyword in date_str.lower():
            return None
    
    try:
        for fmt in ['%Y-%m-%d', '%d %b %Y', '%d %B %Y', '%m/%d/%Y', '%d/%m/%Y']:
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.strftime('%d %b %Y')
            except:
                continue
        # 如果无法解析，返回原始值（可能是已经格式化的日期）
        return date_str if len(date_str) > 5 else None
    except:
        return None


def get_yahoo_price(symbol):
    """从 Yahoo Finance 获取实时价格"""
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
        params = {'interval': '1d', 'range': '2d', 'includeAdjustedClose': 'true'}
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        
        response = requests.get(url, params=params, headers=headers, timeout=10)
        data = response.json()
        
        if 'chart' in data and data['chart']['result']:
            result = data['chart']['result'][0]
            meta = result['meta']
            
            price = meta.get('regularMarketPrice', 0)
            prev_close = meta.get('previousClose', 0)
            
            if not prev_close and 'timestamp' in result and len(result['timestamp']) > 1:
                timestamps = result['timestamp']
                closes = result['indicators']['quote'][0]['close']
                if len(closes) >= 2:
                    prev_close = closes[-2] if closes[-2] else closes[-1]
            
            if prev_close and price:
                change = price - prev_close
                change_pct = (change / prev_close) * 100
            else:
                change = 0
                change_pct = 0
            
            return {'price': price, 'change': change, 'change_pct': change_pct}
    except Exception as e:
        print(f"获取 {symbol} 价格失败: {e}")
    
    return None


def get_global_markets():
    """获取全球市场行情"""
    result = {'indices': {}, 'core': {}, 'last_updated': datetime.now().isoformat()}
    updated_count = 0
    
    for key, info in INDICES.items():
        data = get_yahoo_price(info['symbol'])
        if data and data['price'] > 0:
            result['indices'][key] = {'name': info['name'], **data}
            updated_count += 1
        else:
            cached = load_data('markets_cache')
            if cached and 'indices' in cached and key in cached['indices']:
                result['indices'][key] = cached['indices'][key]
    
    for key, info in CORE_INDICATORS.items():
        data = get_yahoo_price(info['symbol'])
        if data and data['price'] > 0:
            result['core'][key] = {'name': info['name'], **data}
            updated_count += 1
        else:
            cached = load_data('markets_cache')
            if cached and 'core' in cached and key in cached['core']:
                result['core'][key] = cached['core'][key]
    
    if updated_count > 0:
        filepath = os.path.join(DATA_DIR, 'markets_cache.json')
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
    else:
        cached = load_data('markets_cache')
        if cached:
            result = cached
            result['last_updated'] = datetime.now().isoformat()
    
    return result


def get_crypto_prices():
    """获取加密货币价格"""
    prices = {}
    
    try:
        url = 'https://api.coingecko.com/api/v3/simple/price'
        params = {'ids': 'bitcoin,ethereum,solana,ripple', 'vs_currencies': 'usd', 'include_24hr_change': 'true'}
        
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        coin_mapping = {'bitcoin': 'BTC', 'ethereum': 'ETH', 'solana': 'SOL', 'ripple': 'XRP'}
        
        for coin, usd_data in data.items():
            coin_key = coin_mapping.get(coin, coin.upper())
            price = usd_data.get('usd', 0)
            change_pct = usd_data.get('usd_24h_change', 0)
            change = price * (change_pct / 100) if price and change_pct else 0
            
            prices[coin_key] = {'price': price, 'change': change, 'change_pct': change_pct}
        
        if prices:
            result = {}
            for coin in ['BTC', 'ETH', 'SOL', 'XRP']:
                if coin in prices:
                    result[coin] = prices[coin]
            result['last_updated'] = datetime.now().isoformat()
            
            filepath = os.path.join(DATA_DIR, 'crypto_cache.json')
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            return result
        
    except Exception as e:
        print(f"获取加密货币价格失败: {e}")
    
    cached = load_data('crypto_cache')
    if cached:
        cached['last_updated'] = datetime.now().isoformat()
        return cached
    
    return {
        'BTC': {'price': 0, 'change': 0, 'change_pct': 0},
        'ETH': {'price': 0, 'change': 0, 'change_pct': 0},
        'SOL': {'price': 0, 'change': 0, 'change_pct': 0},
        'XRP': {'price': 0, 'change': 0, 'change_pct': 0},
        'last_updated': datetime.now().isoformat()
    }


def scrape_sosovalue_xrp():
    """
    从 SosoValue 抓取 XRP ETF 总体资金流入数据
    SosoValue 提供 XRP ETF 的日度总净流入数据
    """
    url = 'https://sosovalue.com/assets/etf/us-xrp-spot'
    
    result = {
        'headers': ['Date', 'Total'],
        'daily_data': [],
        'summary': {},
        'last_updated': datetime.now().isoformat()
    }
    
    try:
        from playwright.sync_api import sync_playwright
        import re
        
        print(f"使用 Playwright 抓取 XRP ETF 数据 from {url}...")
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            page = context.new_page()
            
            # 访问页面
            page.goto(url, wait_until='networkidle', timeout=60000)
            
            # 等待页面加载 - 等待历史数据区域出现
            page.wait_for_timeout(5000)
            
            # 获取页面内容
            html = page.content()
            
            browser.close()
        
        # 解析 HTML
        soup = BeautifulSoup(html, 'lxml')
        
        # 方法1: 查找包含 "XRP现货ETF历史数据总览" 的区域
        # 数据格式是连续的 div，每个日期一行
        history_section = None
        for div in soup.find_all('div'):
            if 'XRP现货ETF历史数据总览' in div.get_text():
                history_section = div
                break
        
        if history_section:
            # 在父元素或相邻元素中查找数据行
            parent = history_section.parent
            if parent:
                # 查找所有包含日期格式的 div
                date_pattern = r'(\d{1,2})月\s+(\d{1,2}),\s*(\d{4})'
                
                # 获取整个区域的文本
                section_text = parent.get_text()
                
                # 查找所有日期和对应的资金流入
                # 数据格式通常是: 日期 单日总净流入 累计总净流入 ...
                lines = section_text.split('\n')
                
                current_date = None
                for i, line in enumerate(lines):
                    line = line.strip()
                    if not line:
                        continue
                    
                    # 匹配日期
                    date_match = re.search(date_pattern, line)
                    if date_match:
                        month = int(date_match.group(1))
                        day = int(date_match.group(2))
                        year = int(date_match.group(3))
                        
                        try:
                            dt = datetime(year, month, day)
                            date_str = dt.strftime('%d %b %Y')
                            
                            # 在接下来的几行中查找资金流入数据
                            flow_value = None
                            for j in range(i+1, min(i+5, len(lines))):
                                flow_line = lines[j].strip()
                                # 匹配资金流入格式: -$6.08M 或 $4.19M 或 -6.08M
                                flow_match = re.search(r'[-+]?\$?([\d.]+)\s*M', flow_line)
                                if flow_match:
                                    val = float(flow_match.group(1))
                                    # 判断正负
                                    if '-$' in flow_line or flow_line.startswith('-') or flow_line.startswith('-$'):
                                        val = -val
                                    flow_value = val
                                    break
                            
                            if flow_value is not None:
                                # 检查是否已存在该日期
                                if not any(d['date'] == date_str for d in result['daily_data']):
                                    result['daily_data'].append({
                                        'date': date_str,
                                        'total': flow_value
                                    })
                        except:
                            continue
        
        # 方法2: 如果方法1失败，尝试直接解析页面中所有日期-资金对
        if not result['daily_data']:
            page_text = soup.get_text()
            
            # 查找所有日期
            date_pattern = r'(\d{1,2})月\s+(\d{1,2}),\s*(\d{4})'
            dates = list(re.finditer(date_pattern, page_text))
            
            for i, date_match in enumerate(dates):
                month = int(date_match.group(1))
                day = int(date_match.group(2))
                year = int(date_match.group(3))
                
                try:
                    dt = datetime(year, month, day)
                    date_str = dt.strftime('%d %b %Y')
                    
                    # 在该日期之后查找资金数据
                    start_pos = date_match.end()
                    end_pos = dates[i+1].start() if i+1 < len(dates) else start_pos + 200
                    section = page_text[start_pos:end_pos]
                    
                    # 查找第一个资金数值
                    flow_match = re.search(r'[-+]?\$?([\d.]+)\s*M', section)
                    if flow_match:
                        val = float(flow_match.group(1))
                        flow_str = section[flow_match.start():flow_match.end()]
                        if '-$' in flow_str or section[flow_match.start()-2:flow_match.start()].strip() == '-':
                            val = -val
                        
                        if not any(d['date'] == date_str for d in result['daily_data']):
                            result['daily_data'].append({
                                'date': date_str,
                                'total': val
                            })
                except:
                    continue
        
        # 去重并排序（按日期降序）
        seen_dates = set()
        unique_data = []
        for item in result['daily_data']:
            if item['date'] not in seen_dates:
                seen_dates.add(item['date'])
                unique_data.append(item)
        
        result['daily_data'] = sorted(unique_data, key=lambda x: datetime.strptime(x['date'], '%d %b %Y'), reverse=True)
        
        print(f"XRP ETF 数据抓取成功: {len(result['daily_data'])} 条记录")
        return result
        
    except ImportError:
        print("Playwright 未安装，无法抓取 XRP 数据")
        return None
    except Exception as e:
        print(f"Playwright 抓取 XRP 失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def scrape_farside_with_playwright(coin='btc'):
    """
    使用 Playwright 抓取 Farside ETF 数据
    可以绕过 403 限制
    """
    config = ETF_CONFIG.get(coin)
    if not config:
        print(f"不支持的币种: {coin}")
        return None
    
    url = config['farside_url']
    
    result = {
        'headers': config['headers'],
        'daily_data': [],
        'summary': {},
        'last_updated': datetime.now().isoformat()
    }
    
    try:
        from playwright.sync_api import sync_playwright
        
        print(f"使用 Playwright 抓取 {coin.upper()} ETF 数据...")
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            page = context.new_page()
            
            # 访问页面
            page.goto(url, wait_until='networkidle', timeout=60000)
            
            # 等待表格加载
            page.wait_for_selector('table', timeout=30000)
            
            # 获取页面内容
            html = page.content()
            
            browser.close()
        
        # 解析 HTML
        soup = BeautifulSoup(html, 'lxml')
        tables = soup.find_all('table')
        
        if not tables:
            print(f"未找到 {coin} 的数据表格")
            return None
        
        # 找到包含数据的表格
        daily_table = None
        for table in tables:
            rows = table.find_all('tr')
            if len(rows) > 5:
                daily_table = table
                break
        
        if not daily_table:
            print(f"未找到 {coin} 的日度数据表格")
            return None
        
        # 解析数据
        rows = daily_table.find_all('tr')
        field_map = config['field_map']
        
        for row in rows[1:]:  # 跳过表头
            cells = row.find_all(['td', 'th'])
            if len(cells) < 3:
                continue
            
            date_cell = cells[0].get_text(strip=True)
            if not date_cell:
                continue
            
            # 使用 format_date 验证并格式化日期
            date_str = format_date(date_cell)
            if not date_str:  # 如果不是有效日期，跳过
                continue
            
            row_data = {'date': date_str}
            
            header_cols = config['headers']
            for i, header in enumerate(header_cols[1:], 1):
                if i < len(cells):
                    value_str = cells[i].get_text(strip=True)
                    field_name = field_map.get(header)
                    if field_name:
                        row_data[field_name] = parse_value(value_str)
            
            if len(row_data) > 1:
                result['daily_data'].append(row_data)
        
        print(f"{coin.upper()} ETF 数据抓取成功: {len(result['daily_data'])} 条记录")
        return result
        
    except ImportError:
        print("Playwright 未安装，尝试使用 requests...")
        return None
    except Exception as e:
        print(f"Playwright 抓取 {coin} 失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def scrape_farside_etf(coin='btc'):
    """
    从 Farside 抓取 ETF 资金流入数据
    先尝试 requests，失败则使用 Playwright
    XRP 数据从 SosoValue 抓取（Farside 没有 XRP 页面）
    """
    # XRP 使用 SosoValue 数据源
    if coin == 'xrp':
        return scrape_sosovalue_xrp()
    
    config = ETF_CONFIG.get(coin)
    if not config:
        print(f"不支持的币种: {coin}")
        return None
    
    url = config['farside_url']
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'Cache-Control': 'max-age=0',
    }
    
    result = {
        'headers': config['headers'],
        'daily_data': [],
        'summary': {},
        'last_updated': datetime.now().isoformat()
    }
    
    try:
        print(f"正在抓取 {coin.upper()} ETF 数据 from {url}...")
        
        # 创建 session 以维持 cookies
        session = requests.Session()
        
        # 先访问主页获取 cookie
        session.get('https://farside.co.uk/', headers=headers, timeout=10)
        
        # 再访问具体页面
        response = session.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'lxml')
        tables = soup.find_all('table')
        
        if not tables:
            print(f"未找到 {coin} 的数据表格，尝试 Playwright...")
            return scrape_farside_with_playwright(coin)
        
        daily_table = None
        for table in tables:
            rows = table.find_all('tr')
            if len(rows) > 5:
                daily_table = table
                break
        
        if not daily_table:
            print(f"未找到 {coin} 的日度数据表格，尝试 Playwright...")
            return scrape_farside_with_playwright(coin)
        
        rows = daily_table.find_all('tr')
        field_map = config['field_map']
        
        for row in rows[1:]:
            cells = row.find_all(['td', 'th'])
            if len(cells) < 3:
                continue
            
            date_cell = cells[0].get_text(strip=True)
            if not date_cell or date_cell.lower() in ['total', 'average', '']:
                continue
            
            date_str = format_date(date_cell)
            row_data = {'date': date_str}
            
            header_cols = config['headers']
            for i, header in enumerate(header_cols[1:], 1):
                if i < len(cells):
                    value_str = cells[i].get_text(strip=True)
                    field_name = field_map.get(header)
                    if field_name:
                        row_data[field_name] = parse_value(value_str)
            
            if len(row_data) > 1:
                result['daily_data'].append(row_data)
        
        print(f"{coin.upper()} ETF 数据抓取成功: {len(result['daily_data'])} 条记录")
        return result
        
    except requests.RequestException as e:
        print(f"Requests 抓取 {coin} 失败: {e}，尝试 Playwright...")
        return scrape_farside_with_playwright(coin)
    except Exception as e:
        print(f"解析 {coin} ETF 数据失败: {e}，尝试 Playwright...")
        return scrape_farside_with_playwright(coin)


def auto_update_etf(coin='btc'):
    """自动更新 ETF 数据"""
    new_data = scrape_farside_etf(coin)
    
    if new_data and len(new_data.get('daily_data', [])) > 0:
        filepath = os.path.join(DATA_DIR, f'{coin}_etf_data.json')
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(new_data, f, ensure_ascii=False, indent=2)
        return True, f"{coin.upper()}: 更新成功 ({len(new_data['daily_data'])} 条数据)"
    
    return False, f"{coin.upper()}: 抓取失败，使用缓存数据"


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
    print("=" * 60)
    print("测试 ETF 数据抓取")
    print("=" * 60)
    
    for coin in ['btc', 'eth', 'sol', 'xrp']:
        print(f"\n--- 测试 {coin.upper()} ETF ---")
        success, msg = auto_update_etf(coin)
        print(msg)
        
        data = load_data(f'{coin}_etf_data')
        if data and data.get('daily_data'):
            print(f"最新3条记录:")
            for row in data['daily_data'][:3]:
                print(f"  {row}")
