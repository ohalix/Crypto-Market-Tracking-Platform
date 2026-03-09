/**
 * GlobalMarket 前端应用
 * 支持：全球股指、核心指标、加密货币、ETF数据
 */

// 格式化数字
function formatNumber(num) {
    if (num === 0) return '0.0';
    const formatted = num.toFixed(1);
    return num > 0 ? `+${formatted}` : formatted;
}

// 格式化价格
function formatPrice(price, isIndex = false) {
    if (!price) return '-';
    if (isIndex) {
        return price.toLocaleString('en-US', {maximumFractionDigits: 0});
    }
    return '$' + price.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2});
}

// 格式化百分比
function formatPercent(value) {
    if (!value) return '0.00%';
    const sign = value >= 0 ? '+' : '';
    return `${sign}${value.toFixed(2)}%`;
}

// 格式化日期
function formatDate(dateStr) {
    if (!dateStr || dateStr === 'Invalid Date') return '未知';
    try {
        const date = new Date(dateStr);
        if (isNaN(date.getTime())) return '未知';
        return date.toLocaleString('zh-CN');
    } catch (e) {
        return '未知';
    }
}

// 获取数据
async function fetchData() {
    try {
        const response = await fetch('/api/data');
        if (!response.ok) throw new Error('获取数据失败');
        return await response.json();
    } catch (error) {
        console.error('Error:', error);
        return null;
    }
}

// 渲染价格卡片
function renderPriceCard(containerId, data, isIndex = false) {
    const container = document.getElementById(containerId);
    if (!container) return;
    
    container.innerHTML = Object.entries(data).map(([key, item]) => {
        const changeClass = item.change_pct >= 0 ? 'positive' : 'negative';
        return `
            <div class="price-card">
                <h3>${item.name}</h3>
                <div class="price-value">${formatPrice(item.price, isIndex)}</div>
                <div class="price-change ${changeClass}">${formatPercent(item.change_pct)}</div>
            </div>
        `;
    }).join('');
}

// 渲染核心指标
function renderCoreIndicators(coreData) {
    renderPriceCard('core-cards', coreData);
}

// 渲染全球股指
function renderGlobalIndices(indicesData) {
    renderPriceCard('index-cards', indicesData, true);
}

// 渲染加密货币
function renderCrypto(cryptoData) {
    const container = document.getElementById('crypto-cards');
    if (!container || !cryptoData) return;
    
    const coins = ['BTC', 'ETH', 'SOL', 'XRP'];
    const names = {'BTC': 'Bitcoin', 'ETH': 'Ethereum', 'SOL': 'Solana', 'XRP': 'XRP'};
    
    container.innerHTML = coins.map(coin => {
        const data = cryptoData[coin];
        if (!data) return '';
        const changeClass = data.change_pct >= 0 ? 'positive' : 'negative';
        return `
            <div class="price-card crypto">
                <h3>${names[coin]}</h3>
                <div class="price-value">${formatPrice(data.price)}</div>
                <div class="price-change ${changeClass}">${formatPercent(data.change_pct)}</div>
            </div>
        `;
    }).join('');
}

// 计算连续流入/流出天数
function calculateConsecutiveDays(dailyData) {
    if (!dailyData || dailyData.length === 0) return 0;
    
    // 从最新日期开始倒序检查
    let consecutiveDays = 0;
    let lastDirection = 0; // 0=无, 1=流入, -1=流出
    
    for (let i = dailyData.length - 1; i >= 0; i--) {
        const total = dailyData[i].total || 0;
        const currentDirection = total > 0 ? 1 : (total < 0 ? -1 : 0);
        
        if (currentDirection === 0) continue; // 跳过0值
        
        if (lastDirection === 0) {
            // 第一个非零值
            lastDirection = currentDirection;
            consecutiveDays = 1;
        } else if (currentDirection === lastDirection) {
            // 方向相同，继续计数
            consecutiveDays++;
        } else {
            // 方向改变，停止计数
            break;
        }
    }
    
    // 返回带符号的天数（正数=流入，负数=流出）
    return lastDirection * consecutiveDays;
}

