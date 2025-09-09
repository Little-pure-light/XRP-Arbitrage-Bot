import random
import time
import logging
from datetime import datetime

class APIConnector:
    """MEXC exchange API connection simulator"""
    
    def __init__(self):
        self.connected = False
        self.last_ping = None
        self.logger = logging.getLogger(__name__)
        
    def connect(self):
        """Simulate API connection"""
        try:
            # Simulate connection delay
            time.sleep(0.5)
            self.connected = True
            self.last_ping = datetime.utcnow()
            self.logger.info("Connected to MEXC API (simulated)")
            return True
        except Exception as e:
            self.logger.error(f"Failed to connect to API: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from API"""
        self.connected = False
        self.last_ping = None
        self.logger.info("Disconnected from MEXC API")
    
    def is_connected(self):
        """Check if API is connected"""
        return self.connected
    
    def get_ticker(self, symbol):
        """Get ticker data for a symbol"""
        if not self.connected:
            raise Exception("API not connected")
        
        # Simulate realistic XRP prices with small variations
        base_prices = {
            'XRP/USDT': 0.5234,
            'XRP/USDC': 0.5241
        }
        
        if symbol not in base_prices:
            raise Exception(f"Symbol {symbol} not found")
        
        base_price = base_prices[symbol]
        # Add small random variation (-0.5% to +0.5%)
        variation = random.uniform(-0.005, 0.005)
        current_price = base_price * (1 + variation)
        
        # Simulate volume
        volume = random.uniform(1000000, 5000000)
        
        ticker = {
            'symbol': symbol,
            'last': current_price,
            'bid': current_price * 0.9995,
            'ask': current_price * 1.0005,
            'volume': volume,
            'timestamp': datetime.utcnow().timestamp() * 1000
        }
        
        return ticker
    
    def get_balance(self):
        """Get account balance"""
        if not self.connected:
            raise Exception("API not connected")
        
        # Simulate account balances
        return {
            'XRP': {'free': 10000.0, 'used': 100.0, 'total': 10100.0},
            'USDT': {'free': 5000.0, 'used': 50.0, 'total': 5050.0},
            'USDC': {'free': 5000.0, 'used': 50.0, 'total': 5050.0}
        }
    
    def create_order(self, symbol, order_type, side, amount, price=None):
        """Create a trading order"""
        if not self.connected:
            raise Exception("API not connected")
        
        # Simulate order creation
        order_id = f"sim_{int(time.time())}_{random.randint(1000, 9999)}"
        
        # Simulate small chance of order failure
        if random.random() < 0.05:  # 5% chance of failure
            raise Exception("Order creation failed (simulated)")
        
        order = {
            'id': order_id,
            'symbol': symbol,
            'type': order_type,
            'side': side,
            'amount': amount,
            'price': price,
            'status': 'open',
            'timestamp': datetime.utcnow().timestamp() * 1000
        }
        
        # Simulate immediate execution for market orders
        if order_type == 'market':
            order['status'] = 'closed'
            ticker = self.get_ticker(symbol)
            order['price'] = ticker['last']
        
        self.logger.info(f"Created order: {order_id} for {amount} {symbol}")
        return order
    
    def get_order_status(self, order_id, symbol):
        """Get order status"""
        if not self.connected:
            raise Exception("API not connected")
        
        # Simulate order completion after short delay
        return {
            'id': order_id,
            'status': 'closed',
            'filled': True,
            'timestamp': datetime.utcnow().timestamp() * 1000
        }
    
    def cancel_order(self, order_id, symbol):
        """Cancel an order"""
        if not self.connected:
            raise Exception("API not connected")
        
        self.logger.info(f"Cancelled order: {order_id}")
        return {'id': order_id, 'status': 'cancelled'}
