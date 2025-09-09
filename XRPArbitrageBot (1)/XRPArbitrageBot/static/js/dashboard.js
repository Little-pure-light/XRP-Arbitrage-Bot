// XRP Arbitrage Trading System - Dashboard JavaScript

class TradingDashboard {
    constructor() {
        this.isTrading = false;
        this.priceChart = null;
        this.updateIntervals = {};
        this.lastPrices = {};
        
        this.init();
    }
    
    init() {
        this.bindEvents();
        this.loadInitialData();
        console.log('Trading Dashboard initialized');
    }
    
    bindEvents() {
        // Trading control buttons
        document.getElementById('start-trading-btn')?.addEventListener('click', () => this.startTrading());
        document.getElementById('stop-trading-btn')?.addEventListener('click', () => this.stopTrading());
        
        // Price update events
        document.addEventListener('priceUpdate', (e) => this.handlePriceUpdate(e.detail));
        document.addEventListener('balanceUpdate', (e) => this.handleBalanceUpdate(e.detail));
    }
    
    async loadInitialData() {
        try {
            await Promise.all([
                this.updatePrices(),
                this.updateBalances(),
                this.updateTodayStats(),
                this.updateSystemStatus()
            ]);
        } catch (error) {
            console.error('Error loading initial data:', error);
            this.showError('Failed to load initial data');
        }
    }
    
    async updatePrices() {
        try {
            const response = await fetch('/api/prices');
            if (!response.ok) throw new Error('Failed to fetch prices');
            
            const data = await response.json();
            this.updatePriceDisplay(data);
            this.updateSpreadIndicator(data);
            
            // Store for chart updates
            this.lastPrices = data;
            
        } catch (error) {
            console.error('Error updating prices:', error);
            this.updatePriceStatus('error');
        }
    }
    
    updatePriceDisplay(data) {
        if (!data || !data['XRP/USDT'] || !data['XRP/USDC']) {
            return;
        }
        
        // Update XRP/USDT
        const usdtPrice = data['XRP/USDT'].price;
        const usdtElement = document.getElementById('xrp-usdt-price');
        if (usdtElement) {
            usdtElement.textContent = '$' + usdtPrice.toFixed(4);
            this.animateValueChange(usdtElement, this.lastPrices['XRP/USDT']?.price, usdtPrice);
        }
        
        // Update XRP/USDC
        const usdcPrice = data['XRP/USDC'].price;
        const usdcElement = document.getElementById('xrp-usdc-price');
        if (usdcElement) {
            usdcElement.textContent = '$' + usdcPrice.toFixed(4);
            this.animateValueChange(usdcElement, this.lastPrices['XRP/USDC']?.price, usdcPrice);
        }
        
        // Update price changes (simplified - would need historical data for real changes)
        this.updatePriceChange('xrp-usdt-change', 0.12); // Mock change
        this.updatePriceChange('xrp-usdc-change', -0.08); // Mock change
        
        // Update last update time
        const lastUpdateElement = document.getElementById('last-price-update');
        if (lastUpdateElement) {
            lastUpdateElement.textContent = new Date().toLocaleTimeString();
        }
        
        this.updatePriceStatus('connected');
    }
    
    updatePriceChange(elementId, changePercent) {
        const element = document.getElementById(elementId);
        if (!element) return;
        
        const sign = changePercent >= 0 ? '+' : '';
        element.textContent = `${sign}${changePercent.toFixed(2)}%`;
        
        element.className = 'price-change';
        if (changePercent > 0) {
            element.classList.add('positive');
        } else if (changePercent < 0) {
            element.classList.add('negative');
        } else {
            element.classList.add('neutral');
        }
    }
    
