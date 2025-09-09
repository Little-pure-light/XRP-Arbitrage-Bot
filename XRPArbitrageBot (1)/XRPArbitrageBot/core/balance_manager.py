import logging
from app import db
from models import Balance
from core.api_connector import APIConnector

class BalanceManager:
    """Wallet balance management and stablecoin rebalancing"""
    
    def __init__(self):
        self.api = APIConnector()
        self.logger = logging.getLogger(__name__)
        
        # Connect to API
        self.api.connect()
    
    def initialize_balances(self):
        """Initialize balances if they don't exist"""
        try:
            # Check if balances exist
            existing_balances = Balance.query.all()
            if existing_balances:
                return
            
            # Create initial balances
            initial_balances = [
                Balance(currency='XRP', amount=10000.0, locked=0.0),
                Balance(currency='USDT', amount=5000.0, locked=0.0),
                Balance(currency='USDC', amount=5000.0, locked=0.0)
            ]
            
            for balance in initial_balances:
                db.session.add(balance)
            
            db.session.commit()
            self.logger.info("Initialized default balances")
            
        except Exception as e:
            self.logger.error(f"Error initializing balances: {e}")
            db.session.rollback()
    
    def get_balances(self):
        """Get current balances"""
        try:
            balances = {}
            db_balances = Balance.query.all()
            
            for balance in db_balances:
                balances[balance.currency] = {
                    'free': balance.amount,
                    'locked': balance.locked,
                    'total': balance.amount + balance.locked
                }
            
            # If no balances in DB, initialize and get from API simulation
            if not balances:
                self.initialize_balances()
                return self.get_balances()
            
            return balances
            
        except Exception as e:
            self.logger.error(f"Error getting balances: {e}")
            return {}
    
    def update_balance(self, currency, amount_change, lock_change=0):
        """Update balance for a currency"""
        try:
            balance = Balance.query.filter_by(currency=currency).first()
            if not balance:
                balance = Balance(currency=currency, amount=0.0, locked=0.0)
                db.session.add(balance)
            
            balance.amount += amount_change
            balance.locked += lock_change
            
            # Ensure no negative balances
            if balance.amount < 0:
                balance.amount = 0
            if balance.locked < 0:
                balance.locked = 0
            
            db.session.commit()
            self.logger.info(f"Updated {currency} balance: {amount_change:+.4f}")
            
        except Exception as e:
            self.logger.error(f"Error updating balance: {e}")
            db.session.rollback()
    
    def lock_balance(self, currency, amount):
        """Lock balance for pending trades"""
        try:
            balance = Balance.query.filter_by(currency=currency).first()
            if not balance:
                raise Exception(f"No balance found for {currency}")
            
            if balance.amount < amount:
                raise Exception(f"Insufficient {currency} balance")
            
            balance.amount -= amount
            balance.locked += amount
            
            db.session.commit()
            self.logger.info(f"Locked {amount:.4f} {currency}")
            
        except Exception as e:
            self.logger.error(f"Error locking balance: {e}")
            db.session.rollback()
            raise
    
    def unlock_balance(self, currency, amount):
        """Unlock balance after trade completion"""
        try:
            balance = Balance.query.filter_by(currency=currency).first()
            if not balance:
                raise Exception(f"No balance found for {currency}")
            
            if balance.locked < amount:
                self.logger.warning(f"Trying to unlock more {currency} than locked")
                amount = balance.locked
            
            balance.locked -= amount
            balance.amount += amount
            
            db.session.commit()
            self.logger.info(f"Unlocked {amount:.4f} {currency}")
            
        except Exception as e:
            self.logger.error(f"Error unlocking balance: {e}")
            db.session.rollback()
    
    def check_sufficient_balance(self, currency, required_amount, safety_buffer=0.1):
        """Check if there's sufficient balance for a trade"""
        try:
            balance = Balance.query.filter_by(currency=currency).first()
            if not balance:
                return False
            
            available = balance.amount
            required_with_buffer = required_amount * (1 + safety_buffer)
            
            return available >= required_with_buffer
            
        except Exception as e:
            self.logger.error(f"Error checking balance: {e}")
            return False
    
    def rebalance_stablecoins(self, target_ratio=0.5):
        """Rebalance USDT/USDC to maintain target ratio"""
        try:
            balances = self.get_balances()
            
            if 'USDT' not in balances or 'USDC' not in balances:
                self.logger.warning("USDT or USDC balance not found")
                return
            
            usdt_balance = balances['USDT']['free']
            usdc_balance = balances['USDC']['free']
            total_stable = usdt_balance + usdc_balance
            
            if total_stable == 0:
                return
            
            target_usdt = total_stable * target_ratio
            target_usdc = total_stable * (1 - target_ratio)
            
            usdt_diff = target_usdt - usdt_balance
            usdc_diff = target_usdc - usdc_balance
            
            # Only rebalance if difference is significant (>5%)
            if abs(usdt_diff) / total_stable > 0.05:
                if usdt_diff > 0:
                    # Need more USDT, convert USDC to USDT
                    self.update_balance('USDC', -abs(usdt_diff))
                    self.update_balance('USDT', abs(usdt_diff))
                    self.logger.info(f"Rebalanced: Converted {abs(usdt_diff):.2f} USDC to USDT")
                else:
                    # Need more USDC, convert USDT to USDC
                    self.update_balance('USDT', -abs(usdc_diff))
                    self.update_balance('USDC', abs(usdc_diff))
                    self.logger.info(f"Rebalanced: Converted {abs(usdc_diff):.2f} USDT to USDC")
            
        except Exception as e:
            self.logger.error(f"Error rebalancing stablecoins: {e}")
    
    def get_balance_summary(self):
        """Get balance summary with totals"""
        try:
            balances = self.get_balances()
            
            # Calculate USD equivalents (assuming XRP price)
            from core.price_monitor import PriceMonitor
            price_monitor = PriceMonitor()
            prices = price_monitor.get_current_prices()
            
            xrp_price = 0.52  # Default fallback
            if 'XRP/USDT' in prices:
                xrp_price = prices['XRP/USDT']['price']
            
            summary = {
                'balances': balances,
                'totals': {
                    'xrp_usd_value': balances.get('XRP', {}).get('total', 0) * xrp_price,
                    'stable_total': (balances.get('USDT', {}).get('total', 0) + 
                                   balances.get('USDC', {}).get('total', 0)),
                    'portfolio_total': 0
                }
            }
            
            summary['totals']['portfolio_total'] = (
                summary['totals']['xrp_usd_value'] + 
                summary['totals']['stable_total']
            )
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Error getting balance summary: {e}")
            return {'balances': {}, 'totals': {}}
