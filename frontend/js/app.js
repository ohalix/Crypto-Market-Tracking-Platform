/**
 * CryptoMarket 前端应用（支持 BTC + ETH + 实时价格）
 */

// 格式化数字
function formatNumber(num) {
    if (num === 0) return '0.0';
    const formatted = num.toFixed(1);
    return num > 0 ? `+${formatted}` : formatted;
}

// 格式化价格
function formatPrice(price) {
    if (!price) return '-';
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
function renderPrices(prices) {
    const container = document.getElementById('price-cards');
    if (!prices || !prices.btc || !prices.eth) {
        container.innerHTML = '<div class="price-card"><h3>价格加载中...</h3></div>';
        return;
    }

    const btcChangeClass = prices.btc.change_24h >= 0 ? 'positive' : 'negative';
    const ethChangeClass = prices.eth.change_24h >= 0 ? 'positive' : 'negative';

    container.innerHTML = `
        <div class="price-card btc">
            <div class="price-header">
                <img src="https://cryptologos.cc/logos/bitcoin-btc-logo.png" alt="BTC" class="coin-icon">
                <h3>Bitcoin</h3>
            </div>
            <div class="price-value">${formatPrice(prices.btc.price)}</div>
            <div class="price-change ${btcChangeClass}">${formatPercent(prices.btc.change_24h)}</div>
        </div>
        <div class="price-card eth">
            <div class="price-header">
                <img src="https://cryptologos.cc/logos/ethereum-eth-logo.png" alt="ETH" class="coin-icon">
                <h3>Ethereum</h3>
            </div>
            <div class="price-value">${formatPrice(prices.eth.price)}</div>
            <div class="price-change ${ethChangeClass}">${formatPercent(prices.eth.change_24h)}</div>
        </div>
    `;
}

// 渲染 ETF 汇总卡片
function renderETFSummary(data, containerId, coin) {
    const container = document.getElementById(containerId);
    if (!data || !data.daily_data || data.daily_data.length === 0) {
        container.innerHTML = '<div class="summary-card"><h3>暂无数据</h3></div>';
        return;
    }

    const latest = data.daily_data[0];
    const totalInflow = data.daily_data.reduce((sum, d) => sum + (d.total || 0), 0);
    const positiveDays = data.daily_data.filter(d => (d.total || 0) > 0).length;
    const negativeDays = data.daily_data.filter(d => (d.total || 0) < 0).length;

    const cards = [
        { title: '最新流入', value: latest.total || 0, class: (latest.total || 0) >= 0 ? 'positive' : 'negative' },
        { title: '累计流入', value: totalInflow, class: totalInflow >= 0 ? 'positive' : 'negative' },
        { title: '流入天数', value: positiveDays, class: 'positive' },
        { title: '流出天数', value: negativeDays, class: 'negative' }
    ];

    container.innerHTML = cards.map(card => `
        <div class="summary-card">
            <h3>${card.title}</h3>
            <div class="value ${card.class}">${formatNumber(card.value)}M</div>
        </div>
    `).join('');
}

// 渲染 ETF 表格
function renderETFTable(data, tbodyId, coin) {
    const tbody = document.getElementById(tbodyId);
    if (!data || !data.daily_data || data.daily_data.length === 0) {
        tbody.innerHTML = `<tr><td colspan="13">暂无数据</td></tr>`;
        return;
    }

    tbody.innerHTML = data.daily_data.map(row => {
        let cells;
        if (coin === 'btc') {
            cells = [
                row.date || '-',
                row.blackrock || 0, row.fidelity || 0, row.bitwise || 0,
                row.ark || 0, row.invesco || 0, row.franklin || 0,
                row.valkyrie || 0, row.vaneck || 0, row.wtree || 0,
                row.grayscale_gb || 0, row.grayscale_btc || 0, row.total || 0
            ];
        } else {
            cells = [
                row.date || '-',
                row.blackrock || 0, row.fidelity || 0, row.bitwise || 0,
                row.shares21 || 0, row.vaneck || 0, row.invesco || 0,
                row.franklin || 0, row.grayscale_et || 0, row.grayscale_eth || 0,
                row.total || 0
            ];
        }

        return `
            <tr>
                ${cells.map((cell, index) => {
                    if (index === 0) return `<td>${cell}</td>`;
                    const value = parseFloat(cell) || 0;
                    const className = value > 0 ? 'positive' : value < 0 ? 'negative' : '';
                    return `<td class="${className}">${formatNumber(value)}</td>`;
                }).join('')}
            </tr>
        `;
    }).join('');
}

// 更新页面
async function updatePage() {
    const result = await fetchData();
    
    if (result && result.data) {
        const { data, server_time } = result;
        
        // 渲染价格
        if (data.prices) {
            renderPrices(data.prices);
        }
        
        // 渲染 BTC
        if (data.btc) {
            const btcUpdateEl = document.getElementById('btc-last-update');
            if (btcUpdateEl) {
                btcUpdateEl.textContent = `最后更新: ${formatDate(data.btc.last_updated)}`;
            }
            renderETFSummary(data.btc, 'btc-summary', 'btc');
            renderETFTable(data.btc, 'btc-table-body', 'btc');
        }
        
        // 渲染 ETH
        if (data.eth) {
            const ethUpdateEl = document.getElementById('eth-last-update');
            if (ethUpdateEl) {
                ethUpdateEl.textContent = `最后更新: ${formatDate(data.eth.last_updated)}`;
            }
            renderETFSummary(data.eth, 'eth-summary', 'eth');
            renderETFTable(data.eth, 'eth-table-body', 'eth');
        }
    } else {
        console.error('数据加载失败');
    }
}

// TAB 切换功能
function initTabs() {
    const tabBtns = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');
    
    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            // 移除所有 active
            tabBtns.forEach(b => b.classList.remove('active'));
            tabContents.forEach(c => c.classList.remove('active'));
            
            // 添加 active 到当前
            btn.classList.add('active');
            const tabId = btn.getAttribute('data-tab') + '-tab';
            document.getElementById(tabId).classList.add('active');
        });
    });
}

// 初始化
async function init() {
    await updatePage();
    initTabs();
    
    // 每 5 分钟自动刷新
    setInterval(updatePage, 5 * 60 * 1000);
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', init);