    updateSpreadIndicator(data) {
        if (!data.spread_percentage) return;
        
        const spreadValue = document.getElementById('spread-value');
        const spreadIndicator = document.getElementById('spread-indicator');
        
        if (spreadValue) {
            spreadValue.textContent = data.spread_percentage.toFixed(4) + '%';
        }
        
        if (spreadIndicator) {
            const threshold = 0.003; // 0.3% threshold
            
            if (data.spread_percentage >= threshold) {
                spreadIndicator.innerHTML = '<i class="fas fa-circle text-success"></i> Opportunity';
                spreadIndicator.classList.add('opportunity');
                spreadValue.classList.add('opportunity');
            } else {
                spreadIndicator.innerHTML = '<i class="fas fa-circle text-secondary"></i> No Opportunity';
                spreadIndicator.classList.remove('opportunity');
                spreadValue.classList.remove('opportunity');
            }
        }
    }
    
    async updateBalances() {
        try {
            const response = await fetch('/api/balances');
            if (!response.ok) throw new Error('Failed to fetch balances');
            
            const data = await response.json();
            this.updateBalanceDisplay(data);
            
        } catch (error) {
            console.error('Error updating balances:', error);
        }
    }
    
    updateBalanceDisplay(balances) {
        // Update individual balances
        ['XRP', 'USDT', 'USDC'].forEach(currency => {
            const balance = balances[currency];
            if (!balance) return;
            
            const balanceEl = document.getElementById(`${currency.toLowerCase()}-balance`);
            const lockedEl = document.getElementById(`${currency.toLowerCase()}-locked`);
            
            if (balanceEl) {
                balanceEl.textContent = balance.free.toLocaleString(undefined, {
                    minimumFractionDigits: 2,
                    maximumFractionDigits: 2
                });
            }
            
            if (lockedEl) {
                lockedEl.textContent = balance.locked.toLocaleString(undefined, {
                    minimumFractionDigits: 2,
                    maximumFractionDigits: 2
                });
            }
        });
        
        // Calculate and update portfolio total
        this.updatePortfolioTotal(balances);
    }
    
    updatePortfolioTotal(balances) {
        let total = 0;
        
        // Add stablecoin values
        if (balances.USDT) total += balances.USDT.total;
        if (balances.USDC) total += balances.USDC.total;
        
        // Add XRP value (assuming current price)
        if (balances.XRP && this.lastPrices['XRP/USDT']) {
            total += balances.XRP.total * this.lastPrices['XRP/USDT'].price;
        }
        
        const portfolioElement = document.getElementById('portfolio-total');
        if (portfolioElement) {
            portfolioElement.textContent = '$' + total.toLocaleString(undefined, {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2
            });
        }
    }
    
    async updateTodayStats() {
        try {
            const response = await fetch('/api/profit/stats');
            if (!response.ok) throw new Error('Failed to fetch stats');
            
            const data = await response.json();
            this.updateStatsDisplay(data);
            
        } catch (error) {
            console.error('Error updating today stats:', error);
        }
    }
    
    updateStatsDisplay(stats) {
        // Update today's trades count
        const tradesEl = document.getElementById('today-trades');
        if (tradesEl) {
            tradesEl.textContent = stats.total_trades || 0;
        }
        
        // Update P&L
        const pnlEl = document.getElementById('today-pnl');
        if (pnlEl) {
            const pnl = stats.total_profit_loss || 0;
            pnlEl.textContent = '$' + pnl.toFixed(2);
            
            pnlEl.className = 'stat-value profit-loss';
            if (pnl > 0) {
                pnlEl.classList.add('positive');
            } else if (pnl < 0) {
                pnlEl.classList.add('negative');
            }
        }
        
        // Update volume
        const volumeEl = document.getElementById('today-volume');
        if (volumeEl) {
            volumeEl.textContent = (stats.total_volume || 0).toLocaleString();
        }
        
        // Update success rate
        const successEl = document.getElementById('success-rate');
        if (successEl) {
            successEl.textContent = (stats.success_rate || 0).toFixed(1) + '%';
        }
    }
    
    async updateRecentTrades() {
        try {
            const response = await fetch('/api/trades/recent?limit=10');
            if (!response.ok) throw new Error('Failed to fetch recent trades');
            
            const trades = await response.json();
            this.updateRecentTradesTable(trades);
            
        } catch (error) {
            console.error('Error updating recent trades:', error);
        }
    }
    
