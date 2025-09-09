// XRP Arbitrage Trading System - Trading Monitor JavaScript

class TradingMonitor {
    constructor() {
        this.feedUpdateInterval = null;
        this.analyticsUpdateInterval = null;
        this.charts = {};
        this.tradingFeed = [];
        this.maxFeedItems = 1000;
        
        this.init();
    }
    
    init() {
        this.bindEvents();
        this.initializeCharts();
        this.startPeriodicUpdates();
        console.log('Trading Monitor initialized');
    }
    
    bindEvents() {
        // History query form
        document.getElementById('history-query-form')?.addEventListener('submit', (e) => {
            e.preventDefault();
            this.executeHistoryQuery();
        });
        
        // Chart timeframe selectors
        document.getElementById('pnl-timeframe')?.addEventListener('change', (e) => {
            this.updatePnlChart(e.target.value);
        });
        
        // Spread chart buttons
        document.querySelectorAll('[onclick*="updateSpreadChart"]').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                const timeframe = e.target.getAttribute('onclick').match(/'(\w+)'/)[1];
                this.updateSpreadChart(timeframe);
                
                // Update active button
                document.querySelectorAll('[onclick*="updateSpreadChart"]').forEach(b => b.classList.remove('active'));
                e.target.classList.add('active');
            });
        });
    }
    
    initializeCharts() {
        // Initialize all charts
        this.initializePnlChart();
        this.initializeDistributionChart();
        this.initializeSpreadChart();
    }
    
    startPeriodicUpdates() {
        // Update trading feed every 3 seconds
        this.feedUpdateInterval = setInterval(() => {
            this.updateTradingFeed();
        }, 3000);
        
        // Update analytics every 10 seconds
        this.analyticsUpdateInterval = setInterval(() => {
            this.updateAnalytics();
        }, 10000);
        
        // Update charts every 30 seconds
        setInterval(() => {
            this.updateCharts();
        }, 30000);
    }
    
    async updateTradingFeed() {
        try {
            const response = await fetch('/api/trades/recent?limit=20');
            if (!response.ok) throw new Error('Failed to fetch recent trades');
            
            const trades = await response.json();
            this.updateFeedWithTrades(trades);
            
        } catch (error) {
            console.error('Error updating trading feed:', error);
            this.updateFeedStatus('error');
        }
    }
    
    updateFeedWithTrades(trades) {
        if (!trades || trades.length === 0) return;
        
        const feedContainer = document.getElementById('trading-feed');
        if (!feedContainer) return;
        
        // Check for new trades
        const newTrades = trades.filter(trade => 
            !this.tradingFeed.some(existing => existing.id === trade.id)
        );
        
        // Add new trades to the beginning of the feed
        newTrades.reverse().forEach(trade => {
            this.addTradeToFeed(trade, true);
        });
        
        // Update internal feed array
        this.tradingFeed = trades;
        
        // Limit feed size
        this.limitFeedSize();
        
        this.updateFeedStatus('live');
    }
    
    addTradeToFeed(trade, isNew = false) {
        const feedContainer = document.getElementById('trading-feed');
        if (!feedContainer) return;
        
        const time = new Date(trade.created_at).toLocaleTimeString();
        const pnl = trade.profit_loss || 0;
        const pnlText = pnl !== 0 ? `P&L: $${pnl.toFixed(2)}` : '';
        const pnlClass = pnl > 0 ? 'text-success' : pnl < 0 ? 'text-danger' : 'text-muted';
        
        const feedItem = document.createElement('div');
        feedItem.className = `feed-item ${isNew ? 'new' : ''}`;
        feedItem.innerHTML = `
            <div class="d-flex justify-content-between align-items-start">
                <div class="flex-grow-1">
                    <div class="d-flex align-items-center gap-2 mb-1">
                        <span class="feed-item-type ${trade.type}">${trade.type.toUpperCase()}</span>
                        <span class="text-muted">${trade.pair}</span>
                        <span class="badge ${this.getStatusClass(trade.status)}">${trade.status}</span>
                    </div>
                    <div class="feed-item-details">
                        Amount: ${trade.amount.toFixed(2)} XRP @ $${trade.price.toFixed(4)}
                        ${pnlText ? `<span class="ms-2 ${pnlClass}">${pnlText}</span>` : ''}
                    </div>
                </div>
                <div class="feed-item-time">${time}</div>
            </div>
        `;
        
        // Insert at the beginning
        if (feedContainer.firstChild && feedContainer.firstChild.classList?.contains('text-center')) {
            // Replace placeholder message
            feedContainer.innerHTML = '';
        }
        
        feedContainer.insertBefore(feedItem, feedContainer.firstChild);
        
        // Animate new items
        if (isNew) {
            setTimeout(() => feedItem.classList.remove('new'), 2000);
        }
    }
    
    limitFeedSize() {
        const feedContainer = document.getElementById('trading-feed');
        if (!feedContainer) return;
        
        const items = feedContainer.querySelectorAll('.feed-item');
        if (items.length > this.maxFeedItems) {
            for (let i = this.maxFeedItems; i < items.length; i++) {
                items[i].remove();
            }
        }
    }
    
    updateFeedStatus(status) {
        const statusEl = document.getElementById('feed-status');
        if (!statusEl) return;
        
        switch (status) {
            case 'live':
                statusEl.textContent = 'Live';
                statusEl.className = 'badge bg-success';
                break;
            case 'error':
                statusEl.textContent = 'Error';
                statusEl.className = 'badge bg-danger';
                break;
            case 'paused':
                statusEl.textContent = 'Paused';
                statusEl.className = 'badge bg-warning';
                break;
        }
    }
    
    async updateAnalytics() {
        try {
            const response = await fetch('/api/profit/stats');
            if (!response.ok) throw new Error('Failed to fetch analytics');
            
            const stats = await response.json();
            this.updateAnalyticsDisplay(stats);
            
        } catch (error) {
            console.error('Error updating analytics:', error);
        }
    }
    
    updateAnalyticsDisplay(stats) {
        // Update key metrics
        const totalPnlEl = document.getElementById('total-pnl');
        if (totalPnlEl) {
            const pnl = stats.total_profit_loss || 0;
            totalPnlEl.textContent = '$' + pnl.toFixed(2);
            totalPnlEl.className = 'metric-value profit-loss';
            if (pnl > 0) {
                totalPnlEl.classList.add('positive');
            } else if (pnl < 0) {
                totalPnlEl.classList.add('negative');
            }
        }
        
        const winRateEl = document.getElementById('win-rate');
        if (winRateEl) {
            winRateEl.textContent = (stats.success_rate || 0).toFixed(1) + '%';
        }
        
        const avgTradeEl = document.getElementById('avg-trade');
        if (avgTradeEl) {
            avgTradeEl.textContent = '$' + (stats.avg_profit_per_trade || 0).toFixed(2);
        }
        
        const maxDrawdownEl = document.getElementById('max-drawdown');
        if (maxDrawdownEl && stats.drawdown) {
            maxDrawdownEl.textContent = '$' + (stats.drawdown.max_drawdown || 0).toFixed(2);
        }
        
        // Update risk indicators
        this.updateRiskIndicators(stats);
        
        // Update quick stats
        this.updateQuickStats(stats);
    }
    
    updateRiskIndicators(stats) {
        // Risk score
        const riskScoreEl = document.getElementById('risk-score');
        if (riskScoreEl && stats.risk_metrics) {
            const riskScore = stats.risk_metrics.risk_score || 0;
            let riskLevel, riskClass;
            
            if (riskScore < 30) {
                riskLevel = 'Low';
                riskClass = 'bg-success';
            } else if (riskScore < 60) {
                riskLevel = 'Medium';
                riskClass = 'bg-warning';
            } else {
                riskLevel = 'High';
                riskClass = 'bg-danger';
            }
            
            riskScoreEl.textContent = riskLevel;
            riskScoreEl.className = `badge ${riskClass}`;
        }
        
        // Volatility level
        const volatilityEl = document.getElementById('volatility-level');
        if (volatilityEl && stats.risk_metrics) {
            const volatility = stats.risk_metrics.volatility || 0;
            let level;
            
            if (volatility < 0.01) {
                level = 'Low';
            } else if (volatility < 0.03) {
                level = 'Normal';
            } else {
                level = 'High';
            }
            
            volatilityEl.textContent = level;
        }
        
        // Daily volume usage (mock calculation)
        const dailyVolumeEl = document.getElementById('daily-volume-usage');
        if (dailyVolumeEl) {
            const usage = ((stats.total_volume || 0) / 5000 * 100).toFixed(1);
            dailyVolumeEl.textContent = usage + '%';
        }
    }
    
    updateQuickStats(stats) {
        // Active since (mock - would need start time tracking)
        const activeSinceEl = document.getElementById('active-since');
        if (activeSinceEl) {
            activeSinceEl.textContent = '2 hours 15 min';
        }
        
        // Opportunities today (mock - would need opportunity tracking)
        const opportunitiesEl = document.getElementById('opportunities-today');
        if (opportunitiesEl) {
            opportunitiesEl.textContent = Math.floor(Math.random() * 20) + 10;
        }
        
        // Execution rate
        const executionRateEl = document.getElementById('execution-rate');
        if (executionRateEl) {
            const rate = stats.total_trades > 0 ? ((stats.profitable_trades_count || 0) / stats.total_trades * 100) : 0;
            executionRateEl.textContent = rate.toFixed(1) + '%';
        }
        
        // Best spread (mock)
        const bestSpreadEl = document.getElementById('best-spread');
        if (bestSpreadEl) {
            bestSpreadEl.textContent = '0.045%';
        }
    }
    
    async executeHistoryQuery() {
        const period = document.getElementById('query-period')?.value || '24h';
        const status = document.getElementById('query-status')?.value || 'all';
        const pair = document.getElementById('query-pair')?.value || 'all';
        
        try {
            let url = `/api/trades/recent?limit=1000`;
            const response = await fetch(url);
            if (!response.ok) throw new Error('Failed to fetch trade history');
            
            let trades = await response.json();
            
            // Filter trades based on query parameters
            trades = this.filterTrades(trades, { period, status, pair });
            
            // Update detailed trades table
            this.updateDetailedTradesTable(trades);
            
            // Update query results summary
            this.updateQueryResults(trades);
            
            // Show results panel
            const resultsPanel = document.getElementById('query-results');
            if (resultsPanel) {
                resultsPanel.style.display = 'block';
            }
            
        } catch (error) {
            console.error('Error executing history query:', error);
            this.showError('Failed to execute query');
        }
    }
    
    filterTrades(trades, filters) {
        return trades.filter(trade => {
            // Status filter
            if (filters.status !== 'all' && trade.status !== filters.status) {
                return false;
            }
            
            // Pair filter
            if (filters.pair !== 'all' && trade.pair !== filters.pair) {
                return false;
            }
            
            // Period filter (simplified - would need proper date filtering)
            const tradeDate = new Date(trade.created_at);
            const now = new Date();
            const hoursDiff = (now - tradeDate) / (1000 * 60 * 60);
            
            switch (filters.period) {
                case '1h':
                    return hoursDiff <= 1;
                case '6h':
                    return hoursDiff <= 6;
                case '24h':
                    return hoursDiff <= 24;
                case '7d':
                    return hoursDiff <= 168; // 7 * 24
                case '30d':
                    return hoursDiff <= 720; // 30 * 24
                default:
                    return true;
            }
        });
    }
    
    updateQueryResults(trades) {
        const totalEl = document.getElementById('query-total');
        const volumeEl = document.getElementById('query-volume');
        const pnlEl = document.getElementById('query-pnl');
        
        if (totalEl) totalEl.textContent = trades.length;
        
        const totalVolume = trades.reduce((sum, trade) => sum + trade.amount, 0);
        if (volumeEl) volumeEl.textContent = totalVolume.toFixed(0) + ' XRP';
        
        const totalPnl = trades.reduce((sum, trade) => sum + (trade.profit_loss || 0), 0);
        if (pnlEl) {
            pnlEl.textContent = '$' + totalPnl.toFixed(2);
            pnlEl.className = 'profit-loss';
            if (totalPnl > 0) {
                pnlEl.classList.add('positive');
            } else if (totalPnl < 0) {
                pnlEl.classList.add('negative');
            }
        }
    }
    
    updateDetailedTradesTable(trades) {
        const tbody = document.getElementById('detailed-trades');
        if (!tbody) return;
        
        if (!trades || trades.length === 0) {
            tbody.innerHTML = '<tr><td colspan="10" class="text-center text-muted">No trades found</td></tr>';
            return;
        }
        
        tbody.innerHTML = trades.map(trade => {
            const timestamp = new Date(trade.created_at).toLocaleString();
            const pnl = trade.profit_loss || 0;
            const pnlClass = pnl > 0 ? 'text-success' : pnl < 0 ? 'text-danger' : 'text-muted';
            const statusClass = this.getStatusClass(trade.status);
            
            return `
                <tr>
                    <td class="small">${timestamp}</td>
                    <td>#${trade.id}</td>
                    <td class="text-uppercase fw-bold ${trade.type === 'buy' ? 'text-success' : 'text-danger'}">${trade.type}</td>
                    <td>${trade.pair}</td>
                    <td>${trade.amount.toFixed(2)}</td>
                    <td>$${trade.price.toFixed(4)}</td>
                    <td>$${trade.total_value.toFixed(2)}</td>
                    <td class="${pnlClass}">$${pnl.toFixed(2)}</td>
                    <td><span class="badge ${statusClass}">${trade.status}</span></td>
                    <td class="small text-muted">${trade.order_id || 'N/A'}</td>
                </tr>
            `;
        }).join('');
    }
    
    updateCharts() {
        this.updatePnlChart();
        this.updateDistributionChart();
        this.updateSpreadChart();
    }
    
    async updatePnlChart(timeframe = '24h') {
        if (!this.charts.pnlChart) return;
        
        try {
            const response = await fetch(`/api/chart/profit-trend?timeframe=${timeframe}`);
            if (!response.ok) throw new Error('Failed to fetch P&L data');
            
            const data = await response.json();
            this.charts.pnlChart.data.datasets[0].data = data.map(point => ({
                x: new Date(point.time),
                y: point.cumulative
            }));
            
            this.charts.pnlChart.update('none');
            
        } catch (error) {
            console.error('Error updating P&L chart:', error);
        }
    }
    
    async updateDistributionChart() {
        if (!this.charts.distributionChart) return;
        
        try {
            const response = await fetch('/api/profit/stats');
            if (!response.ok) throw new Error('Failed to fetch distribution data');
            
            const stats = await response.json();
            
            // Update with profit/loss distribution
            const profitable = stats.profitable_trades_count || 0;
            const losing = stats.losing_trades_count || 0;
            
            this.charts.distributionChart.data.datasets[0].data = [profitable, losing];
            this.charts.distributionChart.update('none');
            
        } catch (error) {
            console.error('Error updating distribution chart:', error);
        }
    }
    
    async updateSpreadChart(timeframe = '6h') {
        if (!this.charts.spreadChart) return;
        
        try {
            const response = await fetch(`/api/chart/price-history?hours=${this.getHoursFromTimeframe(timeframe)}`);
            if (!response.ok) throw new Error('Failed to fetch spread data');
            
            const data = await response.json();
            
            // Calculate spreads from price data
            const spreads = this.calculateSpreads(data);
            
            this.charts.spreadChart.data.datasets[0].data = spreads;
            this.charts.spreadChart.update('none');
            
        } catch (error) {
            console.error('Error updating spread chart:', error);
        }
    }
    
    calculateSpreads(data) {
        if (!data.usdt || !data.usdc || data.usdt.length === 0 || data.usdc.length === 0) {
            return [];
        }
        
        // Match timestamps and calculate spreads
        const spreads = [];
        
        data.usdt.forEach(usdtPoint => {
            const matchingUsdc = data.usdc.find(usdcPoint => 
                Math.abs(new Date(usdcPoint.time) - new Date(usdtPoint.time)) < 60000 // Within 1 minute
            );
            
            if (matchingUsdc) {
                const spread = Math.abs(usdtPoint.price - matchingUsdc.price);
                const spreadPct = (spread / Math.min(usdtPoint.price, matchingUsdc.price)) * 100;
                
                spreads.push({
                    x: new Date(usdtPoint.time),
                    y: spreadPct
                });
            }
        });
        
        return spreads;
    }
    
    getHoursFromTimeframe(timeframe) {
        switch (timeframe) {
            case '1h': return 1;
            case '6h': return 6;
            case '24h': return 24;
            default: return 6;
        }
    }
    
    getStatusClass(status) {
        switch (status) {
            case 'completed': return 'bg-success';
            case 'pending': return 'bg-warning';
            case 'failed': return 'bg-danger';
            case 'cancelled': return 'bg-secondary';
            default: return 'bg-secondary';
        }
    }
    
    clearTradingFeed() {
        const feedContainer = document.getElementById('trading-feed');
        if (feedContainer) {
            feedContainer.innerHTML = '<div class="feed-item text-center text-muted py-4"><i class="fas fa-clock me-2"></i>Feed cleared</div>';
            this.tradingFeed = [];
        }
    }
    
    exportTradeHistory() {
        // This would export the current trade history
        // For now, just show a message
        this.showSuccess('Export functionality would be implemented here');
    }
    
    loadInitialTrades() {
        this.updateTradingFeed();
    }
    
    initializePnlChart() {
        // This will be handled by charts.js
        if (window.initializePnlChart) {
            window.initializePnlChart();
        }
    }
    
    initializeDistributionChart() {
        // This will be handled by charts.js
        if (window.initializeDistributionChart) {
            window.initializeDistributionChart();
        }
    }
    
    initializeSpreadChart() {
        // This will be handled by charts.js
        if (window.initializeSpreadChart) {
            window.initializeSpreadChart();
        }
    }
    
    // UI helpers
    showSuccess(message) {
        this.showAlert(message, 'success');
    }
    
    showError(message) {
        this.showAlert(message, 'danger');
    }
    
    showAlert(message, type) {
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
        alertDiv.innerHTML = `
            <i class="fas fa-${type === 'success' ? 'check-circle' : 'exclamation-triangle'} me-2"></i>
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        const main = document.querySelector('main');
        main.insertBefore(alertDiv, main.firstChild);
        
        setTimeout(() => {
            if (alertDiv.parentNode) {
                alertDiv.remove();
            }
        }, 5000);
    }
    
    destroy() {
        // Clear intervals
        if (this.feedUpdateInterval) {
            clearInterval(this.feedUpdateInterval);
        }
        if (this.analyticsUpdateInterval) {
            clearInterval(this.analyticsUpdateInterval);
        }
        
        // Destroy charts
        Object.values(this.charts).forEach(chart => {
            if (chart && typeof chart.destroy === 'function') {
                chart.destroy();
            }
        });
    }
}

// Global functions for template usage
window.initializeMonitor = () => {
    window.monitor = new TradingMonitor();
};

window.updateTradingFeed = () => {
    if (window.monitor) {
        window.monitor.updateTradingFeed();
    }
};

window.updateAnalytics = () => {
    if (window.monitor) {
        window.monitor.updateAnalytics();
    }
};

window.updateCharts = () => {
    if (window.monitor) {
        window.monitor.updateCharts();
    }
};

window.executeHistoryQuery = () => {
    if (window.monitor) {
        window.monitor.executeHistoryQuery();
    }
};

window.updateSpreadChart = (timeframe) => {
    if (window.monitor) {
        window.monitor.updateSpreadChart(timeframe);
    }
};

window.clearTradingFeed = () => {
    if (window.monitor) {
        window.monitor.clearTradingFeed();
    }
};

window.exportTradeHistory = () => {
    if (window.monitor) {
        window.monitor.exportTradeHistory();
    }
};

window.loadInitialTrades = () => {
    if (window.monitor) {
        window.monitor.loadInitialTrades();
    }
};

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    if (window.monitor) {
        window.monitor.destroy();
    }
});
