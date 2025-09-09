import logging
from datetime import datetime, timedelta
from core.price_monitor import PriceMonitor
from core.profit_analyzer import ProfitAnalyzer

class TradingStrategy:
    """Advanced trading decision logic"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.price_monitor = PriceMonitor()
        self.profit_analyzer = ProfitAnalyzer()
    
    def should_trade(self, opportunity, config, market_conditions=None):
        """
        Advanced trading decision logic
        
        Args:
            opportunity: Detected arbitrage opportunity
            config: Trading configuration
            market_conditions: Current market analysis
            
        Returns:
            dict: {'trade': bool, 'confidence': float, 'reason': str}
        """
        try:
            decision_factors = []
            confidence_score = 0.0
            
            # Factor 1: Spread size (30% weight)
            spread_factor = self._analyze_spread_factor(opportunity, config)
            decision_factors.append(spread_factor)
            confidence_score += spread_factor['score'] * 0.3
            
            # Factor 2: Market volatility (25% weight)
            volatility_factor = self._analyze_volatility_factor()
            decision_factors.append(volatility_factor)
            confidence_score += volatility_factor['score'] * 0.25
            
            # Factor 3: Historical success rate (20% weight)
            success_factor = self._analyze_success_factor()
            decision_factors.append(success_factor)
            confidence_score += success_factor['score'] * 0.2
            
            # Factor 4: Market timing (15% weight)
            timing_factor = self._analyze_timing_factor()
            decision_factors.append(timing_factor)
            confidence_score += timing_factor['score'] * 0.15
            
            # Factor 5: Balance health (10% weight)
            balance_factor = self._analyze_balance_factor(opportunity['amount'])
            decision_factors.append(balance_factor)
            confidence_score += balance_factor['score'] * 0.1
            
            # Make trading decision
            should_trade = confidence_score >= 0.6  # 60% confidence threshold
            
            # Compile decision reasoning
            positive_factors = [f for f in decision_factors if f['score'] > 0.5]
            negative_factors = [f for f in decision_factors if f['score'] <= 0.5]
            
            reason_parts = []
            if positive_factors:
                reason_parts.append(f"Positive: {', '.join([f['name'] for f in positive_factors])}")
            if negative_factors:
                reason_parts.append(f"Negative: {', '.join([f['name'] for f in negative_factors])}")
            
            reason = "; ".join(reason_parts) if reason_parts else "Neutral market conditions"
            
            decision = {
                'trade': should_trade,
                'confidence': confidence_score,
                'reason': reason,
                'factors': decision_factors
            }
            
            self.logger.info(f"Trading decision: {should_trade} (confidence: {confidence_score:.2f}) - {reason}")
            
            return decision
            
        except Exception as e:
            self.logger.error(f"Error in trading decision: {e}")
            return {
                'trade': False,
                'confidence': 0.0,
                'reason': f"Decision error: {e}",
                'factors': []
            }
    
    def _analyze_spread_factor(self, opportunity, config):
        """Analyze spread attractiveness"""
        try:
            spread_pct = opportunity['spread_percentage']
            threshold_pct = config.spread_threshold * 100
            
            # Score based on how much the spread exceeds the threshold
            if spread_pct >= threshold_pct * 3:  # 3x threshold
                score = 1.0
                assessment = "Excellent spread"
            elif spread_pct >= threshold_pct * 2:  # 2x threshold
                score = 0.8
                assessment = "Good spread"
            elif spread_pct >= threshold_pct * 1.5:  # 1.5x threshold
                score = 0.6
                assessment = "Adequate spread"
            elif spread_pct >= threshold_pct:  # Above threshold
                score = 0.4
                assessment = "Minimal spread"
            else:
                score = 0.0
                assessment = "Spread too small"
            
            return {
                'name': 'Spread Size',
                'score': score,
                'assessment': assessment,
                'details': f"{spread_pct:.4f}% vs {threshold_pct:.4f}% threshold"
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing spread factor: {e}")
            return {'name': 'Spread Size', 'score': 0.5, 'assessment': 'Analysis failed'}
    
    def _analyze_volatility_factor(self):
        """Analyze market volatility"""
        try:
            prices = self.price_monitor.get_current_prices()
            
            # Get recent price history for volatility calculation
            from models import PriceHistory
            recent_cutoff = datetime.utcnow() - timedelta(minutes=15)
            
            recent_prices = PriceHistory.query.filter(
                PriceHistory.timestamp >= recent_cutoff,
                PriceHistory.pair == 'XRP/USDT'
            ).order_by(PriceHistory.timestamp).all()
            
            if len(recent_prices) < 5:
                return {
                    'name': 'Market Volatility',
                    'score': 0.5,
                    'assessment': 'Insufficient data',
                    'details': 'Not enough price history'
                }
            
            price_values = [p.price for p in recent_prices]
            avg_price = sum(price_values) / len(price_values)
            
            # Calculate volatility as standard deviation
            variance = sum((p - avg_price) ** 2 for p in price_values) / len(price_values)
            volatility = (variance ** 0.5) / avg_price
            
            # Score volatility (lower is better for arbitrage)
            if volatility < 0.001:  # < 0.1%
                score = 1.0
                assessment = "Very low volatility"
            elif volatility < 0.005:  # < 0.5%
                score = 0.8
                assessment = "Low volatility"
            elif volatility < 0.01:  # < 1%
                score = 0.6
                assessment = "Moderate volatility"
            elif volatility < 0.02:  # < 2%
                score = 0.3
                assessment = "High volatility"
            else:
                score = 0.1
                assessment = "Very high volatility"
            
            return {
                'name': 'Market Volatility',
                'score': score,
                'assessment': assessment,
                'details': f"Volatility: {volatility:.4f}"
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing volatility: {e}")
            return {'name': 'Market Volatility', 'score': 0.5, 'assessment': 'Analysis failed'}
    
    def _analyze_success_factor(self):
        """Analyze historical success rate"""
        try:
            stats = self.profit_analyzer.get_comprehensive_stats(days=7)
            
            if stats['total_trades'] == 0:
                return {
                    'name': 'Success Rate',
                    'score': 0.5,
                    'assessment': 'No trading history',
                    'details': 'First trade'
                }
            
            success_rate = stats['success_rate']
            avg_profit = stats['avg_profit_per_trade']
            
            # Score based on success rate and profitability
            if success_rate >= 80 and avg_profit > 0:
                score = 1.0
                assessment = "Excellent track record"
            elif success_rate >= 70 and avg_profit > 0:
                score = 0.8
                assessment = "Good track record"
            elif success_rate >= 60:
                score = 0.6
                assessment = "Adequate track record"
            elif success_rate >= 50:
                score = 0.4
                assessment = "Poor track record"
            else:
                score = 0.2
                assessment = "Very poor track record"
            
            return {
                'name': 'Success Rate',
                'score': score,
                'assessment': assessment,
                'details': f"{success_rate:.1f}% success, avg profit: {avg_profit:.4f}"
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing success factor: {e}")
            return {'name': 'Success Rate', 'score': 0.5, 'assessment': 'Analysis failed'}
    
    def _analyze_timing_factor(self):
        """Analyze market timing"""
        try:
            current_hour = datetime.utcnow().hour
            
            # Get historical performance by hour
            stats = self.profit_analyzer.get_comprehensive_stats(days=30)
            time_analysis = stats.get('time_analysis', {})
            
            if 'hourly_performance' not in time_analysis:
                # Default scoring based on typical trading hours
                if 8 <= current_hour <= 16:  # Business hours
                    score = 0.7
                    assessment = "Good trading hours"
                elif 0 <= current_hour <= 6:  # Night hours
                    score = 0.4
                    assessment = "Low activity hours"
                else:
                    score = 0.6
                    assessment = "Moderate activity hours"
            else:
                hourly_perf = time_analysis['hourly_performance']
                
                if current_hour in hourly_perf:
                    hour_profit = hourly_perf[current_hour]
                    
                    # Score based on historical performance this hour
                    if hour_profit > 0.5:
                        score = 1.0
                        assessment = "Excellent timing"
                    elif hour_profit > 0.1:
                        score = 0.8
                        assessment = "Good timing"
                    elif hour_profit > 0:
                        score = 0.6
                        assessment = "Positive timing"
                    elif hour_profit > -0.1:
                        score = 0.4
                        assessment = "Neutral timing"
                    else:
                        score = 0.2
                        assessment = "Poor timing"
                else:
                    score = 0.5
                    assessment = "No historical data"
            
            return {
                'name': 'Market Timing',
                'score': score,
                'assessment': assessment,
                'details': f"Hour: {current_hour}:00"
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing timing factor: {e}")
            return {'name': 'Market Timing', 'score': 0.5, 'assessment': 'Analysis failed'}
    
    def _analyze_balance_factor(self, trade_amount):
        """Analyze balance health for trading"""
        try:
            from core.balance_manager import BalanceManager
            balance_manager = BalanceManager()
            
            balances = balance_manager.get_balances()
            
            # Check XRP balance sufficiency
            xrp_balance = balances.get('XRP', {}).get('free', 0)
            xrp_ratio = trade_amount / xrp_balance if xrp_balance > 0 else 1
            
            # Check stablecoin balance
            usdt_balance = balances.get('USDT', {}).get('free', 0)
            usdc_balance = balances.get('USDC', {}).get('free', 0)
            total_stable = usdt_balance + usdc_balance
            
            estimated_cost = trade_amount * 0.52  # Approximate XRP price
            stable_ratio = estimated_cost / total_stable if total_stable > 0 else 1
            
            # Score based on balance utilization
            max_ratio = max(xrp_ratio, stable_ratio)
            
            if max_ratio < 0.1:  # Using < 10% of balance
                score = 1.0
                assessment = "Excellent balance health"
            elif max_ratio < 0.2:  # Using < 20% of balance
                score = 0.8
                assessment = "Good balance health"
            elif max_ratio < 0.4:  # Using < 40% of balance
                score = 0.6
                assessment = "Adequate balance health"
            elif max_ratio < 0.6:  # Using < 60% of balance
                score = 0.4
                assessment = "Marginal balance health"
            else:
                score = 0.2
                assessment = "Poor balance health"
            
            return {
                'name': 'Balance Health',
                'score': score,
                'assessment': assessment,
                'details': f"Using {max_ratio:.1%} of available balance"
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing balance factor: {e}")
            return {'name': 'Balance Health', 'score': 0.5, 'assessment': 'Analysis failed'}
    
    def optimize_trade_amount(self, base_amount, opportunity, config):
        """Optimize trade amount based on current conditions"""
        try:
            # Start with configured base amount
            optimized_amount = base_amount
            
            # Adjust based on spread size
            spread_pct = opportunity['spread_percentage']
            threshold_pct = config.spread_threshold * 100
            
            if spread_pct > threshold_pct * 2:
                # Large spread - increase trade size by up to 50%
                multiplier = 1 + min(0.5, (spread_pct / threshold_pct - 1) * 0.25)
                optimized_amount *= multiplier
            
            # Adjust based on recent performance
            stats = self.profit_analyzer.get_today_stats()
            if stats['success_rate'] > 80 and stats['total_profit_loss'] > 0:
                # Good performance today - slightly increase trade size
                optimized_amount *= 1.1
            elif stats['success_rate'] < 50 or stats['total_profit_loss'] < 0:
                # Poor performance today - decrease trade size
                optimized_amount *= 0.8
            
            # Ensure we don't exceed configured limits
            optimized_amount = min(optimized_amount, config.trade_amount * 1.5)
            optimized_amount = max(optimized_amount, config.trade_amount * 0.5)
            
            # Safety check - ensure we have sufficient balances
            from core.risk_controller import RiskController
            risk_controller = RiskController()
            max_safe = risk_controller.calculate_max_safe_trade_amount(config)
            
            optimized_amount = min(optimized_amount, max_safe)
            
            self.logger.info(f"Trade amount optimized: {base_amount:.2f} -> {optimized_amount:.2f}")
            
            return optimized_amount
            
        except Exception as e:
            self.logger.error(f"Error optimizing trade amount: {e}")
            return base_amount
