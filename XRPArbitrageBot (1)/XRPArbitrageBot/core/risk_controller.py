import logging
from datetime import datetime, timedelta
from app import db
from models import Trade, TradingConfig, Balance, CircuitBreaker
from core.balance_manager import BalanceManager
from core.volume_tracker import VolumeTracker

class RiskController:
    """Enhanced risk management with circuit breakers and volatility-based sizing"""
    
    def __init__(self):
        self.balance_manager = BalanceManager()
        self.volume_tracker = VolumeTracker()
        self.logger = logging.getLogger(__name__)
    
    def check_trade_risk(self, opportunity, config):
        """
        Enhanced comprehensive risk check with circuit breakers
        
        Args:
            opportunity: Trade opportunity details
            config: Trading configuration
            
        Returns:
            dict: {'safe': bool, 'reason': str, 'adjusted_amount': float}
        """
        try:
            # 0. Check circuit breakers first
            breaker_status = self.volume_tracker.check_circuit_breakers()
            if not breaker_status['trading_allowed']:
                active_breakers = [b['type'] for b in breaker_status['breakers'] if b['active']]
                return {
                    'safe': False, 
                    'reason': f'Circuit breaker(s) active: {active_breakers}',
                    'adjusted_amount': 0
                }
            
            # 1. Calculate volatility-adjusted trade amount
            adjusted_amount = self._calculate_volatility_adjusted_amount(opportunity, config)
            opportunity['amount'] = adjusted_amount  # Update opportunity with adjusted amount
            
            # 2. Check daily volume limits with adjusted amount
            trade_value_usd = adjusted_amount * opportunity['sell_price']
            volume_check = self.volume_tracker.check_daily_volume_limit(trade_value_usd, config)
            if not volume_check['allowed']:
                return {
                    'safe': False, 
                    'reason': volume_check['reason'],
                    'adjusted_amount': 0
                }
            
            # 3. Check balance safety margins
            balance_check = self._check_balance_safety(adjusted_amount, config.risk_buffer)
            if not balance_check['safe']:
                return {
                    'safe': False,
                    'reason': balance_check['reason'],
                    'adjusted_amount': 0
                }
            
            # 4. Check pending orders limit
            pending_check = self._check_pending_orders_limit(config.max_pending_orders)
            if not pending_check['safe']:
                return {
                    'safe': False,
                    'reason': pending_check['reason'],
                    'adjusted_amount': 0
                }
            
            # 5. Check price volatility
            volatility_check = self._check_price_volatility(opportunity)
            if not volatility_check['safe']:
                return {
                    'safe': False,
                    'reason': volatility_check['reason'],
                    'adjusted_amount': 0
                }
            
            # 6. Check spread validity
            spread_check = self._check_spread_validity(opportunity, config.spread_threshold)
            if not spread_check['safe']:
                return {
                    'safe': False,
                    'reason': spread_check['reason'],
                    'adjusted_amount': 0
                }
            
            # 7. Check trading frequency
            frequency_check = self._check_trading_frequency()
            if not frequency_check['safe']:
                return {
                    'safe': False,
                    'reason': frequency_check['reason'],
                    'adjusted_amount': 0
                }
            
            return {
                'safe': True, 
                'reason': 'All risk checks passed',
                'adjusted_amount': adjusted_amount
            }
            
        except Exception as e:
            self.logger.error(f"Error in risk check: {e}")
            return {
                'safe': False, 
                'reason': f'Risk check error: {e}',
                'adjusted_amount': 0
            }
    
    def _check_daily_volume_limit(self, trade_amount, daily_limit):
        """Check if trade would exceed daily volume limit"""
        try:
            today = datetime.utcnow().date()
            today_start = datetime.combine(today, datetime.min.time())
            
            # Calculate today's total volume
            today_trades = Trade.query.filter(
                Trade.created_at >= today_start,
                Trade.status.in_(['completed', 'pending'])
            ).all()
            
            today_volume = sum(trade.amount for trade in today_trades)
            
            if today_volume + trade_amount > daily_limit:
                return {
                    'safe': False, 
                    'reason': f'Daily volume limit exceeded: {today_volume + trade_amount:.2f} > {daily_limit}'
                }
            
            return {'safe': True, 'reason': 'Volume limit OK'}
            
        except Exception as e:
            self.logger.error(f"Error checking daily volume: {e}")
            return {'safe': False, 'reason': 'Volume check failed'}
    
    def _check_balance_safety(self, trade_amount, risk_buffer):
        """Check if balances have sufficient safety margins"""
        try:
            balances = self.balance_manager.get_balances()
            
            # Check XRP balance (for sell order)
            xrp_balance = balances.get('XRP', {}).get('free', 0)
            required_xrp = trade_amount * (1 + risk_buffer)
            
            if xrp_balance < required_xrp:
                return {
                    'safe': False,
                    'reason': f'Insufficient XRP balance with safety margin: {xrp_balance:.2f} < {required_xrp:.2f}'
                }
            
            # Check stablecoin balances (for buy order)
            usdt_balance = balances.get('USDT', {}).get('free', 0)
            usdc_balance = balances.get('USDC', {}).get('free', 0)
            
            # Estimate required stablecoin (using approximate price)
            estimated_price = 0.52  # Conservative estimate
            required_stable = trade_amount * estimated_price * (1 + risk_buffer)
            
            if usdt_balance < required_stable and usdc_balance < required_stable:
                return {
                    'safe': False,
                    'reason': f'Insufficient stablecoin balance with safety margin'
                }
            
            return {'safe': True, 'reason': 'Balance safety OK'}
            
        except Exception as e:
            self.logger.error(f"Error checking balance safety: {e}")
            return {'safe': False, 'reason': 'Balance safety check failed'}
    
    def _check_pending_orders_limit(self, max_pending):
        """Check if pending orders limit would be exceeded"""
        try:
            pending_count = Trade.query.filter_by(status='pending').count()
            
            if pending_count >= max_pending:
                return {
                    'safe': False,
                    'reason': f'Too many pending orders: {pending_count} >= {max_pending}'
                }
            
            return {'safe': True, 'reason': 'Pending orders OK'}
            
        except Exception as e:
            self.logger.error(f"Error checking pending orders: {e}")
            return {'safe': False, 'reason': 'Pending orders check failed'}
    
    def _check_price_volatility(self, opportunity):
        """Check if price volatility is within acceptable limits"""
        try:
            # Get recent price movements
            recent_cutoff = datetime.utcnow() - timedelta(minutes=5)
            
            from models import PriceHistory
            recent_prices = PriceHistory.query.filter(
                PriceHistory.timestamp >= recent_cutoff
            ).order_by(PriceHistory.timestamp.desc()).limit(20).all()
            
            if len(recent_prices) < 5:
                return {'safe': True, 'reason': 'Insufficient price history for volatility check'}
            
            # Calculate price volatility
            prices = [p.price for p in recent_prices]
            max_price = max(prices)
            min_price = min(prices)
            volatility = (max_price - min_price) / min_price
            
            # If volatility > 2%, it's too risky
            if volatility > 0.02:
                return {
                    'safe': False,
                    'reason': f'High price volatility detected: {volatility:.4f}'
                }
            
            return {'safe': True, 'reason': 'Price volatility OK'}
            
        except Exception as e:
            self.logger.error(f"Error checking price volatility: {e}")
            return {'safe': True, 'reason': 'Volatility check skipped due to error'}
    
    def _check_spread_validity(self, opportunity, min_spread):
        """Check if spread is still valid and above threshold"""
        try:
            current_spread = opportunity.get('spread_percentage', 0)
            
            if current_spread < min_spread:
                return {
                    'safe': False,
                    'reason': f'Spread too small: {current_spread:.4f} < {min_spread:.4f}'
                }
            
            # Check if spread is not too good to be true (>5% is suspicious)
            if current_spread > 0.05:
                return {
                    'safe': False,
                    'reason': f'Spread too large, possible data error: {current_spread:.4f}'
                }
            
            return {'safe': True, 'reason': 'Spread validity OK'}
            
        except Exception as e:
            self.logger.error(f"Error checking spread validity: {e}")
            return {'safe': False, 'reason': 'Spread validity check failed'}
    
    def _check_trading_frequency(self, min_interval_seconds=30):
        """Check if we're not trading too frequently"""
        try:
            recent_cutoff = datetime.utcnow() - timedelta(seconds=min_interval_seconds)
            
            recent_trades = Trade.query.filter(
                Trade.created_at >= recent_cutoff
            ).count()
            
            # Allow max 1 trade per 30 seconds
            if recent_trades > 0:
                return {
                    'safe': False,
                    'reason': f'Trading too frequently: {recent_trades} trades in last {min_interval_seconds}s'
                }
            
            return {'safe': True, 'reason': 'Trading frequency OK'}
            
        except Exception as e:
            self.logger.error(f"Error checking trading frequency: {e}")
            return {'safe': True, 'reason': 'Frequency check skipped due to error'}
    
    def check_system_health(self):
        """Check overall system health"""
        try:
            health_status = {
                'healthy': True,
                'warnings': [],
                'errors': []
            }
            
            # Check database connectivity
            try:
                from sqlalchemy import text
                db.session.execute(text('SELECT 1'))
            except Exception as e:
                health_status['healthy'] = False
                health_status['errors'].append(f'Database connection error: {e}')
            
            # Check balance consistency
            balances = self.balance_manager.get_balances()
            for currency, balance in balances.items():
                if balance['total'] < 0:
                    health_status['warnings'].append(f'Negative {currency} balance detected')
                
                if balance['locked'] > balance['total']:
                    health_status['healthy'] = False
                    health_status['errors'].append(f'Locked {currency} exceeds total balance')
            
            # Check for stuck pending orders
            old_pending = Trade.query.filter(
                Trade.status == 'pending',
                Trade.created_at < datetime.utcnow() - timedelta(minutes=5)
            ).count()
            
            if old_pending > 0:
                health_status['warnings'].append(f'{old_pending} orders pending for >5 minutes')
            
            return health_status
            
        except Exception as e:
            self.logger.error(f"Error checking system health: {e}")
            return {
                'healthy': False,
                'warnings': [],
                'errors': [f'Health check failed: {e}']
            }
    
    def calculate_max_safe_trade_amount(self, config):
        """Calculate maximum safe trade amount based on current conditions"""
        try:
            balances = self.balance_manager.get_balances()
            
            # Base on XRP balance with safety margin
            xrp_balance = balances.get('XRP', {}).get('free', 0)
            max_xrp = xrp_balance * (1 - config.risk_buffer)
            
            # Base on daily volume limit
            today = datetime.utcnow().date()
            today_start = datetime.combine(today, datetime.min.time())
            
            today_trades = Trade.query.filter(
                Trade.created_at >= today_start,
                Trade.status.in_(['completed', 'pending'])
            ).all()
            
            today_volume = sum(trade.amount for trade in today_trades)
            remaining_daily_volume = config.daily_max_volume - today_volume
            
            # Return the minimum of the constraints
            max_safe_amount = min(max_xrp, remaining_daily_volume, config.trade_amount)
            
            return max(0, max_safe_amount)
            
        except Exception as e:
            self.logger.error(f"Error calculating max safe trade amount: {e}")
            return 0
    
    def _calculate_volatility_adjusted_amount(self, opportunity, config):
        """Calculate position size adjusted for market volatility"""
        try:
            base_amount = config.trade_amount
            
            # Get recent price volatility
            volatility_factor = self._calculate_price_volatility_factor()
            
            # Apply volatility multiplier from config
            volatility_adjustment = config.volatility_multiplier * volatility_factor
            
            # Reduce position size for high volatility, increase for low volatility
            if volatility_factor > 1.5:  # High volatility
                adjusted_amount = base_amount * 0.5  # Reduce by 50%
            elif volatility_factor > 1.2:  # Medium-high volatility
                adjusted_amount = base_amount * 0.75  # Reduce by 25%
            elif volatility_factor < 0.5:  # Low volatility
                adjusted_amount = base_amount * 1.25  # Increase by 25%
            else:  # Normal volatility
                adjusted_amount = base_amount
            
            # Apply spread-based adjustment (larger spreads allow larger positions)
            spread_percentage = opportunity.get('spread_percentage', 0)
            if spread_percentage > 0.5:  # Large spread > 0.5%
                spread_multiplier = min(1.5, 1 + (spread_percentage / 100))
                adjusted_amount *= spread_multiplier
            
            # Ensure we don't exceed maximum safe amount
            max_safe = self.calculate_max_safe_trade_amount(config)
            final_amount = min(adjusted_amount, max_safe)
            
            self.logger.debug(f"Position sizing: Base={base_amount}, Volatility Factor={volatility_factor:.2f}, Final={final_amount:.2f}")
            
            return max(0, final_amount)
            
        except Exception as e:
            self.logger.error(f"Error calculating volatility-adjusted amount: {e}")
            return config.trade_amount
    
    def _calculate_price_volatility_factor(self):
        """Calculate price volatility factor over recent periods"""
        try:
            # Get price data from the last 30 minutes
            recent_cutoff = datetime.utcnow() - timedelta(minutes=30)
            
            from models import PriceHistory
            recent_prices = PriceHistory.query.filter(
                PriceHistory.timestamp >= recent_cutoff
            ).order_by(PriceHistory.timestamp.desc()).limit(60).all()
            
            if len(recent_prices) < 10:
                return 1.0  # Normal volatility if insufficient data
            
            # Separate by pair and calculate volatility
            usdt_prices = [p.price for p in recent_prices if p.pair == 'XRP/USDT']
            usdc_prices = [p.price for p in recent_prices if p.pair == 'XRP/USDC']
            
            volatility_factors = []
            
            for prices in [usdt_prices, usdc_prices]:
                if len(prices) >= 5:
                    max_price = max(prices)
                    min_price = min(prices)
                    avg_price = sum(prices) / len(prices)
                    
                    # Calculate coefficient of variation (volatility relative to mean)
                    volatility = (max_price - min_price) / avg_price
                    volatility_factors.append(volatility)
            
            if not volatility_factors:
                return 1.0
            
            # Average volatility across pairs
            avg_volatility = sum(volatility_factors) / len(volatility_factors)
            
            # Convert to volatility factor (higher values = more volatile)
            # Normal volatility is around 0.01-0.02 (1-2%)
            volatility_factor = avg_volatility / 0.015  # Normalize to ~1.0 for normal volatility
            
            return max(0.5, min(3.0, volatility_factor))  # Clamp between 0.5x and 3.0x
            
        except Exception as e:
            self.logger.error(f"Error calculating price volatility factor: {e}")
            return 1.0  # Default to normal volatility
    
    def activate_emergency_stop(self, reason):
        """Activate emergency stop circuit breaker"""
        try:
            self.volume_tracker.activate_circuit_breaker(
                'emergency_stop',
                f'Emergency stop activated: {reason}',
                None,
                None
            )
            
            # Cancel all pending orders immediately
            from core.trade_executor import TradeExecutor
            executor = TradeExecutor()
            executor.cancel_pending_orders()
            
            self.logger.critical(f"EMERGENCY STOP ACTIVATED: {reason}")
            
        except Exception as e:
            self.logger.error(f"Error activating emergency stop: {e}")
    
    def check_system_stability(self):
        """Check overall system stability for trading decisions"""
        try:
            stability_score = 100  # Start with perfect score
            warnings = []
            
            # Check recent error rate
            recent_cutoff = datetime.utcnow() - timedelta(minutes=15)
            from models import SystemLog
            recent_errors = SystemLog.query.filter(
                SystemLog.timestamp >= recent_cutoff,
                SystemLog.level == 'ERROR'
            ).count()
            
            if recent_errors > 5:
                stability_score -= 30
                warnings.append(f'High error rate: {recent_errors} errors in 15 minutes')
            elif recent_errors > 2:
                stability_score -= 10
                warnings.append(f'Elevated error rate: {recent_errors} errors in 15 minutes')
            
            # Check balance consistency
            balances = self.balance_manager.get_balances()
            for currency, balance in balances.items():
                if balance['locked'] > balance['total']:
                    stability_score -= 50
                    warnings.append(f'Balance inconsistency in {currency}')
            
            # Check trade success rate
            recent_trades = Trade.query.filter(
                Trade.created_at >= recent_cutoff
            ).all()
            
            if recent_trades:
                failed_trades = len([t for t in recent_trades if t.status in ['failed', 'timeout']])
                failure_rate = failed_trades / len(recent_trades)
                
                if failure_rate > 0.3:  # More than 30% failure rate
                    stability_score -= 40
                    warnings.append(f'High trade failure rate: {failure_rate:.1%}')
            
            return {
                'stability_score': max(0, stability_score),
                'stable': stability_score >= 70,
                'warnings': warnings,
                'recommendation': self._get_stability_recommendation(stability_score)
            }
            
        except Exception as e:
            self.logger.error(f"Error checking system stability: {e}")
            return {
                'stability_score': 50,
                'stable': False,
                'warnings': [f'Stability check failed: {e}'],
                'recommendation': 'Reduce trading activity until issues are resolved'
            }
    
    def _get_stability_recommendation(self, score):
        """Get trading recommendation based on stability score"""
        if score >= 90:
            return 'Normal trading activity'
        elif score >= 70:
            return 'Cautious trading with reduced position sizes'
        elif score >= 50:
            return 'Limited trading - address system issues'
        else:
            return 'Stop trading until stability is restored'
