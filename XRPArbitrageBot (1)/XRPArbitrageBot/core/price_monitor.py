import time
import threading
import logging
from datetime import datetime
from app import db
from models import PriceHistory
from core.api_connector import APIConnector

class PriceMonitor:
    """Real-time XRP price monitoring"""
    
    def __init__(self):
        self.api = APIConnector()
        self.running = False
        self.thread = None
        self.current_prices = {}
        self.last_update = None
        self.logger = logging.getLogger(__name__)
        
        # Connect to API
        self.api.connect()
    
    def start_monitoring(self):
        """Start price monitoring in background thread"""
        if self.running:
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._monitor_loop)
        self.thread.daemon = True
        self.thread.start()
        self.logger.info("Price monitoring started")
    
    def stop_monitoring(self):
        """Stop price monitoring"""
        self.running = False
        if self.thread:
            self.thread.join()
        self.logger.info("Price monitoring stopped")
    
    def _monitor_loop(self):
        """Main monitoring loop"""
        while self.running:
            try:
                # Get current prices
                usdt_ticker = self.api.get_ticker('XRP/USDT')
                usdc_ticker = self.api.get_ticker('XRP/USDC')
                
                # Update current prices
                self.current_prices = {
                    'XRP/USDT': {
                        'price': usdt_ticker['last'],
                        'bid': usdt_ticker['bid'],
                        'ask': usdt_ticker['ask'],
                        'volume': usdt_ticker['volume'],
                        'timestamp': datetime.utcnow()
                    },
                    'XRP/USDC': {
                        'price': usdc_ticker['last'],
                        'bid': usdc_ticker['bid'],
                        'ask': usdc_ticker['ask'],
                        'volume': usdc_ticker['volume'],
                        'timestamp': datetime.utcnow()
                    }
                }
                
                self.last_update = datetime.utcnow()
                
                # Store in database every 10th update (reduce storage)
                if int(time.time()) % 10 == 0:
                    self._store_price_history()
                
                # Calculate and log spread
                spread = abs(usdt_ticker['last'] - usdc_ticker['last'])
                spread_percentage = (spread / usdt_ticker['last']) * 100
                
                if spread_percentage > 0.1:  # Log significant spreads
                    self.logger.info(f"Spread detected: {spread_percentage:.4f}% "
                                   f"(USDT: {usdt_ticker['last']:.4f}, "
                                   f"USDC: {usdc_ticker['last']:.4f})")
                
            except Exception as e:
                self.logger.error(f"Error in price monitoring: {e}")
            
            # Update every 2 seconds
            time.sleep(2)
    
    def _store_price_history(self):
        """Store current prices in database"""
        try:
            from app import app
            with app.app_context():
                for pair, data in self.current_prices.items():
                    price_history = PriceHistory(
                        pair=pair,
                        price=data['price'],
                        volume=data['volume']
                    )
                    db.session.add(price_history)
                
                db.session.commit()
        except Exception as e:
            self.logger.error(f"Error storing price history: {e}")
            try:
                from app import app
                with app.app_context():
                    db.session.rollback()
            except:
                pass
    
    def get_current_prices(self):
        """Get current prices"""
        if not self.current_prices:
            # If no prices yet, get initial prices
            try:
                usdt_ticker = self.api.get_ticker('XRP/USDT')
                usdc_ticker = self.api.get_ticker('XRP/USDC')
                
                self.current_prices = {
                    'XRP/USDT': {
                        'price': usdt_ticker['last'],
                        'bid': usdt_ticker['bid'],
                        'ask': usdt_ticker['ask'],
                        'volume': usdt_ticker['volume'],
                        'timestamp': datetime.utcnow()
                    },
                    'XRP/USDC': {
                        'price': usdc_ticker['last'],
                        'bid': usdc_ticker['bid'],
                        'ask': usdc_ticker['ask'],
                        'volume': usdc_ticker['volume'],
                        'timestamp': datetime.utcnow()
                    }
                }
                self.last_update = datetime.utcnow()
            except Exception as e:
                self.logger.error(f"Error getting initial prices: {e}")
                return {}
        
        # Calculate spread
        if 'XRP/USDT' in self.current_prices and 'XRP/USDC' in self.current_prices:
            usdt_price = self.current_prices['XRP/USDT']['price']
            usdc_price = self.current_prices['XRP/USDC']['price']
            spread = abs(usdt_price - usdc_price)
            spread_percentage = (spread / usdt_price) * 100
            
            return {
                'XRP/USDT': self.current_prices['XRP/USDT'],
                'XRP/USDC': self.current_prices['XRP/USDC'],
                'spread': spread,
                'spread_percentage': spread_percentage,
                'last_update': self.last_update.isoformat() if self.last_update else None
            }
        
        return self.current_prices
    
    def get_last_update(self):
        """Get timestamp of last price update"""
        return self.last_update.isoformat() if self.last_update else None
    
    def get_spread(self):
        """Get current spread between XRP/USDT and XRP/USDC"""
        prices = self.get_current_prices()
        if 'spread' in prices:
            return prices['spread'], prices['spread_percentage']
        return 0, 0