// 渲染 ETF 汇总
function renderETFSummary(data, containerId) {
    const container = document.getElementById(containerId);
    if (!container || !data || !data.daily_data || data.daily_data.length === 0) {
        if (container) container.innerHTML = '<div class="summary-card"><h3>暂无数据</h3></div>';
        return;
    }

    // 取最新数据（数组最后一个）
    const latest = data.daily_data[data.daily_data.length - 1];
    const totalInflow = data.daily_data.reduce((sum, d) => sum + (d.total || 0), 0);
    const consecutiveDays = calculateConsecutiveDays(data.daily_data);

    const cards = [
        { title: '最新流入', value: latest.total || 0, class: (latest.total || 0) >= 0 ? 'positive' : 'negative', isMoney: true },
        { title: '累计流入', value: totalInflow, class: totalInflow >= 0 ? 'positive' : 'negative', isMoney: true },
        { title: '连续流入(流出)天数', value: consecutiveDays, class: consecutiveDays >= 0 ? 'positive' : 'negative', isMoney: false }
    ];

    container.innerHTML = cards.map(card => `
        <div class="summary-card">
            <h3>${card.title}</h3>
            <div class="value ${card.class}">${card.isMoney ? formatNumber(card.value) + 'M' : (card.value > 0 ? '+' : '') + card.value + '天'}</div>
        </div>
    `).join('');
}

// 渲染 ETF 表格
function renderETFTable(data, tbodyId, coin) {
    const tbody = document.getElementById(tbodyId);
    if (!tbody || !data || !data.daily_data) {
        if (tbody) tbody.innerHTML = '<tr><td colspan="13">暂无数据</td></tr>';
        return;
    }

    // 渲染数据行
    let html = data.daily_data.map(row => {
        let cells;
        if (coin === 'btc') {
            cells = [row.date, row.blackrock, row.fidelity, row.bitwise, row.ark, row.invesco, 
                     row.franklin, row.valkyrie, row.vaneck, row.wtree, row.grayscale_gb, row.grayscale_btc, row.total];
        } else if (coin === 'eth') {
            cells = [row.date, row.blackrock, row.fidelity, row.bitwise, row.shares21, row.vaneck, 
                     row.invesco, row.franklin, row.grayscale_et, row.grayscale_eth, row.total];
        } else if (coin === 'sol') {
            cells = [row.date, row.bitwise, row.vaneck1, row.vaneck2, row.vaneck3, 
                     row.franklin, row.grayscale, row.total];
        } else if (coin === 'xrp') {
            cells = [row.date, row.canary, row.bitwise, row.franklin, row.shares21, row.grayscale, row.total];
        }

        return `<tr>${cells.map((cell, idx) => {
            if (idx === 0) return `<td>${cell || '-'}</td>`;
            const value = parseFloat(cell) || 0;
            const className = value > 0 ? 'positive' : value < 0 ? 'negative' : '';
            return `<td class="${className}">${formatNumber(value)}</td>`;
        }).join('')}</tr>`;
    }).join('');

    // 添加 Total 行（使用数据文件中的 summary 数据）
    if (data.summary && data.summary.Total) {
        const totalRow = data.summary.Total;
        html += `<tr class="total-row" style="font-weight: bold; background: rgba(255,255,255,0.1);">${totalRow.map((cell, idx) => {
            if (idx === 0) return `<td>${cell}</td>`;
            const cleanCell = cell.toString().replace(/[(),]/g, '');
            const value = parseFloat(cleanCell) || 0;
            const className = value > 0 ? 'positive' : value < 0 ? 'negative' : '';
            return `<td class="${className}">${formatNumber(value)}</td>`;
        }).join('')}</tr>`;
    }

    tbody.innerHTML = html;
}

// 更新页面
async function updatePage() {
    const result = await fetchData();
    if (!result || !result.data) return;

    const { data } = result;

    // 渲染核心指标
    if (data.markets && data.markets.core) {
        renderCoreIndicators(data.markets.core);
    }

    // 渲染全球股指
    if (data.markets && data.markets.indices) {
        renderGlobalIndices(data.markets.indices);
    }

    // 渲染加密货币
    if (data.crypto) {
        renderCrypto(data.crypto);
    }

    // 渲染 ETF 数据
    ['btc', 'eth', 'sol', 'xrp'].forEach(coin => {
        const etfData = data[`${coin}_etf`];
        if (etfData) {
            const updateEl = document.getElementById(`${coin}-last-update`);
            if (updateEl) updateEl.textContent = `最后更新: ${formatDate(etfData.last_updated)}`;
            
            renderETFSummary(etfData, `${coin}-summary`);
            renderETFTable(etfData, `${coin}-table-body`, coin);
        }
    });
}

// TAB 切换
function initTabs() {
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
            
            btn.classList.add('active');
            document.getElementById(`${btn.dataset.tab}-tab`).classList.add('active');
        });
    });
}

// 初始化
async function init() {
    await updatePage();
    initTabs();
    setInterval(updatePage, 5 * 60 * 1000); // 每5分钟刷新
}

document.addEventListener('DOMContentLoaded', init);
