import time
import asyncio
import logging
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from app import db
from models import Trade
from core.api_connector import APIConnector
from core.balance_manager import BalanceManager

class TradeExecutor:
    """Advanced trade execution with ATOMIC EXECUTION for arbitrage"""
    
    def __init__(self):
        self.api = APIConnector()
        self.balance_manager = BalanceManager()
        self.logger = logging.getLogger(__name__)
        self.pending_orders = {}
        self.max_pending_orders = 3
        self.slippage_tolerance = 0.001  # 0.1%
        self.exchange_fees = {
            'maker_fee': 0.0002,  # 0.02%
            'taker_fee': 0.0006   # 0.06%
        }
        
        # Connect to API
        self.api.connect()
    
    def execute_arbitrage_trade(self, opportunity):
        """
        Execute ATOMIC ARBITRAGE TRADE: Both orders placed simultaneously
        
        Args:
            opportunity: Dict with trade details
                - sell_pair: pair to sell (e.g., 'XRP/USDT')
                - buy_pair: pair to buy (e.g., 'XRP/USDC')
                - amount: XRP amount to trade
                - sell_price: expected sell price
                - buy_price: expected buy price
                - estimated_profit: expected profit
        """
        try:
            # Check pending orders limit FIRST
            current_pending = self.get_pending_orders_count()
            if current_pending >= self.max_pending_orders:
                self.logger.warning(f"Maximum pending orders limit reached: {current_pending}/{self.max_pending_orders}")
                return None
            
            amount = opportunity['amount']
            sell_pair = opportunity['sell_pair']
            buy_pair = opportunity['buy_pair']
            
            self.logger.info(f"Starting ATOMIC arbitrage trade: {amount} XRP ({sell_pair} -> {buy_pair})")
            
            # Pre-flight checks with fees
            net_profit = self._calculate_net_profit_with_fees(opportunity)
            if net_profit <= 0:
                self.logger.warning(f"Trade not profitable after fees: {net_profit:.4f}")
                return None
            
            # Pre-validate balances for both sides
            if not self._validate_atomic_trade_balances(opportunity):
                self.logger.error("Insufficient balances for atomic trade")
                return None
            
            # Execute ATOMIC orders (simultaneous execution)
            atomic_result = self._execute_atomic_orders(opportunity)
            
            if not atomic_result:
                self.logger.error("Atomic order execution failed")
                return None
            
            # Process results
            sell_trade = atomic_result['sell_trade']
            buy_trade = atomic_result['buy_trade']
            
            # Calculate actual profit/loss with executed prices
            actual_profit = self._calculate_actual_profit(sell_trade, buy_trade)
            
            # Update profit/loss for both trades
            sell_trade.profit_loss = actual_profit / 2
            buy_trade.profit_loss = actual_profit / 2
            
            db.session.commit()
            
            self.logger.info(f"ATOMIC arbitrage completed. Actual P&L: {actual_profit:.4f}")
            
            return {
                'sell_trade': sell_trade,
                'buy_trade': buy_trade,
                'profit_loss': actual_profit,
                'execution_type': 'atomic',
                'slippage': self._calculate_slippage(opportunity, sell_trade, buy_trade)
            }
            
        except Exception as e:
            self.logger.error(f"Error executing atomic arbitrage trade: {e}")
            db.session.rollback()
            return None
    
    def _execute_sell_order(self, pair, amount, expected_price):
        """Execute a sell order"""
        try:
            # Check if we have sufficient XRP
            if not self.balance_manager.check_sufficient_balance('XRP', amount):
                raise Exception("Insufficient XRP balance for sell order")
            
            # Lock XRP balance
            self.balance_manager.lock_balance('XRP', amount)
            
            # Create trade record
            trade = Trade(
                trade_type='sell',
                pair=pair,
                amount=amount,
                price=expected_price,
                total_value=amount * expected_price,
                status='pending'
            )
            db.session.add(trade)
            db.session.flush()  # Get the trade ID
            
            # Execute order via API
            order = self.api.create_order(
                symbol=pair,
                order_type='market',
                side='sell',
                amount=amount
            )
            
            # Update trade with order details
            trade.order_id = order['id']
            trade.price = order['price']
            trade.total_value = amount * order['price']
            
            # Simulate order completion
            time.sleep(0.1)  # Small delay for realism
            
            # Check order status
            status = self.api.get_order_status(order['id'], pair)
            if status['status'] == 'closed':
                trade.status = 'completed'
                trade.completed_at = datetime.utcnow()
                
                # Update balances
                self.balance_manager.unlock_balance('XRP', amount)
                self.balance_manager.update_balance('XRP', -amount)
                
                # Determine which stablecoin we received
                if 'USDT' in pair:
                    self.balance_manager.update_balance('USDT', trade.total_value)
                else:
                    self.balance_manager.update_balance('USDC', trade.total_value)
                
                self.logger.info(f"Sell order completed: {amount} XRP at {order['price']:.4f}")
            
            db.session.commit()
            return trade
            
        except Exception as e:
            self.logger.error(f"Error executing sell order: {e}")
            db.session.rollback()
            # Unlock balance if it was locked
            try:
                self.balance_manager.unlock_balance('XRP', amount)
            except:
                pass
            return None
    
    def _execute_buy_order(self, pair, amount, expected_price):
        """Execute a buy order"""
        try:
            # Determine which stablecoin we need
            currency = 'USDT' if 'USDT' in pair else 'USDC'
            required_value = amount * expected_price
            
            # Check if we have sufficient stablecoin
            if not self.balance_manager.check_sufficient_balance(currency, required_value):
                raise Exception(f"Insufficient {currency} balance for buy order")
            
            # Lock stablecoin balance
            self.balance_manager.lock_balance(currency, required_value)
            
            # Create trade record
            trade = Trade(
                trade_type='buy',
                pair=pair,
                amount=amount,
                price=expected_price,
                total_value=required_value,
                status='pending'
            )
            db.session.add(trade)
            db.session.flush()  # Get the trade ID
            
            # Execute order via API
            order = self.api.create_order(
                symbol=pair,
                order_type='market',
                side='buy',
                amount=amount
            )
            
            # Update trade with order details
            trade.order_id = order['id']
            trade.price = order['price']
            trade.total_value = amount * order['price']
            
            # Simulate order completion
            time.sleep(0.1)  # Small delay for realism
            
            # Check order status
            status = self.api.get_order_status(order['id'], pair)
            if status['status'] == 'closed':
                trade.status = 'completed'
                trade.completed_at = datetime.utcnow()
                
                # Update balances
                self.balance_manager.unlock_balance(currency, required_value)
                self.balance_manager.update_balance(currency, -trade.total_value)
                self.balance_manager.update_balance('XRP', amount)
                
                self.logger.info(f"Buy order completed: {amount} XRP at {order['price']:.4f}")
            
            db.session.commit()
            return trade
            
        except Exception as e:
            self.logger.error(f"Error executing buy order: {e}")
            db.session.rollback()
            # Unlock balance if it was locked
            try:
                if 'currency' in locals() and 'required_value' in locals():
                    self.balance_manager.unlock_balance(currency, required_value)
            except:
                pass
            return None
    
    def get_pending_orders_count(self):
        """Get count of pending orders"""
        return Trade.query.filter_by(status='pending').count()
    
    def enforce_pending_orders_limit(self):
        """Enforce maximum pending orders limit"""
        try:
            current_count = self.get_pending_orders_count()
            if current_count >= self.max_pending_orders:
                self.logger.warning(f"Pending orders limit reached: {current_count}/{self.max_pending_orders}")
                return False
            return True
        except Exception as e:
            self.logger.error(f"Error checking pending orders limit: {e}")
            return False
    
    def cancel_pending_orders(self):
        """Cancel all pending orders"""
        try:
            pending_trades = Trade.query.filter_by(status='pending').all()
            
            for trade in pending_trades:
                if trade.order_id:
                    try:
                        self.api.cancel_order(trade.order_id, trade.pair)
                    except:
                        pass  # Order might already be completed
                
                trade.status = 'cancelled'
                
                # Unlock balances
                if trade.trade_type == 'sell':
                    self.balance_manager.unlock_balance('XRP', trade.amount)
                else:
                    currency = 'USDT' if 'USDT' in trade.pair else 'USDC'
                    self.balance_manager.unlock_balance(currency, trade.total_value)
            
            db.session.commit()
            self.logger.info(f"Cancelled {len(pending_trades)} pending orders")
            
        except Exception as e:
            self.logger.error(f"Error cancelling pending orders: {e}")
            db.session.rollback()
    
    def _calculate_net_profit_with_fees(self, opportunity):
        """Calculate net profit after exchange fees"""
        try:
            amount = opportunity['amount']
            sell_price = opportunity['sell_price']
            buy_price = opportunity['buy_price']
            
            # Calculate gross values
            sell_gross = amount * sell_price
            buy_gross = amount * buy_price
            
            # Apply exchange fees (using taker fees for conservative estimate)
            sell_fee = sell_gross * self.exchange_fees['taker_fee']
            buy_fee = buy_gross * self.exchange_fees['taker_fee']
            
            # Net values after fees
            sell_net = sell_gross - sell_fee
            buy_net = buy_gross + buy_fee  # We pay more when buying
            
            net_profit = sell_net - buy_net
            
            self.logger.debug(f"Profit calculation: Sell {sell_net:.4f} - Buy {buy_net:.4f} = {net_profit:.4f}")
            return net_profit
            
        except Exception as e:
            self.logger.error(f"Error calculating net profit: {e}")
            return 0
    
    def _validate_atomic_trade_balances(self, opportunity):
        """Validate that we have sufficient balances for atomic trade"""
        try:
            amount = opportunity['amount']
            buy_pair = opportunity['buy_pair']
            buy_price = opportunity['buy_price']
            
            # Check XRP balance for sell side
            if not self.balance_manager.check_sufficient_balance('XRP', amount):
                self.logger.error(f"Insufficient XRP balance: need {amount}")
                return False
            
            # Check stablecoin balance for buy side
            currency = 'USDT' if 'USDT' in buy_pair else 'USDC'
            required_value = amount * buy_price * (1 + self.exchange_fees['taker_fee'])  # Include fee buffer
            
            if not self.balance_manager.check_sufficient_balance(currency, required_value):
                self.logger.error(f"Insufficient {currency} balance: need {required_value:.4f}")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error validating balances: {e}")
            return False
    
    def _execute_atomic_orders(self, opportunity):
        """Execute both orders simultaneously using thread pool"""
        try:
            self.logger.info("Executing ATOMIC orders simultaneously...")
            
            # Prepare order parameters
            sell_params = {
                'pair': opportunity['sell_pair'],
                'amount': opportunity['amount'],
                'expected_price': opportunity['sell_price'],
                'trade_type': 'sell'
            }
            
            buy_params = {
                'pair': opportunity['buy_pair'],
                'amount': opportunity['amount'],
                'expected_price': opportunity['buy_price'],
                'trade_type': 'buy'
            }
            
            # Execute both orders simultaneously using ThreadPoolExecutor
            with ThreadPoolExecutor(max_workers=2) as executor:
                # Submit both orders
                sell_future = executor.submit(self._execute_single_atomic_order, sell_params)
                buy_future = executor.submit(self._execute_single_atomic_order, buy_params)
                
                # Wait for both to complete with timeout
                sell_trade = None
                buy_trade = None
                
                try:
                    # Wait for completion with 10 second timeout
                    for future in as_completed([sell_future, buy_future], timeout=10):
                        result = future.result()
                        if result and result.trade_type == 'sell':
                            sell_trade = result
                        elif result and result.trade_type == 'buy':
                            buy_trade = result
                        else:
                            self.logger.error("One order failed in atomic execution")
                            return None
                
                except Exception as e:
                    self.logger.error(f"Timeout or error in atomic execution: {e}")
                    return None
            
            # Validate both orders completed
            if not sell_trade or not buy_trade:
                self.logger.error("Atomic execution incomplete - rolling back")
                self._rollback_atomic_orders(sell_trade, buy_trade)
                return None
            
            self.logger.info("ATOMIC orders executed successfully")
            return {
                'sell_trade': sell_trade,
                'buy_trade': buy_trade,
                'execution_time': datetime.utcnow()
            }
            
        except Exception as e:
            self.logger.error(f"Error in atomic execution: {e}")
            return None
    
    def _execute_single_atomic_order(self, order_params):
        """Execute a single order as part of atomic execution"""
        try:
            pair = order_params['pair']
            amount = order_params['amount']
            expected_price = order_params['expected_price']
            trade_type = order_params['trade_type']
            
            # Pre-lock balances
            if trade_type == 'sell':
                self.balance_manager.lock_balance('XRP', amount)
                currency = 'XRP'
                lock_amount = amount
            else:
                currency = 'USDT' if 'USDT' in pair else 'USDC'
                required_value = amount * expected_price * (1 + self.exchange_fees['taker_fee'])
                self.balance_manager.lock_balance(currency, required_value)
                lock_amount = required_value
            
            # Create trade record
            trade = Trade(
                trade_type=trade_type,
                pair=pair,
                amount=amount,
                price=expected_price,
                total_value=amount * expected_price,
                status='pending'
            )
            db.session.add(trade)
            db.session.flush()
            
            # Execute order via API with slippage protection
            order = self.api.create_order(
                symbol=pair,
                order_type='limit',  # Use limit orders for slippage protection
                side=trade_type,
                amount=amount,
                price=expected_price * (1 - self.slippage_tolerance) if trade_type == 'sell' else expected_price * (1 + self.slippage_tolerance)
            )
            
            # Update trade with order details
            trade.order_id = order['id']
            trade.price = order['price']
            trade.total_value = amount * order['price']
            
            # Simulate order completion (immediate for limit orders in simulation)
            time.sleep(0.05)  # Small delay for realism
            
            # Check order status
            status = self.api.get_order_status(order['id'], pair)
            if status['status'] == 'closed':
                trade.status = 'completed'
                trade.completed_at = datetime.utcnow()
                
                # Update balances
                self.balance_manager.unlock_balance(currency, lock_amount)
                
                if trade_type == 'sell':
                    self.balance_manager.update_balance('XRP', -amount)
                    stablecoin = 'USDT' if 'USDT' in pair else 'USDC'
                    self.balance_manager.update_balance(stablecoin, trade.total_value)
                else:
                    currency = 'USDT' if 'USDT' in pair else 'USDC'
                    self.balance_manager.update_balance(currency, -trade.total_value)
                    self.balance_manager.update_balance('XRP', amount)
                
                self.logger.info(f"{trade_type.title()} order completed: {amount} XRP at {order['price']:.4f}")
            else:
                trade.status = 'failed'
                self.balance_manager.unlock_balance(currency, lock_amount)
                return None
            
            db.session.commit()
            return trade
            
        except Exception as e:
            self.logger.error(f"Error executing {trade_type} order: {e}")
            db.session.rollback()
            return None
    
    def _rollback_atomic_orders(self, sell_trade, buy_trade):
        """Rollback failed atomic orders"""
        try:
            self.logger.warning("Rolling back failed atomic execution")
            
            if sell_trade and sell_trade.order_id:
                try:
                    self.api.cancel_order(sell_trade.order_id, sell_trade.pair)
                    sell_trade.status = 'cancelled'
                except:
                    pass
            
            if buy_trade and buy_trade.order_id:
                try:
                    self.api.cancel_order(buy_trade.order_id, buy_trade.pair)
                    buy_trade.status = 'cancelled'
                except:
                    pass
            
            db.session.commit()
            
        except Exception as e:
            self.logger.error(f"Error rolling back atomic orders: {e}")
    
    def _calculate_actual_profit(self, sell_trade, buy_trade):
        """Calculate actual profit from executed trades"""
        try:
            sell_value = sell_trade.total_value if sell_trade else 0
            buy_value = buy_trade.total_value if buy_trade else 0
            
            # Apply actual fees based on executed prices
            sell_fee = sell_value * self.exchange_fees['taker_fee']
            buy_fee = buy_value * self.exchange_fees['taker_fee']
            
            actual_profit = (sell_value - sell_fee) - (buy_value + buy_fee)
            
            return actual_profit
            
        except Exception as e:
            self.logger.error(f"Error calculating actual profit: {e}")
            return 0
    
    def _calculate_slippage(self, opportunity, sell_trade, buy_trade):
        """Calculate slippage compared to expected prices"""
        try:
            expected_sell_price = opportunity['sell_price']
            expected_buy_price = opportunity['buy_price']
            
            actual_sell_price = sell_trade.price if sell_trade else expected_sell_price
            actual_buy_price = buy_trade.price if buy_trade else expected_buy_price
            
            sell_slippage = (expected_sell_price - actual_sell_price) / expected_sell_price
            buy_slippage = (actual_buy_price - expected_buy_price) / expected_buy_price
            
            return {
                'sell_slippage': sell_slippage,
                'buy_slippage': buy_slippage,
                'total_slippage_impact': sell_slippage + buy_slippage
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating slippage: {e}")
            return {'sell_slippage': 0, 'buy_slippage': 0, 'total_slippage_impact': 0}
    
    def check_order_timeouts(self, timeout_seconds=30):
        """Check for and handle order timeouts"""
        try:
            cutoff_time = datetime.utcnow() - timedelta(seconds=timeout_seconds)
            
            timed_out_trades = Trade.query.filter(
                Trade.status == 'pending',
                Trade.created_at < cutoff_time
            ).all()
            
            for trade in timed_out_trades:
                self.logger.warning(f"Order timeout detected: {trade.order_id}")
                
                # Try to get final status
                if trade.order_id:
                    try:
                        status = self.api.get_order_status(trade.order_id, trade.pair)
                        if status['status'] == 'closed':
                            trade.status = 'completed'
                            trade.completed_at = datetime.utcnow()
                        else:
                            trade.status = 'timeout'
                            # Unlock balances
                            if trade.trade_type == 'sell':
                                self.balance_manager.unlock_balance('XRP', trade.amount)
                            else:
                                currency = 'USDT' if 'USDT' in trade.pair else 'USDC'
                                self.balance_manager.unlock_balance(currency, trade.total_value)
                    except:
                        trade.status = 'timeout'
            
            db.session.commit()
            
        except Exception as e:
            self.logger.error(f"Error checking order timeouts: {e}")
            db.session.rollback()
