import logging
from datetime import datetime, timedelta
from sqlalchemy import func
from app import db
from models import Trade, PriceHistory, ArbitrageOpportunity, Balance
from core.profit_analyzer import ProfitAnalyzer

class DataPipeline:
    """Data processing pipeline for trading analytics"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.profit_analyzer = ProfitAnalyzer()
    
    def process_trading_data(self, time_range='24h'):
        """Process and aggregate trading data for analytics"""
        try:
            # Determine time range
            if time_range == '1h':
                cutoff = datetime.utcnow() - timedelta(hours=1)
            elif time_range == '24h':
                cutoff = datetime.utcnow() - timedelta(hours=24)
            elif time_range == '7d':
                cutoff = datetime.utcnow() - timedelta(days=7)
            elif time_range == '30d':
                cutoff = datetime.utcnow() - timedelta(days=30)
            else:
                cutoff = datetime.utcnow() - timedelta(hours=24)
            
            # Aggregate trade data
            trade_summary = self._aggregate_trades(cutoff)
            
            # Process price movements
            price_analysis = self._analyze_price_movements(cutoff)
            
            # Calculate spread statistics
            spread_stats = self._calculate_spread_statistics(cutoff)
            
            # Generate opportunity analysis
            opportunity_analysis = self._analyze_opportunities(cutoff)
            
            # Risk metrics
            risk_metrics = self._calculate_risk_metrics(cutoff)
            
            processed_data = {
                'time_range': time_range,
                'processed_at': datetime.utcnow().isoformat(),
                'trade_summary': trade_summary,
                'price_analysis': price_analysis,
                'spread_statistics': spread_stats,
                'opportunity_analysis': opportunity_analysis,
                'risk_metrics': risk_metrics
            }
            
            return processed_data
            
        except Exception as e:
            self.logger.error(f"Error processing trading data: {e}")
            return {}
    
    def _aggregate_trades(self, cutoff_time):
        """Aggregate trade data for the specified time period"""
        try:
            trades = Trade.query.filter(Trade.created_at >= cutoff_time).all()
            
            if not trades:
                return {
                    'total_trades': 0,
                    'total_volume': 0.0,
                    'total_profit_loss': 0.0,
                    'avg_trade_size': 0.0,
                    'success_rate': 0.0,
                    'trades_by_hour': {},
                    'trades_by_pair': {}
                }
            
            # Basic aggregations
            total_trades = len(trades)
            total_volume = sum(trade.amount for trade in trades)
            completed_trades = [t for t in trades if t.status == 'completed']
            total_profit_loss = sum(trade.profit_loss or 0 for trade in completed_trades)
            
            avg_trade_size = total_volume / total_trades if total_trades > 0 else 0
            profitable_trades = len([t for t in completed_trades if (t.profit_loss or 0) > 0])
            success_rate = (profitable_trades / len(completed_trades) * 100) if completed_trades else 0
            
            # Trades by hour
            trades_by_hour = {}
            for trade in trades:
                hour = trade.created_at.hour
                if hour not in trades_by_hour:
                    trades_by_hour[hour] = {'count': 0, 'volume': 0, 'profit': 0}
                trades_by_hour[hour]['count'] += 1
                trades_by_hour[hour]['volume'] += trade.amount
                trades_by_hour[hour]['profit'] += trade.profit_loss or 0
            
            # Trades by pair
            trades_by_pair = {}
            for trade in trades:
                pair = trade.pair
                if pair not in trades_by_pair:
                    trades_by_pair[pair] = {'count': 0, 'volume': 0, 'profit': 0}
                trades_by_pair[pair]['count'] += 1
                trades_by_pair[pair]['volume'] += trade.amount
                trades_by_pair[pair]['profit'] += trade.profit_loss or 0
            
            return {
                'total_trades': total_trades,
                'total_volume': total_volume,
                'total_profit_loss': total_profit_loss,
                'avg_trade_size': avg_trade_size,
                'success_rate': success_rate,
                'trades_by_hour': trades_by_hour,
                'trades_by_pair': trades_by_pair,
                'completed_trades': len(completed_trades),
                'pending_trades': len([t for t in trades if t.status == 'pending']),
                'failed_trades': len([t for t in trades if t.status == 'failed'])
            }
            
        except Exception as e:
            self.logger.error(f"Error aggregating trades: {e}")
            return {}
    
    def _analyze_price_movements(self, cutoff_time):
        """Analyze price movements and volatility"""
        try:
            # Get price history for both pairs
            usdt_prices = PriceHistory.query.filter(
                PriceHistory.pair == 'XRP/USDT',
                PriceHistory.timestamp >= cutoff_time
            ).order_by(PriceHistory.timestamp).all()
            
            usdc_prices = PriceHistory.query.filter(
                PriceHistory.pair == 'XRP/USDC',
                PriceHistory.timestamp >= cutoff_time
            ).order_by(PriceHistory.timestamp).all()
            
            analysis = {}
            
            # Analyze USDT pair
            if usdt_prices:
                usdt_values = [p.price for p in usdt_prices]
                analysis['XRP/USDT'] = self._calculate_price_stats(usdt_values)
                analysis['XRP/USDT']['data_points'] = len(usdt_prices)
            
            # Analyze USDC pair
            if usdc_prices:
                usdc_values = [p.price for p in usdc_prices]
                analysis['XRP/USDC'] = self._calculate_price_stats(usdc_values)
                analysis['XRP/USDC']['data_points'] = len(usdc_prices)
            
            # Calculate correlation if both pairs have data
            if usdt_prices and usdc_prices:
                usdt_values = [p.price for p in usdt_prices] if 'usdt_values' not in locals() else usdt_values
                usdc_values = [p.price for p in usdc_prices] if 'usdc_values' not in locals() else usdc_values
                correlation = self._calculate_price_correlation(usdt_values, usdc_values)
                analysis['correlation'] = correlation
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"Error analyzing price movements: {e}")
            return {}
    
    def _calculate_price_stats(self, prices):
        """Calculate statistical measures for price data"""
        if not prices or len(prices) < 2:
            return {
                'min': 0, 'max': 0, 'avg': 0, 'volatility': 0,
                'change': 0, 'change_percent': 0
            }
        
        min_price = min(prices)
        max_price = max(prices)
        avg_price = sum(prices) / len(prices)
        
        # Calculate volatility (standard deviation)
        variance = sum((p - avg_price) ** 2 for p in prices) / (len(prices) - 1)
        volatility = variance ** 0.5
        
        # Price change
        price_change = prices[-1] - prices[0]
        change_percent = (price_change / prices[0] * 100) if prices[0] > 0 else 0
        
        return {
            'min': min_price,
            'max': max_price,
            'avg': avg_price,
            'volatility': volatility,
            'change': price_change,
            'change_percent': change_percent,
            'current': prices[-1]
        }
    
    def _calculate_price_correlation(self, prices1, prices2):
        """Calculate correlation between two price series"""
        try:
            if len(prices1) != len(prices2) or len(prices1) < 2:
                return 0
            
            # Take the minimum length to ensure equal lengths
            min_len = min(len(prices1), len(prices2))
            p1 = prices1[:min_len]
            p2 = prices2[:min_len]
            
            # Calculate means
            mean1 = sum(p1) / len(p1)
            mean2 = sum(p2) / len(p2)
            
            # Calculate correlation coefficient
            numerator = sum((p1[i] - mean1) * (p2[i] - mean2) for i in range(len(p1)))
            
            sum_sq1 = sum((p - mean1) ** 2 for p in p1)
            sum_sq2 = sum((p - mean2) ** 2 for p in p2)
            denominator = (sum_sq1 * sum_sq2) ** 0.5
            
            correlation = numerator / denominator if denominator > 0 else 0
            return correlation
            
        except Exception as e:
            self.logger.error(f"Error calculating correlation: {e}")
            return 0
    
    def _calculate_spread_statistics(self, cutoff_time):
        """Calculate spread statistics and trends"""
        try:
            opportunities = ArbitrageOpportunity.query.filter(
                ArbitrageOpportunity.created_at >= cutoff_time
            ).order_by(ArbitrageOpportunity.created_at).all()
            
            if not opportunities:
                return {
                    'avg_spread': 0,
                    'max_spread': 0,
                    'min_spread': 0,
                    'spread_volatility': 0,
                    'spread_trend': 'neutral'
                }
            
            spreads = [opp.spread_percentage for opp in opportunities]
            
            avg_spread = sum(spreads) / len(spreads)
            max_spread = max(spreads)
            min_spread = min(spreads)
            
            # Calculate spread volatility
            spread_variance = sum((s - avg_spread) ** 2 for s in spreads) / len(spreads)
            spread_volatility = spread_variance ** 0.5
            
            # Determine spread trend
            if len(spreads) >= 5:
                recent_avg = sum(spreads[-5:]) / 5
                older_avg = sum(spreads[:5]) / 5
                
                if recent_avg > older_avg * 1.1:
                    spread_trend = 'increasing'
                elif recent_avg < older_avg * 0.9:
                    spread_trend = 'decreasing'
                else:
                    spread_trend = 'stable'
            else:
                spread_trend = 'insufficient_data'
            
            return {
                'avg_spread': avg_spread,
                'max_spread': max_spread,
                'min_spread': min_spread,
                'spread_volatility': spread_volatility,
                'spread_trend': spread_trend,
                'total_opportunities': len(opportunities)
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating spread statistics: {e}")
            return {}
    
    def _analyze_opportunities(self, cutoff_time):
        """Analyze arbitrage opportunities"""
        try:
            opportunities = ArbitrageOpportunity.query.filter(
                ArbitrageOpportunity.created_at >= cutoff_time
            ).all()
            
            if not opportunities:
                return {
                    'total_opportunities': 0,
                    'executed_opportunities': 0,
                    'execution_rate': 0,
                    'avg_opportunity_duration': 0
                }
            
            total_opportunities = len(opportunities)
            executed_opportunities = len([o for o in opportunities if o.executed])
            execution_rate = (executed_opportunities / total_opportunities * 100) if total_opportunities > 0 else 0
            
            # Analyze opportunity types
            opportunity_types = {}
            for opp in opportunities:
                opp_type = opp.opportunity_type
                if opp_type not in opportunity_types:
                    opportunity_types[opp_type] = {'count': 0, 'executed': 0}
                opportunity_types[opp_type]['count'] += 1
                if opp.executed:
                    opportunity_types[opp_type]['executed'] += 1
            
            return {
                'total_opportunities': total_opportunities,
                'executed_opportunities': executed_opportunities,
                'execution_rate': execution_rate,
                'opportunity_types': opportunity_types,
                'missed_opportunities': total_opportunities - executed_opportunities
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing opportunities: {e}")
            return {}
    
    def _calculate_risk_metrics(self, cutoff_time):
        """Calculate risk metrics for the time period"""
        try:
            trades = Trade.query.filter(
                Trade.created_at >= cutoff_time,
                Trade.status == 'completed'
            ).all()
            
            if not trades:
                return {
                    'value_at_risk': 0,
                    'max_drawdown': 0,
                    'risk_score': 0
                }
            
            # Calculate returns
            returns = [trade.profit_loss or 0 for trade in trades]
            
            # Value at Risk (95% confidence)
            if len(returns) >= 20:
                sorted_returns = sorted(returns)
                var_index = int(len(sorted_returns) * 0.05)  # 5th percentile
                value_at_risk = abs(sorted_returns[var_index])
            else:
                value_at_risk = 0
            
            # Maximum drawdown calculation
            cumulative_returns = []
            running_total = 0
            for ret in returns:
                running_total += ret
                cumulative_returns.append(running_total)
            
            peak = cumulative_returns[0] if cumulative_returns else 0
            max_drawdown = 0
            
            for value in cumulative_returns:
                if value > peak:
                    peak = value
                drawdown = peak - value
                if drawdown > max_drawdown:
                    max_drawdown = drawdown
            
            # Risk score (0-100, lower is better)
            avg_return = sum(returns) / len(returns) if returns else 0
            volatility = (sum((r - avg_return) ** 2 for r in returns) / len(returns)) ** 0.5 if returns else 0
            
            if avg_return > 0 and volatility > 0:
                sharpe_ratio = avg_return / volatility
                risk_score = max(0, min(100, 50 - (sharpe_ratio * 10)))
            else:
                risk_score = 75  # High risk if no positive returns or no volatility data
            
            return {
                'value_at_risk': value_at_risk,
                'max_drawdown': max_drawdown,
                'risk_score': risk_score,
                'volatility': volatility,
                'total_risk_events': len([r for r in returns if r < 0])
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating risk metrics: {e}")
            return {}
    
    def generate_trading_report(self, time_range='24h'):
        """Generate comprehensive trading report"""
        try:
            processed_data = self.process_trading_data(time_range)
            
            # Get current system status
            from core.balance_manager import BalanceManager
            balance_manager = BalanceManager()
            current_balances = balance_manager.get_balance_summary()
            
            # Get profit analysis
            profit_stats = self.profit_analyzer.get_comprehensive_stats()
            
            report = {
                'generated_at': datetime.utcnow().isoformat(),
                'time_range': time_range,
                'summary': {
                    'total_trades': processed_data.get('trade_summary', {}).get('total_trades', 0),
                    'total_profit_loss': processed_data.get('trade_summary', {}).get('total_profit_loss', 0),
                    'success_rate': processed_data.get('trade_summary', {}).get('success_rate', 0),
                    'risk_score': processed_data.get('risk_metrics', {}).get('risk_score', 0)
                },
                'processed_data': processed_data,
                'current_balances': current_balances,
                'profit_analysis': profit_stats
            }
            
            return report
            
        except Exception as e:
            self.logger.error(f"Error generating trading report: {e}")
            return {}
