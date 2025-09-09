import logging
from datetime import datetime, timedelta
from app import db
from models import SystemLog, Trade

class DataLogger:
    """Transaction logging and history management"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Configure file logging
        file_handler = logging.FileHandler('trading_system.log')
        file_handler.setLevel(logging.INFO)
        
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        
        self.logger.addHandler(file_handler)
    
    def log_trade(self, trade_data, trade_type='info'):
        """Log trade information"""
        try:
            message = f"Trade {trade_type}: {trade_data}"
            self.logger.info(message)
            
            # Store in database
            log_entry = SystemLog(
                level='INFO',
                message=message,
                module='TradeLogger'
            )
            db.session.add(log_entry)
            db.session.commit()
            
        except Exception as e:
            self.logger.error(f"Error logging trade: {e}")
    
    def log_arbitrage_opportunity(self, opportunity):
        """Log arbitrage opportunity"""
        try:
            message = (f"Arbitrage opportunity detected - "
                      f"Spread: {opportunity.get('spread_percentage', 0):.4f}%, "
                      f"USDT: {opportunity.get('usdt_price', 0):.4f}, "
                      f"USDC: {opportunity.get('usdc_price', 0):.4f}")
            
            self.logger.info(message)
            
            log_entry = SystemLog(
                level='INFO',
                message=message,
                module='ArbitrageEngine'
            )
            db.session.add(log_entry)
            db.session.commit()
            
        except Exception as e:
            self.logger.error(f"Error logging arbitrage opportunity: {e}")
    
    def log_balance_change(self, currency, old_balance, new_balance, reason):
        """Log balance changes"""
        try:
            change = new_balance - old_balance
            message = (f"Balance change - {currency}: "
                      f"{old_balance:.4f} -> {new_balance:.4f} "
                      f"(Δ{change:+.4f}) - Reason: {reason}")
            
            self.logger.info(message)
            
            log_entry = SystemLog(
                level='INFO',
                message=message,
                module='BalanceManager'
            )
            db.session.add(log_entry)
            db.session.commit()
            
        except Exception as e:
            self.logger.error(f"Error logging balance change: {e}")
    
    def log_risk_event(self, risk_type, details, severity='WARNING'):
        """Log risk management events"""
        try:
            message = f"Risk Event ({risk_type}): {details}"
            
            if severity == 'ERROR':
                self.logger.error(message)
            elif severity == 'WARNING':
                self.logger.warning(message)
            else:
                self.logger.info(message)
            
            log_entry = SystemLog(
                level=severity,
                message=message,
                module='RiskController'
            )
            db.session.add(log_entry)
            db.session.commit()
            
        except Exception as e:
            self.logger.error(f"Error logging risk event: {e}")
    
    def log_system_event(self, event_type, details, module='System'):
        """Log general system events"""
        try:
            message = f"{event_type}: {details}"
            self.logger.info(message)
            
            log_entry = SystemLog(
                level='INFO',
                message=message,
                module=module
            )
            db.session.add(log_entry)
            db.session.commit()
            
        except Exception as e:
            self.logger.error(f"Error logging system event: {e}")
    
    def log_error(self, error_message, module='Unknown', exception=None):
        """Log errors with optional exception details"""
        try:
            if exception:
                message = f"Error in {module}: {error_message} - Exception: {str(exception)}"
            else:
                message = f"Error in {module}: {error_message}"
            
            self.logger.error(message)
            
            log_entry = SystemLog(
                level='ERROR',
                message=message,
                module=module
            )
            db.session.add(log_entry)
            db.session.commit()
            
        except Exception as e:
            self.logger.error(f"Error logging error: {e}")
    
    def get_recent_logs(self, limit=100, level=None):
        """Get recent system logs"""
        try:
            query = SystemLog.query
            
            if level:
                query = query.filter_by(level=level)
            
            logs = query.order_by(SystemLog.timestamp.desc()).limit(limit).all()
            
            return [{
                'id': log.id,
                'timestamp': log.timestamp.isoformat(),
                'level': log.level,
                'message': log.message,
                'module': log.module
            } for log in logs]
            
        except Exception as e:
            self.logger.error(f"Error getting recent logs: {e}")
            return []
    
    def get_trade_history(self, days=7, status=None):
        """Get trade history"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            query = Trade.query.filter(Trade.created_at >= cutoff_date)
            
            if status:
                query = query.filter_by(status=status)
            
            trades = query.order_by(Trade.created_at.desc()).all()
            
            return [{
                'id': trade.id,
                'type': trade.trade_type,
                'pair': trade.pair,
                'amount': trade.amount,
                'price': trade.price,
                'total_value': trade.total_value,
                'profit_loss': trade.profit_loss,
                'status': trade.status,
                'created_at': trade.created_at.isoformat(),
                'completed_at': trade.completed_at.isoformat() if trade.completed_at else None
            } for trade in trades]
            
        except Exception as e:
            self.logger.error(f"Error getting trade history: {e}")
            return []
    
    def cleanup_old_logs(self, days_to_keep=30):
        """Clean up old log entries"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
            
            # Delete old system logs
            old_logs = SystemLog.query.filter(SystemLog.timestamp < cutoff_date)
            deleted_count = old_logs.count()
            old_logs.delete()
            
            db.session.commit()
            
            self.logger.info(f"Cleaned up {deleted_count} old log entries")
            return deleted_count
            
        except Exception as e:
            self.logger.error(f"Error cleaning up old logs: {e}")
            db.session.rollback()
            return 0
    
    def export_trade_history(self, start_date=None, end_date=None):
        """Export trade history for analysis"""
        try:
            query = Trade.query
            
            if start_date:
                query = query.filter(Trade.created_at >= start_date)
            if end_date:
                query = query.filter(Trade.created_at <= end_date)
            
            trades = query.order_by(Trade.created_at).all()
            
            # Prepare data for export
            export_data = []
            for trade in trades:
                export_data.append({
                    'timestamp': trade.created_at.isoformat(),
                    'type': trade.trade_type,
                    'pair': trade.pair,
                    'amount': trade.amount,
                    'price': trade.price,
                    'total_value': trade.total_value,
                    'profit_loss': trade.profit_loss or 0,
                    'status': trade.status,
                    'order_id': trade.order_id
                })
            
            return export_data
            
        except Exception as e:
            self.logger.error(f"Error exporting trade history: {e}")
            return []
