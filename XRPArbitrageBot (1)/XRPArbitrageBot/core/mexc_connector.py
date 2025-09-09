import os
import time
import hmac
import hashlib
import requests
import logging
from datetime import datetime
from cryptography.fernet import Fernet
from core.api_connector import APIConnector

class MEXCConnector(APIConnector):
    """MEXC Exchange-specific API connector with advanced features"""
    
    def __init__(self):
        super().__init__()
        self.base_url = 'https://api.mexc.com'
        self.ws_url = 'wss://wbs.mexc.com/ws'
        self.exchange_name = 'MEXC'
        self.logger = logging.getLogger(__name__)
        
        # MEXC-specific configuration
        self.rate_limits = {
            'orders': 20,  # Orders per second
            'general': 10,  # General API calls per second
            'market_data': 50  # Market data calls per second
        }
        
        self.trading_fees = {
            'maker': 0.0002,  # 0.02%
            'taker': 0.0006   # 0.06%
        }
        
        # Security
        self.encrypted_credentials = None
        self._load_encrypted_credentials()
        
        # Rate limiting
        self._last_request_time = {}
        self._request_counts = {}
        
    def _load_encrypted_credentials(self):
        """Load encrypted API credentials"""
        try:
            # Check for encrypted credentials in environment
            encrypted_key = os.environ.get('MEXC_API_KEY_ENCRYPTED')
            encrypted_secret = os.environ.get('MEXC_API_SECRET_ENCRYPTED')
            encryption_key = os.environ.get('MEXC_ENCRYPTION_KEY')
            
            if encrypted_key and encrypted_secret and encryption_key:
                fernet = Fernet(encryption_key.encode())
                self.api_key = fernet.decrypt(encrypted_key.encode()).decode()
                self.api_secret = fernet.decrypt(encrypted_secret.encode()).decode()
                self.logger.info("Encrypted MEXC credentials loaded successfully")
            else:
                # Fallback to plain text (development mode)
                self.api_key = os.environ.get('MEXC_API_KEY', 'demo_key')
                self.api_secret = os.environ.get('MEXC_API_SECRET', 'demo_secret')
                self.logger.warning("Using plain text credentials (development mode)")
                
        except Exception as e:
            self.logger.error(f"Error loading MEXC credentials: {e}")
            self.api_key = 'demo_key'
            self.api_secret = 'demo_secret'
    
    def connect(self):
        """Connect to MEXC API with enhanced validation"""
        try:
            # Test connectivity
            response = self._make_request('GET', '/api/v3/ping')
            
            if response.status_code == 200:
                self.connected = True
                self.logger.info("Connected to MEXC API successfully")
                
                # Test authentication if credentials are provided
                if self.api_key != 'demo_key':
                    self._test_authentication()
                    
                return True
            else:
                self.logger.error(f"MEXC API connection failed: {response.status_code}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error connecting to MEXC API: {e}")
            return False
    
    def _test_authentication(self):
        """Test API authentication"""
        try:
            # Get account information to test auth
            response = self._make_authenticated_request('GET', '/api/v3/account')
            
            if response.status_code == 200:
                self.authenticated = True
                self.logger.info("MEXC API authentication successful")
            else:
                self.logger.error(f"MEXC API authentication failed: {response.status_code}")
                
        except Exception as e:
            self.logger.error(f"Error testing MEXC authentication: {e}")
    
    def _make_authenticated_request(self, method, endpoint, params=None):
        """Make authenticated request with MEXC signature"""
        try:
            if not params:
                params = {}
            
            # Add timestamp
            timestamp = int(time.time() * 1000)
            params['timestamp'] = timestamp
            
            # Create query string
            query_string = '&'.join([f"{key}={value}" for key, value in sorted(params.items())])
            
            # Create signature
            signature = hmac.new(
                self.api_secret.encode(),
                query_string.encode(),
                hashlib.sha256
            ).hexdigest()
            
            params['signature'] = signature
            
            # Add API key to headers
            headers = {
                'X-MEXC-APIKEY': self.api_key,
                'Content-Type': 'application/json'
            }
            
            return self._make_request(method, endpoint, params, headers)
            
        except Exception as e:
            self.logger.error(f"Error making authenticated MEXC request: {e}")
            return None
    
    def _make_request(self, method, endpoint, params=None, headers=None):
        """Make rate-limited request to MEXC API"""
        try:
            # Apply rate limiting
            if not self._check_rate_limit(endpoint):
                time.sleep(0.1)  # Brief pause if rate limited
            
            url = f"{self.base_url}{endpoint}"
            
            if method == 'GET':
                response = requests.get(url, params=params, headers=headers, timeout=10)
            elif method == 'POST':
                response = requests.post(url, json=params, headers=headers, timeout=10)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            # Update rate limiting counters
            self._update_rate_limit_counters(endpoint)
            
            return response
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"MEXC API request error: {e}")
            raise
    
    def _check_rate_limit(self, endpoint):
        """Check if request would exceed rate limits"""
        current_time = time.time()
        
        # Determine rate limit category
        if '/order' in endpoint:
            category = 'orders'
        elif '/ticker' in endpoint or '/depth' in endpoint:
            category = 'market_data'
        else:
            category = 'general'
        
        limit = self.rate_limits[category]
        
        # Check if we have recent requests in this category
        if category not in self._request_counts:
            self._request_counts[category] = []
        
        # Remove old requests (older than 1 second)
        self._request_counts[category] = [
            req_time for req_time in self._request_counts[category]
            if current_time - req_time < 1.0
        ]
        
        # Check if we're under the limit
        return len(self._request_counts[category]) < limit
    
    def _update_rate_limit_counters(self, endpoint):
        """Update rate limiting counters"""
        current_time = time.time()
        
        # Determine category
        if '/order' in endpoint:
            category = 'orders'
        elif '/ticker' in endpoint or '/depth' in endpoint:
            category = 'market_data'
        else:
            category = 'general'
        
        if category not in self._request_counts:
            self._request_counts[category] = []
        
        self._request_counts[category].append(current_time)
    
    def create_order(self, symbol, order_type, side, amount, price=None):
        """Create order with MEXC-specific parameters"""
        try:
            if not self.authenticated:
                return self._simulate_order(symbol, order_type, side, amount, price)
            
            params = {
                'symbol': symbol.replace('/', ''),  # MEXC format: XRPUSDT
                'side': side.upper(),
                'type': order_type.upper(),
                'quantity': str(amount),
                'timeInForce': 'IOC'  # Immediate or Cancel for arbitrage
            }
            
            if price:
                params['price'] = str(price)
            
            response = self._make_authenticated_request('POST', '/api/v3/order', params)
            
            if response and response.status_code == 200:
                order_data = response.json()
                return {
                    'id': order_data.get('orderId'),
                    'symbol': symbol,
                    'side': side,
                    'amount': amount,
                    'price': price or order_data.get('price', 0),
                    'status': 'pending',
                    'timestamp': datetime.utcnow().isoformat()
                }
            else:
                self.logger.error(f"MEXC order creation failed: {response.status_code if response else 'No response'}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error creating MEXC order: {e}")
            return None
    
    def get_order_status(self, order_id, symbol):
        """Get order status from MEXC"""
        try:
            if not self.authenticated:
                return self._simulate_order_status(order_id)
            
            params = {
                'symbol': symbol.replace('/', ''),
                'orderId': order_id
            }
            
            response = self._make_authenticated_request('GET', '/api/v3/order', params)
            
            if response and response.status_code == 200:
                order_data = response.json()
                return {
                    'id': order_data.get('orderId'),
                    'status': self._map_mexc_status(order_data.get('status')),
                    'filled_amount': float(order_data.get('executedQty', 0)),
                    'price': float(order_data.get('price', 0))
                }
            else:
                return {'status': 'unknown'}
                
        except Exception as e:
            self.logger.error(f"Error getting MEXC order status: {e}")
            return {'status': 'error'}
    
    def _map_mexc_status(self, mexc_status):
        """Map MEXC order status to our standard format"""
        status_map = {
            'NEW': 'pending',
            'PARTIALLY_FILLED': 'partial',
            'FILLED': 'closed',
            'CANCELED': 'cancelled',
            'REJECTED': 'rejected',
            'EXPIRED': 'expired'
        }
        return status_map.get(mexc_status, 'unknown')
    
    def cancel_order(self, order_id, symbol):
        """Cancel order on MEXC"""
        try:
            if not self.authenticated:
                return True  # Simulate success in demo mode
            
            params = {
                'symbol': symbol.replace('/', ''),
                'orderId': order_id
            }
            
            response = self._make_authenticated_request('DELETE', '/api/v3/order', params)
            
            return response and response.status_code == 200
            
        except Exception as e:
            self.logger.error(f"Error cancelling MEXC order: {e}")
            return False
    
    def get_market_data(self, symbol):
        """Get real-time market data from MEXC"""
        try:
            mexc_symbol = symbol.replace('/', '')
            response = self._make_request('GET', f'/api/v3/ticker/24hr', {'symbol': mexc_symbol})
            
            if response and response.status_code == 200:
                data = response.json()
                return {
                    'symbol': symbol,
                    'price': float(data.get('lastPrice', 0)),
                    'volume': float(data.get('volume', 0)),
                    'high': float(data.get('highPrice', 0)),
                    'low': float(data.get('lowPrice', 0)),
                    'change': float(data.get('priceChangePercent', 0)),
                    'timestamp': datetime.utcnow().isoformat()
                }
            else:
                return self._simulate_market_data(symbol)
                
        except Exception as e:
            self.logger.error(f"Error getting MEXC market data: {e}")
            return self._simulate_market_data(symbol)
    
    def get_account_balance(self):
        """Get account balance from MEXC"""
        try:
            if not self.authenticated:
                return self._simulate_balances()
            
            response = self._make_authenticated_request('GET', '/api/v3/account')
            
            if response and response.status_code == 200:
                account_data = response.json()
                balances = {}
                
                for balance in account_data.get('balances', []):
                    asset = balance.get('asset')
                    free = float(balance.get('free', 0))
                    locked = float(balance.get('locked', 0))
                    
                    if free > 0 or locked > 0:
                        balances[asset] = {
                            'free': free,
                            'locked': locked,
                            'total': free + locked
                        }
                
                return balances
            else:
                return self._simulate_balances()
                
        except Exception as e:
            self.logger.error(f"Error getting MEXC account balance: {e}")
            return self._simulate_balances()
    
    def get_trading_fees(self):
        """Get current trading fees"""
        return self.trading_fees
    
    def _simulate_balances(self):
        """Simulate account balances for testing"""
        return {
            'XRP': {'free': 10000.0, 'locked': 0.0, 'total': 10000.0},
            'USDT': {'free': 5000.0, 'locked': 0.0, 'total': 5000.0},
            'USDC': {'free': 5000.0, 'locked': 0.0, 'total': 5000.0}
        }