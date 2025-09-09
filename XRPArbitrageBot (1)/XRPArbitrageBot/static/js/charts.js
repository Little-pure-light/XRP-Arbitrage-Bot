// XRP Arbitrage Trading System - Charts JavaScript

class TradingCharts {
    constructor() {
        this.charts = {};
        this.chartColors = {
            primary: '#0969da',
            success: '#238636',
            danger: '#da3633',
            warning: '#d29922',
            info: '#0969da',
            usdt: '#26a641',
            usdc: '#1f6feb',
            spread: '#f85149',
            grid: '#30363d',
            text: '#f0f6fc',
            textMuted: '#8b949e'
        };
        
        this.init();
    }
    
    init() {
        this.configureChartDefaults();
        console.log('Trading Charts initialized');
    }
    
    configureChartDefaults() {
        // Configure Chart.js defaults for dark theme
        Chart.defaults.color = this.chartColors.text;
        Chart.defaults.borderColor = this.chartColors.grid;
        Chart.defaults.backgroundColor = 'rgba(9, 105, 218, 0.1)';
        
        Chart.defaults.scales.linear.grid.color = this.chartColors.grid;
        Chart.defaults.scales.linear.ticks.color = this.chartColors.textMuted;
        Chart.defaults.scales.time.grid.color = this.chartColors.grid;
        Chart.defaults.scales.time.ticks.color = this.chartColors.textMuted;
        
        Chart.defaults.plugins.legend.labels.color = this.chartColors.text;
        Chart.defaults.plugins.tooltip.backgroundColor = 'rgba(33, 38, 45, 0.9)';
        Chart.defaults.plugins.tooltip.titleColor = this.chartColors.text;
        Chart.defaults.plugins.tooltip.bodyColor = this.chartColors.text;
        Chart.defaults.plugins.tooltip.borderColor = this.chartColors.grid;
        Chart.defaults.plugins.tooltip.borderWidth = 1;
    }
    
