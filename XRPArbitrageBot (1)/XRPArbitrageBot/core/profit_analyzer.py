import logging
from datetime import datetime, timedelta
from sqlalchemy import func
from app import db
from models import Trade

class ProfitAnalyzer:
    """Profit/loss analysis and statistics"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def get_today_stats(self):
        """Get today's trading statistics"""
        try:
            today = datetime.utcnow().date()
            today_start = datetime.combine(today, datetime.min.time())
            
            # Get today's completed trades
            today_trades = Trade.query.filter(
                Trade.created_at >= today_start,
                Trade.status == 'completed'
            ).all()
            
            if not today_trades:
                return {
                    'total_trades': 0,
                    'total_profit_loss': 0.0,
                    'total_volume': 0.0,
                    'avg_profit_per_trade': 0.0,
                    'success_rate': 0.0,
                    'profitable_trades': 0,
                    'losing_trades': 0
                }
            
            total_trades = len(today_trades)
            total_profit_loss = sum(trade.profit_loss or 0 for trade in today_trades)
            total_volume = sum(trade.amount for trade in today_trades)
            avg_profit_per_trade = total_profit_loss / total_trades if total_trades > 0 else 0
            
            # Count profitable vs losing trades
            profitable_trades = len([t for t in today_trades if (t.profit_loss or 0) > 0])
            losing_trades = len([t for t in today_trades if (t.profit_loss or 0) < 0])
            success_rate = (profitable_trades / total_trades * 100) if total_trades > 0 else 0
            
            return {
                'total_trades': total_trades,
                'total_profit_loss': total_profit_loss,
                'total_volume': total_volume,
                'avg_profit_per_trade': avg_profit_per_trade,
                'success_rate': success_rate,
                'profitable_trades': profitable_trades,
                'losing_trades': losing_trades
            }
            
        except Exception as e:
            self.logger.error(f"Error getting today's stats: {e}")
            return {}
    
    def get_comprehensive_stats(self, days=30):
        """Get comprehensive trading statistics"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            # Get all completed trades in the period
            trades = Trade.query.filter(
                Trade.created_at >= cutoff_date,
                Trade.status == 'completed'
            ).all()
            
            if not trades:
                return self._empty_stats()
            
            # Basic statistics
            total_trades = len(trades)
            total_profit_loss = sum(trade.profit_loss or 0 for trade in trades)
            total_volume = sum(trade.amount for trade in trades)
            
            # Profit/loss analysis
            profitable_trades = [t for t in trades if (t.profit_loss or 0) > 0]
            losing_trades = [t for t in trades if (t.profit_loss or 0) < 0]
            
            success_rate = (len(profitable_trades) / total_trades * 100) if total_trades > 0 else 0
            avg_profit_per_trade = total_profit_loss / total_trades if total_trades > 0 else 0
            
            # Profit statistics
            if profitable_trades:
                avg_winning_trade = sum(t.profit_loss for t in profitable_trades) / len(profitable_trades)
                max_winning_trade = max(t.profit_loss for t in profitable_trades)
            else:
                avg_winning_trade = 0
                max_winning_trade = 0
            
            # Loss statistics
            if losing_trades:
                avg_losing_trade = sum(t.profit_loss for t in losing_trades) / len(losing_trades)
                max_losing_trade = min(t.profit_loss for t in losing_trades)
            else:
                avg_losing_trade = 0
                max_losing_trade = 0
            
            # Drawdown analysis
            drawdown_stats = self._calculate_drawdown(trades)
            
            # Time-based analysis
            time_stats = self._analyze_time_performance(trades)
            
            # Risk metrics
            risk_metrics = self._calculate_risk_metrics(trades)
            
            return {
                'period_days': days,
                'total_trades': total_trades,
                'total_profit_loss': total_profit_loss,
                'total_volume': total_volume,
                'success_rate': success_rate,
                'avg_profit_per_trade': avg_profit_per_trade,
                'profitable_trades_count': len(profitable_trades),
                'losing_trades_count': len(losing_trades),
                'avg_winning_trade': avg_winning_trade,
                'avg_losing_trade': avg_losing_trade,
                'max_winning_trade': max_winning_trade,
                'max_losing_trade': max_losing_trade,
                'drawdown': drawdown_stats,
                'time_analysis': time_stats,
                'risk_metrics': risk_metrics
            }
            
        except Exception as e:
            self.logger.error(f"Error getting comprehensive stats: {e}")
            return self._empty_stats()
    
    def _empty_stats(self):
        """Return empty statistics structure"""
        return {
            'period_days': 0,
            'total_trades': 0,
            'total_profit_loss': 0.0,
            'total_volume': 0.0,
            'success_rate': 0.0,
            'avg_profit_per_trade': 0.0,
            'profitable_trades_count': 0,
            'losing_trades_count': 0,
            'avg_winning_trade': 0.0,
            'avg_losing_trade': 0.0,
            'max_winning_trade': 0.0,
            'max_losing_trade': 0.0,
            'drawdown': {'max_drawdown': 0, 'current_drawdown': 0},
            'time_analysis': {'best_hour': 0, 'worst_hour': 0},
            'risk_metrics': {'sharpe_ratio': 0, 'win_loss_ratio': 0}
        }
    
    def _calculate_drawdown(self, trades):
        """Calculate maximum and current drawdown"""
        try:
            if not trades:
                return {'max_drawdown': 0, 'current_drawdown': 0}
            
            # Sort trades by time
            sorted_trades = sorted(trades, key=lambda x: x.created_at)
            
            # Calculate cumulative P&L
            cumulative_pnl = []
            running_total = 0
            
            for trade in sorted_trades:
                running_total += trade.profit_loss or 0
                cumulative_pnl.append(running_total)
            
            # Calculate drawdown
            peak = cumulative_pnl[0]
            max_drawdown = 0
            current_drawdown = 0
            
            for pnl in cumulative_pnl:
                if pnl > peak:
                    peak = pnl
                
                drawdown = peak - pnl
                if drawdown > max_drawdown:
                    max_drawdown = drawdown
            
            # Current drawdown is from the last peak
            current_peak = max(cumulative_pnl)
            current_drawdown = current_peak - cumulative_pnl[-1]
            
            return {
                'max_drawdown': max_drawdown,
                'current_drawdown': current_drawdown
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating drawdown: {e}")
            return {'max_drawdown': 0, 'current_drawdown': 0}
    
    def _analyze_time_performance(self, trades):
        """Analyze performance by time of day"""
        try:
            if not trades:
                return {'best_hour': 0, 'worst_hour': 0}
            
            # Group trades by hour
            hourly_performance = {}
            
            for trade in trades:
                hour = trade.created_at.hour
                if hour not in hourly_performance:
                    hourly_performance[hour] = []
                hourly_performance[hour].append(trade.profit_loss or 0)
            
            # Calculate average performance per hour
            hourly_avg = {}
            for hour, profits in hourly_performance.items():
                hourly_avg[hour] = sum(profits) / len(profits)
            
            # Find best and worst hours
            if hourly_avg:
                best_hour = max(hourly_avg.keys(), key=lambda k: hourly_avg[k])
                worst_hour = min(hourly_avg.keys(), key=lambda k: hourly_avg[k])
            else:
                best_hour = 0
                worst_hour = 0
            
            return {
                'best_hour': best_hour,
                'worst_hour': worst_hour,
                'hourly_performance': hourly_avg
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing time performance: {e}")
            return {'best_hour': 0, 'worst_hour': 0}
    
    def _calculate_risk_metrics(self, trades):
        """Calculate risk-adjusted performance metrics"""
        try:
            if not trades or len(trades) < 2:
                return {'sharpe_ratio': 0, 'win_loss_ratio': 0}
            
            # Calculate returns
            returns = [trade.profit_loss or 0 for trade in trades]
            avg_return = sum(returns) / len(returns)
            
            # Calculate standard deviation
            variance = sum((r - avg_return) ** 2 for r in returns) / (len(returns) - 1)
            std_dev = variance ** 0.5
            
            # Sharpe ratio (assuming risk-free rate of 0)
            sharpe_ratio = avg_return / std_dev if std_dev > 0 else 0
            
            # Win/Loss ratio
            profitable_trades = [r for r in returns if r > 0]
            losing_trades = [r for r in returns if r < 0]
            
            if profitable_trades and losing_trades:
                avg_win = sum(profitable_trades) / len(profitable_trades)
                avg_loss = abs(sum(losing_trades) / len(losing_trades))
                win_loss_ratio = avg_win / avg_loss
            else:
                win_loss_ratio = 0
            
            return {
                'sharpe_ratio': sharpe_ratio,
                'win_loss_ratio': win_loss_ratio,
                'volatility': std_dev,
                'avg_return': avg_return
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating risk metrics: {e}")
            return {'sharpe_ratio': 0, 'win_loss_ratio': 0}
    
    def get_daily_performance(self, days=30):
        """Get daily performance breakdown"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            # Get trades grouped by date
            trades = Trade.query.filter(
                Trade.created_at >= cutoff_date,
                Trade.status == 'completed'
            ).all()
            
            # Group by date
            daily_performance = {}
            
            for trade in trades:
                date_key = trade.created_at.date().isoformat()
                if date_key not in daily_performance:
                    daily_performance[date_key] = {
                        'trades': 0,
                        'profit_loss': 0.0,
                        'volume': 0.0
                    }
                
                daily_performance[date_key]['trades'] += 1
                daily_performance[date_key]['profit_loss'] += trade.profit_loss or 0
                daily_performance[date_key]['volume'] += trade.amount
            
            return daily_performance
            
        except Exception as e:
            self.logger.error(f"Error getting daily performance: {e}")
            return {}
    
    def get_pair_performance(self, days=30):
        """Get performance breakdown by trading pair"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            trades = Trade.query.filter(
                Trade.created_at >= cutoff_date,
                Trade.status == 'completed'
            ).all()
            
            # Group by pair
            pair_performance = {}
            
            for trade in trades:
                pair = trade.pair
                if pair not in pair_performance:
                    pair_performance[pair] = {
                        'trades': 0,
                        'profit_loss': 0.0,
                        'volume': 0.0,
                        'avg_price': 0.0
                    }
                
                pair_performance[pair]['trades'] += 1
                pair_performance[pair]['profit_loss'] += trade.profit_loss or 0
                pair_performance[pair]['volume'] += trade.amount
                pair_performance[pair]['avg_price'] = (
                    pair_performance[pair]['avg_price'] * (pair_performance[pair]['trades'] - 1) + trade.price
                ) / pair_performance[pair]['trades']
            
            return pair_performance
            
        except Exception as e:
            self.logger.error(f"Error getting pair performance: {e}")
            return {}
