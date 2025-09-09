from app import db
from datetime import datetime
from sqlalchemy import func

class TradingConfig(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    # Basic trading parameters
    spread_threshold = db.Column(db.Float, default=0.003)
    trade_amount = db.Column(db.Float, default=100.0)
    daily_max_volume = db.Column(db.Float, default=5000.0)
    risk_buffer = db.Column(db.Float, default=0.1)
    max_pending_orders = db.Column(db.Integer, default=3)
    
    # Enhanced risk management
    max_daily_loss = db.Column(db.Float, default=100.0)  # Max daily loss limit
    volatility_multiplier = db.Column(db.Float, default=1.0)  # Position size adjustment for volatility
    circuit_breaker_enabled = db.Column(db.Boolean, default=True)
    api_rate_limit = db.Column(db.Integer, default=10)  # API calls per minute
    slippage_tolerance = db.Column(db.Float, default=0.001)  # 0.1% slippage tolerance
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'spread_threshold': self.spread_threshold,
            'trade_amount': self.trade_amount,
            'daily_max_volume': self.daily_max_volume,
            'risk_buffer': self.risk_buffer,
            'max_pending_orders': self.max_pending_orders,
            'max_daily_loss': self.max_daily_loss,
            'volatility_multiplier': self.volatility_multiplier,
            'circuit_breaker_enabled': self.circuit_breaker_enabled,
            'api_rate_limit': self.api_rate_limit,
            'slippage_tolerance': self.slippage_tolerance,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class Trade(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    trade_type = db.Column(db.String(20), nullable=False)  # 'buy' or 'sell'
    pair = db.Column(db.String(20), nullable=False)  # 'XRP/USDT' or 'XRP/USDC'
    amount = db.Column(db.Float, nullable=False)
    price = db.Column(db.Float, nullable=False)
    total_value = db.Column(db.Float, nullable=False)
    spread = db.Column(db.Float)
    profit_loss = db.Column(db.Float)
    status = db.Column(db.String(20), default='pending')  # 'pending', 'completed', 'failed'
    order_id = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)

class Balance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    currency = db.Column(db.String(10), nullable=False)  # 'XRP', 'USDT', 'USDC'
    amount = db.Column(db.Float, nullable=False, default=0.0)
    locked = db.Column(db.Float, nullable=False, default=0.0)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class PriceHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    pair = db.Column(db.String(20), nullable=False)
    price = db.Column(db.Float, nullable=False)
    volume = db.Column(db.Float)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class ArbitrageOpportunity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usdt_price = db.Column(db.Float, nullable=False)
    usdc_price = db.Column(db.Float, nullable=False)
    spread = db.Column(db.Float, nullable=False)
    spread_percentage = db.Column(db.Float, nullable=False)
    opportunity_type = db.Column(db.String(20))  # 'buy_usdt_sell_usdc' or 'buy_usdc_sell_usdt'
    executed = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class SystemLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    level = db.Column(db.String(20), nullable=False)  # 'INFO', 'WARNING', 'ERROR'
    message = db.Column(db.Text, nullable=False)
    module = db.Column(db.String(50))
    error_details = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'level': self.level,
            'message': self.message,
            'module': self.module,
            'error_details': self.error_details,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None
        }

class DailyVolume(db.Model):
    """Daily trading volume tracking"""
    id = db.Column(db.Integer, primary_key=True)
    trade_date = db.Column(db.Date, nullable=False, default=lambda: datetime.utcnow().date())
    total_volume_usd = db.Column(db.Float, default=0.0)
    trade_count = db.Column(db.Integer, default=0)
    profit_loss = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Ensure one record per date
    __table_args__ = (db.UniqueConstraint('trade_date'),)
    
    def to_dict(self):
        return {
            'id': self.id,
            'trade_date': self.trade_date.isoformat() if self.trade_date else None,
            'total_volume_usd': self.total_volume_usd,
            'trade_count': self.trade_count,
            'profit_loss': self.profit_loss,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class CircuitBreaker(db.Model):
    """Circuit breaker status tracking"""
    id = db.Column(db.Integer, primary_key=True)
    breaker_type = db.Column(db.String(50), nullable=False)  # 'daily_loss', 'system_error', 'api_error'
    is_active = db.Column(db.Boolean, default=False)
    trigger_reason = db.Column(db.Text)
    trigger_value = db.Column(db.Float)
    threshold_value = db.Column(db.Float)
    activated_at = db.Column(db.DateTime)
    reset_at = db.Column(db.DateTime)
    auto_reset = db.Column(db.Boolean, default=True)
    reset_after_minutes = db.Column(db.Integer, default=60)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'breaker_type': self.breaker_type,
            'is_active': self.is_active,
            'trigger_reason': self.trigger_reason,
            'trigger_value': self.trigger_value,
            'threshold_value': self.threshold_value,
            'activated_at': self.activated_at.isoformat() if self.activated_at else None,
            'reset_at': self.reset_at.isoformat() if self.reset_at else None,
            'auto_reset': self.auto_reset,
            'reset_after_minutes': self.reset_after_minutes
        }
