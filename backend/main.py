from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from datetime import datetime, timedelta
import asyncio
from scraper import get_all_data, get_global_markets, get_crypto_prices, auto_update_etf

app = FastAPI(title="GlobalMarket API")

# 挂载静态文件
app.mount("/static", StaticFiles(directory="../frontend"), name="static")

# 全局数据缓存
cached_data = {}
last_etf_update = None  # 上次 ETF 更新时间


def load_last_etf_update_time():
    """从文件加载上次 ETF 更新时间"""
    import json
    import os
    filepath = os.path.join(os.path.dirname(__file__), 'last_etf_update.json')
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return datetime.fromisoformat(data['last_update'])
        except:
            return None
    return None


def save_last_etf_update_time(update_time):
    """保存 ETF 更新时间的文件"""
    import json
    import os
    filepath = os.path.join(os.path.dirname(__file__), 'last_etf_update.json')
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump({'last_update': update_time.isoformat()}, f)


def should_update_etf():
    """判断是否需要更新 ETF 数据（每天 10:00 后）"""
    global last_etf_update
    
    # 如果是周末，不更新 ETF
    weekday = datetime.now().weekday()
    if weekday >= 5:  # 周六、周日
        return False
    
    # 如果从未更新过，需要更新
    if last_etf_update is None:
        last_etf_update = load_last_etf_update_time()
    
    if last_etf_update is None:
        return True
    
    # 检查是否是今天 10:00 之后更新的
    now = datetime.now()
    today_10am = now.replace(hour=10, minute=0, second=0, microsecond=0)
    
    # 如果现在是 10:00 之前，不更新
    if now < today_10am:
        return False
    
    # 如果上次更新是今天 10:00 之后，不更新
    if last_etf_update.date() == now.date() and last_etf_update >= today_10am:
        return False
    
    # 需要更新（今天 10:00 后还没更新过）
    return True

@app.on_event("startup")
async def startup_event():
    """启动时加载数据"""
    global cached_data, last_etf_update
    cached_data = get_all_data()
    last_etf_update = load_last_etf_update_time()
    print(f"启动完成，数据加载成功")
    if last_etf_update:
        print(f"上次 ETF 更新时间: {last_etf_update}")


@app.get("/")
@app.head("/")
async def root():
    """返回前端页面"""
    return FileResponse("../frontend/index.html")


@app.get("/api/data")
async def get_data(background_tasks: BackgroundTasks):
    """获取所有数据"""
    global cached_data, last_etf_update
    
    # 每次请求都更新市场数据（保持最新）
    cached_data['markets'] = get_global_markets()
    cached_data['crypto'] = get_crypto_prices()
    
    # 检查是否需要更新 ETF 数据
    if should_update_etf():
        print(f"[{datetime.now()}] 开始更新 ETF 数据...")
        background_tasks.add_task(update_etf_data)
    
    return {
        'data': cached_data,
        'server_time': datetime.now().isoformat(),
        'etf_last_updated': last_etf_update.isoformat() if last_etf_update else None
    }


async def update_etf_data():
    """更新 ETF 数据"""
    global last_etf_update
    
    try:
        for coin in ['btc', 'eth', 'sol', 'xrp']:
            success, msg = auto_update_etf(coin)
            print(f"[{datetime.now()}] {msg}")
        
        # 更新成功后记录时间（持久化到文件）
        last_etf_update = datetime.now()
        save_last_etf_update_time(last_etf_update)
        print(f"[{datetime.now()}] ETF 数据更新完成")
        
    except Exception as e:
        print(f"[{datetime.now()}] ETF 更新失败: {e}")


@app.get("/api/health")
@app.head("/api/health")
async def health_check():
    """健康检查"""
    return {
        'status': 'ok',
        'timestamp': datetime.now().isoformat(),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