    updateRecentTradesTable(trades) {
        const tbody = document.getElementById('recent-trades');
        if (!tbody) return;
        
        if (!trades || trades.length === 0) {
            tbody.innerHTML = '<tr><td colspan="7" class="text-center text-muted">No recent trades</td></tr>';
            return;
        }
        
        tbody.innerHTML = trades.map(trade => {
            const time = new Date(trade.created_at).toLocaleTimeString();
            const pnl = trade.profit_loss || 0;
            const pnlClass = pnl > 0 ? 'text-success' : pnl < 0 ? 'text-danger' : 'text-muted';
            const statusClass = this.getStatusClass(trade.status);
            
            return `
                <tr>
                    <td>${time}</td>
                    <td class="text-uppercase fw-bold ${trade.type === 'buy' ? 'text-success' : 'text-danger'}">${trade.type}</td>
                    <td>${trade.pair}</td>
                    <td>${trade.amount.toFixed(2)}</td>
                    <td>$${trade.price.toFixed(4)}</td>
                    <td class="${pnlClass}">$${pnl.toFixed(2)}</td>
                    <td><span class="badge ${statusClass}">${trade.status}</span></td>
                </tr>
            `;
        }).join('');
    }
    
    getStatusClass(status) {
        switch (status) {
            case 'completed': return 'bg-success';
            case 'pending': return 'bg-warning';
            case 'failed': return 'bg-danger';
            default: return 'bg-secondary';
        }
    }
    
    async updateSystemStatus() {
        try {
            const response = await fetch('/api/system-status');
            if (!response.ok) throw new Error('Failed to fetch system status');
            
            const status = await response.json();
            this.updateStatusDisplay(status);
            
        } catch (error) {
            console.error('Error updating system status:', error);
            this.updatePriceStatus('error');
        }
    }
    
    updateStatusDisplay(status) {
        // Update trading status
        const tradingStatusEl = document.getElementById('trading-status');
        if (tradingStatusEl) {
            tradingStatusEl.textContent = status.trading_active ? 'Running' : 'Stopped';
            tradingStatusEl.className = `badge ${status.trading_active ? 'bg-success' : 'bg-secondary'}`;
        }
        
        // Update API status
        const apiStatusEl = document.getElementById('api-status');
        if (apiStatusEl) {
            if (status.api_connected) {
                apiStatusEl.innerHTML = '<i class="fas fa-check-circle"></i> Connected';
                apiStatusEl.className = 'text-success';
            } else {
                apiStatusEl.innerHTML = '<i class="fas fa-times-circle"></i> Disconnected';
                apiStatusEl.className = 'text-danger';
            }
        }
        
        // Update pending orders
        const pendingEl = document.getElementById('pending-orders');
        if (pendingEl) {
            pendingEl.textContent = status.pending_orders || 0;
        }
        
        // Update button states
        this.updateButtonStates(status.trading_active);
    }
    
    updateButtonStates(isTrading) {
        const startBtn = document.getElementById('start-trading-btn');
        const stopBtn = document.getElementById('stop-trading-btn');
        
        if (startBtn && stopBtn) {
            startBtn.disabled = isTrading;
            stopBtn.disabled = !isTrading;
            
            if (isTrading) {
                startBtn.innerHTML = '<i class="fas fa-play me-2"></i>Running...';
                stopBtn.innerHTML = '<i class="fas fa-stop me-2"></i>Stop Trading';
            } else {
                startBtn.innerHTML = '<i class="fas fa-play me-2"></i>Start Trading';
                stopBtn.innerHTML = '<i class="fas fa-stop me-2"></i>Stopped';
            }
        }
        
        this.isTrading = isTrading;
    }
    
