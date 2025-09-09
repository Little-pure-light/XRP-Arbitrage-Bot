import logging
from datetime import datetime, timedelta
from app import db
from models import DailyVolume, Trade, CircuitBreaker, TradingConfig

class VolumeTracker:
    """Daily volume tracking and circuit breaker management"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def track_trade_volume(self, trade_amount_usd, profit_loss=0):
        """Track daily trading volume and profit/loss"""
        try:
            today = datetime.utcnow().date()
            
            # Get or create today's volume record
            daily_volume = DailyVolume.query.filter_by(trade_date=today).first()
            
            if not daily_volume:
                daily_volume = DailyVolume(
                    trade_date=today,
                    total_volume_usd=0.0,
                    trade_count=0,
                    profit_loss=0.0
                )
                db.session.add(daily_volume)
            
            # Update volume and P&L
            daily_volume.total_volume_usd += trade_amount_usd
            daily_volume.trade_count += 1
            daily_volume.profit_loss += profit_loss
            daily_volume.updated_at = datetime.utcnow()
            
            db.session.commit()
            
            self.logger.info(f"Volume tracked: ${trade_amount_usd:.2f}, Today's total: ${daily_volume.total_volume_usd:.2f}")
            
            # Check circuit breakers after updating volume
            self._check_daily_loss_circuit_breaker(daily_volume)
            
            return daily_volume
            
        except Exception as e:
            self.logger.error(f"Error tracking volume: {e}")
            db.session.rollback()
            return None
    
    def get_daily_volume(self, date=None):
        """Get daily volume for specific date (today if None)"""
        try:
            if date is None:
                date = datetime.utcnow().date()
            
            daily_volume = DailyVolume.query.filter_by(trade_date=date).first()
            
            if not daily_volume:
                # Return empty record for the date
                return {
                    'trade_date': date.isoformat(),
                    'total_volume_usd': 0.0,
                    'trade_count': 0,
                    'profit_loss': 0.0
                }
            
            return daily_volume.to_dict()
            
        except Exception as e:
            self.logger.error(f"Error getting daily volume: {e}")
            return None
    
    def check_daily_volume_limit(self, proposed_trade_amount_usd, config):
        """Check if proposed trade would exceed daily volume limit"""
        try:
            today_volume = self.get_daily_volume()
            current_volume = today_volume['total_volume_usd']
            
            if current_volume + proposed_trade_amount_usd > config.daily_max_volume:
                return {
                    'allowed': False,
                    'reason': f'Would exceed daily limit: ${current_volume + proposed_trade_amount_usd:.2f} > ${config.daily_max_volume:.2f}',
                    'current_volume': current_volume,
                    'remaining_volume': config.daily_max_volume - current_volume
                }
            
            return {
                'allowed': True,
                'current_volume': current_volume,
                'remaining_volume': config.daily_max_volume - current_volume
            }
            
        except Exception as e:
            self.logger.error(f"Error checking daily volume limit: {e}")
            return {'allowed': False, 'reason': 'Volume check failed'}
    
    def _check_daily_loss_circuit_breaker(self, daily_volume):
        """Check and activate daily loss circuit breaker if needed"""
        try:
            config = TradingConfig.query.first()
            if not config or not config.circuit_breaker_enabled:
                return
            
            # Check if daily loss exceeds threshold
            if daily_volume.profit_loss < -config.max_daily_loss:
                self.activate_circuit_breaker(
                    'daily_loss',
                    f'Daily loss threshold exceeded: ${abs(daily_volume.profit_loss):.2f} > ${config.max_daily_loss:.2f}',
                    abs(daily_volume.profit_loss),
                    config.max_daily_loss
                )
            
        except Exception as e:
            self.logger.error(f"Error checking daily loss circuit breaker: {e}")
    
    def activate_circuit_breaker(self, breaker_type, reason, trigger_value=None, threshold_value=None):
        """Activate a circuit breaker"""
        try:
            # Check if breaker is already active
            existing_breaker = CircuitBreaker.query.filter_by(
                breaker_type=breaker_type,
                is_active=True
            ).first()
            
            if existing_breaker:
                self.logger.warning(f"Circuit breaker {breaker_type} already active")
                return existing_breaker
            
            # Create new circuit breaker
            breaker = CircuitBreaker(
                breaker_type=breaker_type,
                is_active=True,
                trigger_reason=reason,
                trigger_value=trigger_value,
                threshold_value=threshold_value,
                activated_at=datetime.utcnow(),
                auto_reset=True,
                reset_after_minutes=60  # Auto-reset after 1 hour
            )
            
            db.session.add(breaker)
            db.session.commit()
            
            self.logger.critical(f"CIRCUIT BREAKER ACTIVATED: {breaker_type} - {reason}")
            
            return breaker
            
        except Exception as e:
            self.logger.error(f"Error activating circuit breaker: {e}")
            db.session.rollback()
            return None
    
    def check_circuit_breakers(self):
        """Check all active circuit breakers and auto-reset if needed"""
        try:
            active_breakers = CircuitBreaker.query.filter_by(is_active=True).all()
            
            current_time = datetime.utcnow()
            results = []
            
            for breaker in active_breakers:
                if breaker.auto_reset and breaker.activated_at:
                    reset_time = breaker.activated_at + timedelta(minutes=breaker.reset_after_minutes)
                    
                    if current_time >= reset_time:
                        # Auto-reset the breaker
                        breaker.is_active = False
                        breaker.reset_at = current_time
                        
                        self.logger.info(f"Circuit breaker auto-reset: {breaker.breaker_type}")
                
                results.append({
                    'type': breaker.breaker_type,
                    'active': breaker.is_active,
                    'reason': breaker.trigger_reason,
                    'activated_at': breaker.activated_at.isoformat() if breaker.activated_at else None,
                    'reset_at': breaker.reset_at.isoformat() if breaker.reset_at else None
                })
            
            db.session.commit()
            
            # Return status
            has_active = any(b['active'] for b in results)
            
            return {
                'has_active_breakers': has_active,
                'breakers': results,
                'trading_allowed': not has_active
            }
            
        except Exception as e:
            self.logger.error(f"Error checking circuit breakers: {e}")
            return {
                'has_active_breakers': False,
                'breakers': [],
                'trading_allowed': True
            }
    
    def manual_reset_circuit_breaker(self, breaker_type):
        """Manually reset a circuit breaker"""
        try:
            breaker = CircuitBreaker.query.filter_by(
                breaker_type=breaker_type,
                is_active=True
            ).first()
            
            if not breaker:
                return {'success': False, 'message': f'No active {breaker_type} circuit breaker found'}
            
            breaker.is_active = False
            breaker.reset_at = datetime.utcnow()
            
            db.session.commit()
            
            self.logger.info(f"Circuit breaker manually reset: {breaker_type}")
            
            return {'success': True, 'message': f'{breaker_type} circuit breaker reset'}
            
        except Exception as e:
            self.logger.error(f"Error resetting circuit breaker: {e}")
            db.session.rollback()
            return {'success': False, 'message': f'Error resetting breaker: {e}'}
    
    def get_volume_statistics(self, days=7):
        """Get volume statistics for the last N days"""
        try:
            end_date = datetime.utcnow().date()
            start_date = end_date - timedelta(days=days-1)
            
            volumes = DailyVolume.query.filter(
                DailyVolume.trade_date >= start_date,
                DailyVolume.trade_date <= end_date
            ).order_by(DailyVolume.trade_date.desc()).all()
            
            total_volume = sum(v.total_volume_usd for v in volumes)
            total_trades = sum(v.trade_count for v in volumes)
            total_profit = sum(v.profit_loss for v in volumes)
            
            return {
                'period_days': days,
                'total_volume_usd': total_volume,
                'total_trades': total_trades,
                'total_profit_loss': total_profit,
                'average_daily_volume': total_volume / days if days > 0 else 0,
                'average_daily_trades': total_trades / days if days > 0 else 0,
                'daily_records': [v.to_dict() for v in volumes]
            }
            
        except Exception as e:
            self.logger.error(f"Error getting volume statistics: {e}")
            return None