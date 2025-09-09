from flask import render_template, jsonify, request, redirect, url_for, flash
from app import app, db
from models import TradingConfig, Trade, Balance, PriceHistory, ArbitrageOpportunity, SystemLog
from datetime import datetime, timedelta
from core.price_monitor import PriceMonitor
from core.balance_manager import BalanceManager
from core.trade_executor import TradeExecutor
from core.profit_analyzer import ProfitAnalyzer
from core.config_manager import ConfigManager
from business.arbitrage_engine import ArbitrageEngine
import json

# Initialize core modules (will be done lazily)
price_monitor = None
balance_manager = None
trade_executor = None
profit_analyzer = None
config_manager = None
arbitrage_engine = None

def get_core_modules():
    global price_monitor, balance_manager, trade_executor, profit_analyzer, config_manager, arbitrage_engine
    if price_monitor is None:
        from core.price_monitor import PriceMonitor
        from core.balance_manager import BalanceManager
        from core.trade_executor import TradeExecutor
        from core.profit_analyzer import ProfitAnalyzer
        from core.config_manager import ConfigManager
        from business.arbitrage_engine import ArbitrageEngine
        
        price_monitor = PriceMonitor()
        balance_manager = BalanceManager()
        trade_executor = TradeExecutor()
        profit_analyzer = ProfitAnalyzer()
        config_manager = ConfigManager()
        arbitrage_engine = ArbitrageEngine()
    
    return price_monitor, balance_manager, trade_executor, profit_analyzer, config_manager, arbitrage_engine

@app.route('/')
def dashboard():
    """Main trading dashboard"""
    modules = get_core_modules()
    config = modules[4].get_config()
    balances = modules[1].get_balances()
    today_stats = modules[3].get_today_stats()
    
    return render_template('dashboard.html', 
                         config=config, 
                         balances=balances, 
                         today_stats=today_stats)

@app.route('/monitor')
def monitor():
    """Trading monitor window"""
    recent_trades = Trade.query.order_by(Trade.created_at.desc()).limit(50).all()
    modules = get_core_modules()
    profit_stats = modules[3].get_comprehensive_stats()
    
    return render_template('monitor.html', 
                         recent_trades=recent_trades, 
                         profit_stats=profit_stats)

@app.route('/config', methods=['GET', 'POST'])
def config():
    """Configuration management"""
    modules = get_core_modules()
    config_manager = modules[4]
    if request.method == 'POST':
        config_manager.update_config({
            'spread_threshold': float(request.form.get('spread_threshold', 0.003)),
            'trade_amount': float(request.form.get('trade_amount', 100.0)),
            'daily_max_volume': float(request.form.get('daily_max_volume', 5000.0)),
            'risk_buffer': float(request.form.get('risk_buffer', 0.1)),
            'max_pending_orders': int(request.form.get('max_pending_orders', 3))
        })
        flash('Configuration updated successfully!', 'success')
        return redirect(url_for('config'))
    
    current_config = config_manager.get_config()
    return render_template('config.html', config=current_config)

@app.route('/api/prices')
def api_prices():
    """Get current XRP prices"""
    modules = get_core_modules()
    prices = modules[0].get_current_prices()
    return jsonify(prices)

@app.route('/api/balances')
def api_balances():
    """Get current balances"""
    modules = get_core_modules()
    balances = modules[1].get_balances()
    return jsonify(balances)

@app.route('/api/trades/recent')
def api_recent_trades():
    """Get recent trades"""
    limit = request.args.get('limit', 20, type=int)
    trades = Trade.query.order_by(Trade.created_at.desc()).limit(limit).all()
    
    trades_data = []
    for trade in trades:
        trades_data.append({
            'id': trade.id,
            'type': trade.trade_type,
            'pair': trade.pair,
            'amount': trade.amount,
            'price': trade.price,
            'total_value': trade.total_value,
            'profit_loss': trade.profit_loss,
            'status': trade.status,
            'created_at': trade.created_at.isoformat() if trade.created_at else None
        })
    
    return jsonify(trades_data)

@app.route('/api/profit/stats')
def api_profit_stats():
    """Get profit/loss statistics"""
    modules = get_core_modules()
    stats = modules[3].get_comprehensive_stats()
    return jsonify(stats)

@app.route('/api/chart/price-history')
def api_price_history():
    """Get price history for charts"""
    hours = request.args.get('hours', 24, type=int)
    since = datetime.utcnow() - timedelta(hours=hours)
    
    usdt_history = PriceHistory.query.filter(
        PriceHistory.pair == 'XRP/USDT',
        PriceHistory.timestamp >= since
    ).order_by(PriceHistory.timestamp).all()
    
    usdc_history = PriceHistory.query.filter(
        PriceHistory.pair == 'XRP/USDC',
        PriceHistory.timestamp >= since
    ).order_by(PriceHistory.timestamp).all()
    
    data = {
        'usdt': [{'time': p.timestamp.isoformat(), 'price': p.price} for p in usdt_history],
        'usdc': [{'time': p.timestamp.isoformat(), 'price': p.price} for p in usdc_history]
    }
    
    return jsonify(data)

@app.route('/api/chart/profit-trend')
def api_profit_trend():
    """Get profit trend for charts"""
    days = request.args.get('days', 7, type=int)
    since = datetime.utcnow() - timedelta(days=days)
    
    trades = Trade.query.filter(
        Trade.created_at >= since,
        Trade.status == 'completed',
        Trade.profit_loss.isnot(None)
    ).order_by(Trade.created_at).all()
    
    cumulative_profit = 0
    data = []
    
    for trade in trades:
        cumulative_profit += trade.profit_loss or 0
        data.append({
            'time': trade.created_at.isoformat(),
            'profit': trade.profit_loss,
            'cumulative': cumulative_profit
        })
    
    return jsonify(data)

@app.route('/api/start-trading', methods=['POST'])
def api_start_trading():
    """Start automated trading"""
    try:
        modules = get_core_modules()
        # Initialize balances if not exists
        modules[1].initialize_balances()
        
        # Start the arbitrage engine
        modules[5].start()
        
        # Log the action
        log = SystemLog(level='INFO', message='Trading started', module='API')
        db.session.add(log)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Trading started successfully'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/stop-trading', methods=['POST'])
def api_stop_trading():
    """Stop automated trading"""
    try:
        modules = get_core_modules()
        modules[5].stop()
        
        # Log the action
        log = SystemLog(level='INFO', message='Trading stopped', module='API')
        db.session.add(log)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Trading stopped successfully'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/opportunities')
def api_opportunities():
    """Get current arbitrage opportunities"""
    opportunities = ArbitrageOpportunity.query.filter(
        ArbitrageOpportunity.executed == False
    ).order_by(ArbitrageOpportunity.created_at.desc()).limit(10).all()
    
    data = []
    for opp in opportunities:
        data.append({
            'id': opp.id,
            'usdt_price': opp.usdt_price,
            'usdc_price': opp.usdc_price,
            'spread': opp.spread,
            'spread_percentage': opp.spread_percentage,
            'opportunity_type': opp.opportunity_type,
            'created_at': opp.created_at.isoformat()
        })
    
    return jsonify(data)

@app.route('/api/system-status')
def api_system_status():
    """Get system status"""
    modules = get_core_modules()
    status = {
        'trading_active': modules[5].is_running(),
        'api_connected': True,  # In simulation, always connected
        'last_price_update': modules[0].get_last_update(),
        'pending_orders': Trade.query.filter(Trade.status == 'pending').count(),
        'system_time': datetime.utcnow().isoformat()
    }
    
    return jsonify(status)