    updatePriceStatus(status) {
        const statusEl = document.getElementById('price-update-status');
        if (!statusEl) return;
        
        switch (status) {
            case 'connected':
                statusEl.textContent = 'Live';
                statusEl.className = 'badge bg-success';
                break;
            case 'error':
                statusEl.textContent = 'Error';
                statusEl.className = 'badge bg-danger';
                break;
            case 'loading':
                statusEl.textContent = 'Loading';
                statusEl.className = 'badge bg-warning';
                break;
            default:
                statusEl.textContent = 'Unknown';
                statusEl.className = 'badge bg-secondary';
        }
    }
    
    async startTrading() {
        if (this.isTrading) return;
        
        try {
            this.showLoading('start-trading-btn');
            
            const response = await fetch('/api/start-trading', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.showSuccess('Trading started successfully');
                this.updateButtonStates(true);
            } else {
                this.showError('Failed to start trading: ' + result.message);
            }
            
        } catch (error) {
            console.error('Error starting trading:', error);
            this.showError('Failed to start trading');
        } finally {
            this.hideLoading('start-trading-btn');
        }
    }
    
    async stopTrading() {
        if (!this.isTrading) return;
        
        try {
            this.showLoading('stop-trading-btn');
            
            const response = await fetch('/api/stop-trading', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.showSuccess('Trading stopped successfully');
                this.updateButtonStates(false);
            } else {
                this.showError('Failed to stop trading: ' + result.message);
            }
            
        } catch (error) {
            console.error('Error stopping trading:', error);
            this.showError('Failed to stop trading');
        } finally {
            this.hideLoading('stop-trading-btn');
        }
    }
    
    // Animation helpers
    animateValueChange(element, oldValue, newValue) {
        if (oldValue === undefined || oldValue === newValue) return;
        
        element.style.transition = 'color 0.3s ease';
        
        if (newValue > oldValue) {
            element.style.color = '#238636'; // Green
        } else if (newValue < oldValue) {
            element.style.color = '#da3633'; // Red
        }
        
        setTimeout(() => {
            element.style.color = '';
        }, 1000);
    }
    
    // UI helpers
    showLoading(buttonId) {
        const button = document.getElementById(buttonId);
        if (button) {
            button.disabled = true;
            button.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Loading...';
        }
    }
    
    hideLoading(buttonId) {
        const button = document.getElementById(buttonId);
        if (button) {
            button.disabled = false;
            // Button text will be updated by updateButtonStates
        }
    }
    
    showSuccess(message) {
        this.showAlert(message, 'success');
    }
    
    showError(message) {
        this.showAlert(message, 'danger');
    }
    
    showAlert(message, type) {
        // Create alert element
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
        alertDiv.innerHTML = `
            <i class="fas fa-${type === 'success' ? 'check-circle' : 'exclamation-triangle'} me-2"></i>
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        // Insert at top of main content
        const main = document.querySelector('main');
        main.insertBefore(alertDiv, main.firstChild);
        
        // Auto remove after 5 seconds
        setTimeout(() => {
            if (alertDiv.parentNode) {
                alertDiv.remove();
            }
        }, 5000);
    }
    
    handlePriceUpdate(data) {
        this.updatePriceDisplay(data);
        this.updateSpreadIndicator(data);
    }
    
    handleBalanceUpdate(data) {
        this.updateBalanceDisplay(data);
    }
}

// Global functions for template usage
window.initializeDashboard = () => {
    window.dashboard = new TradingDashboard();
};

window.updatePrices = () => {
    if (window.dashboard) {
        window.dashboard.updatePrices();
    }
};

window.updateBalances = () => {
    if (window.dashboard) {
        window.dashboard.updateBalances();
    }
};

window.updateTodayStats = () => {
    if (window.dashboard) {
        window.dashboard.updateTodayStats();
    }
};

window.updateRecentTrades = () => {
    if (window.dashboard) {
        window.dashboard.updateRecentTrades();
    }
};

window.updateSystemStatus = () => {
    if (window.dashboard) {
        window.dashboard.updateSystemStatus();
    }
};

window.startTrading = () => {
    if (window.dashboard) {
        window.dashboard.startTrading();
    }
};

window.stopTrading = () => {
    if (window.dashboard) {
        window.dashboard.stopTrading();
    }
};