    // Dashboard Price Chart
    initializePriceChart() {
        const ctx = document.getElementById('priceChart');
        if (!ctx) return null;
        
        const config = {
            type: 'line',
            data: {
                datasets: [
                    {
                        label: 'XRP/USDT',
                        data: [],
                        borderColor: this.chartColors.usdt,
                        backgroundColor: 'rgba(38, 166, 65, 0.1)',
                        borderWidth: 2,
                        fill: false,
                        tension: 0.1,
                        pointRadius: 0,
                        pointHoverRadius: 4
                    },
                    {
                        label: 'XRP/USDC',
                        data: [],
                        borderColor: this.chartColors.usdc,
                        backgroundColor: 'rgba(31, 111, 235, 0.1)',
                        borderWidth: 2,
                        fill: false,
                        tension: 0.1,
                        pointRadius: 0,
                        pointHoverRadius: 4
                    },
                    {
                        label: 'Spread %',
                        data: [],
                        borderColor: this.chartColors.spread,
                        backgroundColor: 'rgba(248, 81, 73, 0.1)',
                        borderWidth: 1,
                        fill: false,
                        tension: 0.1,
                        pointRadius: 0,
                        pointHoverRadius: 4,
                        yAxisID: 'spread'
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    intersect: false,
                    mode: 'index'
                },
                plugins: {
                    legend: {
                        position: 'top',
                        align: 'end',
                        labels: {
                            boxWidth: 12,
                            padding: 15,
                            font: {
                                size: 12
                            }
                        }
                    },
                    tooltip: {
                        callbacks: {
                            title: function(context) {
                                if (context[0].parsed.x) {
                                    return new Date(context[0].parsed.x).toLocaleString();
                                }
                                return '';
                            },
                            label: function(context) {
                                if (context.datasetIndex === 2) { // Spread
                                    return `${context.dataset.label}: ${context.parsed.y.toFixed(4)}%`;
                                } else { // Prices
                                    return `${context.dataset.label}: $${context.parsed.y.toFixed(4)}`;
                                }
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        type: 'time',
                        time: {
                            displayFormats: {
                                minute: 'HH:mm',
                                hour: 'HH:mm'
                            }
                        },
                        title: {
                            display: false
                        },
                        grid: {
                            display: true,
                            color: this.chartColors.grid
                        }
                    },
                    y: {
                        type: 'linear',
                        display: true,
                        position: 'left',
                        title: {
                            display: true,
                            text: 'Price (USD)',
                            font: {
                                size: 12
                            }
                        },
                        grid: {
                            display: true,
                            color: this.chartColors.grid
                        }
                    },
                    spread: {
                        type: 'linear',
                        display: true,
                        position: 'right',
                        title: {
                            display: true,
                            text: 'Spread (%)',
                            font: {
                                size: 12
                            }
                        },
                        grid: {
                            display: false
                        },
                        min: 0
                    }
                },
                animation: {
                    duration: 0
                }
            }
        };
        
        this.charts.priceChart = new Chart(ctx, config);
        this.loadPriceHistory();
        
        return this.charts.priceChart;
    }
    
    async loadPriceHistory() {
        if (!this.charts.priceChart) return;
        
        try {
            const response = await fetch('/api/chart/price-history?hours=24');
            if (!response.ok) throw new Error('Failed to fetch price history');
            
            const data = await response.json();
            this.updatePriceChartData(data);
            
        } catch (error) {
            console.error('Error loading price history:', error);
        }
    }
    
    updatePriceChartData(data) {
        if (!this.charts.priceChart || !data.usdt || !data.usdc) return;
        
        // Update USDT dataset
        this.charts.priceChart.data.datasets[0].data = data.usdt.map(point => ({
            x: new Date(point.time),
            y: point.price
        }));
        
        // Update USDC dataset
        this.charts.priceChart.data.datasets[1].data = data.usdc.map(point => ({
            x: new Date(point.time),
            y: point.price
        }));
        
        // Calculate and update spread dataset
        const spreads = this.calculateSpreadFromPriceData(data);
        this.charts.priceChart.data.datasets[2].data = spreads;
        
        this.charts.priceChart.update('none');
    }
    
    calculateSpreadFromPriceData(data) {
        const spreads = [];
        
        data.usdt.forEach(usdtPoint => {
            const matchingUsdc = data.usdc.find(usdcPoint => 
                Math.abs(new Date(usdcPoint.time) - new Date(usdtPoint.time)) < 60000
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
    
    // Monitor P&L Chart
    initializePnlChart() {
        const ctx = document.getElementById('pnlChart');
        if (!ctx) return null;
        
        const config = {
            type: 'line',
            data: {
                datasets: [
                    {
                        label: 'Cumulative P&L',
                        data: [],
                        borderColor: this.chartColors.primary,
                        backgroundColor: 'rgba(9, 105, 218, 0.1)',
                        borderWidth: 2,
                        fill: true,
                        tension: 0.1,
                        pointRadius: 0,
                        pointHoverRadius: 4
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    intersect: false,
                    mode: 'index'
                },
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        callbacks: {
                            title: function(context) {
                                if (context[0].parsed.x) {
                                    return new Date(context[0].parsed.x).toLocaleString();
                                }
                                return '';
                            },
                            label: function(context) {
                                return `P&L: $${context.parsed.y.toFixed(2)}`;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        type: 'time',
                        time: {
                            displayFormats: {
                                minute: 'HH:mm',
                                hour: 'MMM DD HH:mm',
                                day: 'MMM DD'
                            }
                        },
                        title: {
                            display: false
                        },
                        grid: {
                            display: true,
                            color: this.chartColors.grid
                        }
                    },
                    y: {
                        title: {
                            display: true,
                            text: 'Cumulative P&L ($)',
                            font: {
                                size: 12
                            }
                        },
                        grid: {
                            display: true,
                            color: this.chartColors.grid
                        },
                        ticks: {
                            callback: function(value) {
                                return '$' + value.toFixed(2);
                            }
                        }
                    }
                },
                animation: {
                    duration: 0
                }
            }
        };
        
        this.charts.pnlChart = new Chart(ctx, config);
        this.loadPnlHistory();
        
        return this.charts.pnlChart;
    }
    
    async loadPnlHistory(timeframe = '24h') {
        if (!this.charts.pnlChart) return;
        
        try {
            const days = timeframe === '7d' ? 7 : timeframe === '30d' ? 30 : 1;
            const response = await fetch(`/api/chart/profit-trend?days=${days}`);
            if (!response.ok) throw new Error('Failed to fetch P&L history');
            
            const data = await response.json();
            
            this.charts.pnlChart.data.datasets[0].data = data.map(point => ({
                x: new Date(point.time),
                y: point.cumulative
            }));
            
            // Update line color based on final P&L
            const finalPnl = data.length > 0 ? data[data.length - 1].cumulative : 0;
            this.charts.pnlChart.data.datasets[0].borderColor = finalPnl >= 0 ? this.chartColors.success : this.chartColors.danger;
            this.charts.pnlChart.data.datasets[0].backgroundColor = finalPnl >= 0 ? 
                'rgba(35, 134, 54, 0.1)' : 'rgba(218, 54, 51, 0.1)';
            
            this.charts.pnlChart.update('none');
            
        } catch (error) {
            console.error('Error loading P&L history:', error);
        }
    }
    
    // Monitor Distribution Chart
    initializeDistributionChart() {
        const ctx = document.getElementById('distributionChart');
        if (!ctx) return null;
        
        const config = {
            type: 'doughnut',
            data: {
                labels: ['Profitable', 'Loss'],
                datasets: [
                    {
                        data: [0, 0],
                        backgroundColor: [
                            this.chartColors.success,
                            this.chartColors.danger
                        ],
                        borderColor: [
                            this.chartColors.success,
                            this.chartColors.danger
                        ],
                        borderWidth: 2,
                        hoverOffset: 4
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            boxWidth: 12,
                            padding: 15,
                            font: {
                                size: 12
                            }
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const label = context.label || '';
                                const value = context.parsed;
                                const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                const percentage = total > 0 ? ((value / total) * 100).toFixed(1) : '0.0';
                                return `${label}: ${value} (${percentage}%)`;
                            }
                        }
                    }
                },
                animation: {
                    duration: 750,
                    easing: 'easeInOutQuart'
                }
            }
        };
        
        this.charts.distributionChart = new Chart(ctx, config);
        this.loadDistributionData();
        
        return this.charts.distributionChart;
    }
    
    async loadDistributionData() {
        if (!this.charts.distributionChart) return;
        
        try {
            const response = await fetch('/api/profit/stats');
            if (!response.ok) throw new Error('Failed to fetch distribution data');
            
            const stats = await response.json();
            
            const profitable = stats.profitable_trades_count || 0;
            const losing = stats.losing_trades_count || 0;
            
            this.charts.distributionChart.data.datasets[0].data = [profitable, losing];
            this.charts.distributionChart.update();
            
        } catch (error) {
            console.error('Error loading distribution data:', error);
        }
    }
    
    // Monitor Spread Chart
    initializeSpreadChart() {
        const ctx = document.getElementById('spreadChart');
        if (!ctx) return null;
        
        const config = {
            type: 'line',
            data: {
                datasets: [
                    {
                        label: 'Spread %',
                        data: [],
                        borderColor: this.chartColors.spread,
                        backgroundColor: 'rgba(248, 81, 73, 0.1)',
                        borderWidth: 2,
                        fill: true,
                        tension: 0.1,
                        pointRadius: 0,
                        pointHoverRadius: 4
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    intersect: false,
                    mode: 'index'
                },
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        callbacks: {
                            title: function(context) {
                                if (context[0].parsed.x) {
                                    return new Date(context[0].parsed.x).toLocaleString();
                                }
                                return '';
                            },
                            label: function(context) {
                                return `Spread: ${context.parsed.y.toFixed(4)}%`;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        type: 'time',
                        time: {
                            displayFormats: {
                                minute: 'HH:mm',
                                hour: 'HH:mm'
                            }
                        },
                        title: {
                            display: false
                        },
                        grid: {
                            display: true,
                            color: this.chartColors.grid
                        }
                    },
                    y: {
                        title: {
                            display: true,
                            text: 'Spread (%)',
                            font: {
                                size: 12
                            }
                        },
                        grid: {
                            display: true,
                            color: this.chartColors.grid
                        },
                        min: 0,
                        ticks: {
                            callback: function(value) {
                                return value.toFixed(3) + '%';
                            }
                        }
                    }
                },
                animation: {
                    duration: 0
                }
            }
        };
        
        this.charts.spreadChart = new Chart(ctx, config);
        this.loadSpreadHistory();
        
        return this.charts.spreadChart;
    }
    
    async loadSpreadHistory(hours = 6) {
        if (!this.charts.spreadChart) return;
        
        try {
            const response = await fetch(`/api/chart/price-history?hours=${hours}`);
            if (!response.ok) throw new Error('Failed to fetch spread history');
            
            const data = await response.json();
            const spreads = this.calculateSpreadFromPriceData(data);
            
            this.charts.spreadChart.data.datasets[0].data = spreads;
            this.charts.spreadChart.update('none');
            
        } catch (error) {
            console.error('Error loading spread history:', error);
        }
    }
    
    // Update methods for real-time data
    updatePriceChart(priceData) {
        if (!this.charts.priceChart || !priceData) return;
        
        const now = new Date();
        const datasets = this.charts.priceChart.data.datasets;
        
        // Add new USDT price point
        if (priceData['XRP/USDT']) {
            datasets[0].data.push({
                x: now,
                y: priceData['XRP/USDT'].price
            });
        }
        
        // Add new USDC price point
        if (priceData['XRP/USDC']) {
            datasets[1].data.push({
                x: now,
                y: priceData['XRP/USDC'].price
            });
        }
        
        // Add new spread point
        if (priceData.spread_percentage) {
            datasets[2].data.push({
                x: now,
                y: priceData.spread_percentage
            });
        }
        
        // Keep only last 100 points for performance
        datasets.forEach(dataset => {
            if (dataset.data.length > 100) {
                dataset.data = dataset.data.slice(-100);
            }
        });
        
        this.charts.priceChart.update('none');
    }
    
    // Utility methods
    destroyChart(chartName) {
        if (this.charts[chartName]) {
            this.charts[chartName].destroy();
            delete this.charts[chartName];
        }
    }
    
    destroyAllCharts() {
        Object.keys(this.charts).forEach(chartName => {
            this.destroyChart(chartName);
        });
    }
    
    // Chart animation helpers
    animateValue(element, startValue, endValue, duration = 1000) {
        const start = Date.now();
        const range = endValue - startValue;
        
        const update = () => {
            const elapsed = Date.now() - start;
            const progress = Math.min(elapsed / duration, 1);
            
            // Easing function (ease-out cubic)
            const easedProgress = 1 - Math.pow(1 - progress, 3);
            const currentValue = startValue + (range * easedProgress);
            
            element.textContent = currentValue.toFixed(2);
            
            if (progress < 1) {
                requestAnimationFrame(update);
            }
        };
        
        requestAnimationFrame(update);
    }
    
    // Chart color helpers
    getColorForValue(value, positiveColor = this.chartColors.success, negativeColor = this.chartColors.danger) {
        if (value > 0) return positiveColor;
        if (value < 0) return negativeColor;
        return this.chartColors.textMuted;
    }
    
    // Chart data helpers
    formatTimestamp(timestamp) {
        return new Date(timestamp).toLocaleString();
    }
    
    formatCurrency(value) {
        return '$' + value.toFixed(2);
    }
    
    formatPercentage(value) {
        return value.toFixed(2) + '%';
    }
}

// Initialize global charts instance
window.tradingCharts = new TradingCharts();

// Global functions for template usage
window.initializePriceChart = () => {
    return window.tradingCharts.initializePriceChart();
};

window.initializePnlChart = () => {
    return window.tradingCharts.initializePnlChart();
};

window.initializeDistributionChart = () => {
    return window.tradingCharts.initializeDistributionChart();
};

window.initializeSpreadChart = () => {
    return window.tradingCharts.initializeSpreadChart();
};

window.updatePriceChart = (data) => {
    window.tradingCharts.updatePriceChart(data);
};

// Chart update functions for monitor
window.updatePnlChart = (timeframe) => {
    if (window.tradingCharts.charts.pnlChart) {
        window.tradingCharts.loadPnlHistory(timeframe);
    }
};

window.updateDistributionChart = () => {
    if (window.tradingCharts.charts.distributionChart) {
        window.tradingCharts.loadDistributionData();
    }
};

window.updateSpreadChart = (timeframe) => {
    if (window.tradingCharts.charts.spreadChart) {
        const hours = timeframe === '1h' ? 1 : timeframe === '6h' ? 6 : timeframe === '24h' ? 24 : 6;
        window.tradingCharts.loadSpreadHistory(hours);
    }
};

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    if (window.tradingCharts) {
        window.tradingCharts.destroyAllCharts();
    }
});

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = TradingCharts;
}
