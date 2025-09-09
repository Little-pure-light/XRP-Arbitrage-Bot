import os
import time
import logging
from datetime import datetime, timedelta
from cryptography.fernet import Fernet
from collections import defaultdict
from app import db
from models import SystemLog

class SecurityManager:
    """Security management for API keys, rate limiting, and access control"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.encryption_key = self._get_or_create_encryption_key()
        self.fernet = Fernet(self.encryption_key)
        
        # Rate limiting
        self.rate_limits = defaultdict(list)
        self.failed_attempts = defaultdict(int)
        
        # API usage tracking
        self.api_call_counts = defaultdict(int)
        self.api_call_windows = defaultdict(list)
    
    def _get_or_create_encryption_key(self):
        """Get or create encryption key for API credentials"""
        try:
            # Try to get existing key from environment
            key = os.environ.get('ENCRYPTION_KEY')
            
            if not key:
                # Generate new key
                key = Fernet.generate_key().decode()
                self.logger.warning("Generated new encryption key - store this securely!")
                self.logger.warning(f"ENCRYPTION_KEY={key}")
                
                # Try to save to environment (this won't persist across restarts)
                os.environ['ENCRYPTION_KEY'] = key
            
            return key.encode()
            
        except Exception as e:
            self.logger.error(f"Error handling encryption key: {e}")
            # Fallback key (not secure for production)
            return Fernet.generate_key()
    
    def encrypt_api_credentials(self, api_key, api_secret):
        """Encrypt API credentials for secure storage"""
        try:
            encrypted_key = self.fernet.encrypt(api_key.encode()).decode()
            encrypted_secret = self.fernet.encrypt(api_secret.encode()).decode()
            
            return {
                'encrypted_key': encrypted_key,
                'encrypted_secret': encrypted_secret,
                'encryption_key': self.encryption_key.decode()
            }
            
        except Exception as e:
            self.logger.error(f"Error encrypting API credentials: {e}")
            return None
    
    def decrypt_api_credentials(self, encrypted_key, encrypted_secret):
        """Decrypt API credentials"""
        try:
            api_key = self.fernet.decrypt(encrypted_key.encode()).decode()
            api_secret = self.fernet.decrypt(encrypted_secret.encode()).decode()
            
            return api_key, api_secret
            
        except Exception as e:
            self.logger.error(f"Error decrypting API credentials: {e}")
            return None, None
    
    def check_rate_limit(self, identifier, max_requests=60, window_seconds=60):
        """Check if request is within rate limits"""
        try:
            current_time = time.time()
            
            # Clean old requests
            cutoff_time = current_time - window_seconds
            self.rate_limits[identifier] = [
                req_time for req_time in self.rate_limits[identifier]
                if req_time > cutoff_time
            ]
            
            # Check if under limit
            if len(self.rate_limits[identifier]) >= max_requests:
                self.logger.warning(f"Rate limit exceeded for {identifier}")
                return False
            
            # Add current request
            self.rate_limits[identifier].append(current_time)
            return True
            
        except Exception as e:
            self.logger.error(f"Error checking rate limit: {e}")
            return True  # Allow on error
    
    def track_api_usage(self, api_endpoint, response_code):
        """Track API usage for monitoring"""
        try:
            current_time = time.time()
            
            # Track usage
            self.api_call_counts[api_endpoint] += 1
            self.api_call_windows[api_endpoint].append({
                'timestamp': current_time,
                'response_code': response_code
            })
            
            # Clean old data (keep 1 hour)
            cutoff_time = current_time - 3600
            self.api_call_windows[api_endpoint] = [
                call for call in self.api_call_windows[api_endpoint]
                if call['timestamp'] > cutoff_time
            ]
            
            # Log errors
            if response_code >= 400:
                self.failed_attempts[api_endpoint] += 1
                
                # Alert on high error rate
                recent_calls = [
                    call for call in self.api_call_windows[api_endpoint]
                    if call['timestamp'] > current_time - 300  # Last 5 minutes
                ]
                
                if recent_calls:
                    error_rate = len([c for c in recent_calls if c['response_code'] >= 400]) / len(recent_calls)
                    
                    if error_rate > 0.5:  # More than 50% errors
                        self.logger.critical(f"High API error rate for {api_endpoint}: {error_rate:.1%}")
                        self._log_security_event('HIGH_API_ERROR_RATE', f'{api_endpoint}: {error_rate:.1%}')
            
        except Exception as e:
            self.logger.error(f"Error tracking API usage: {e}")
    
    def validate_api_key_format(self, api_key):
        """Validate API key format"""
        try:
            # Basic validation
            if not api_key or len(api_key) < 10:
                return False
            
            # Check for demo/test keys
            demo_indicators = ['demo', 'test', 'fake', 'sample']
            if any(indicator in api_key.lower() for indicator in demo_indicators):
                self.logger.warning("Demo/test API key detected")
                return True  # Allow demo keys
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error validating API key: {e}")
            return False
    
    def check_suspicious_activity(self):
        """Check for suspicious API usage patterns"""
        try:
            alerts = []
            current_time = time.time()
            
            # Check for excessive failed requests
            for endpoint, attempts in self.failed_attempts.items():
                if attempts > 20:  # More than 20 failed attempts
                    alerts.append(f"Excessive failures for {endpoint}: {attempts}")
            
            # Check for unusual API usage patterns
            for endpoint, calls in self.api_call_windows.items():
                recent_calls = [
                    call for call in calls
                    if call['timestamp'] > current_time - 300  # Last 5 minutes
                ]
                
                if len(recent_calls) > 100:  # More than 100 calls in 5 minutes
                    alerts.append(f"High API usage for {endpoint}: {len(recent_calls)} calls in 5 min")
            
            # Log alerts
            for alert in alerts:
                self.logger.warning(f"Security alert: {alert}")
                self._log_security_event('SUSPICIOUS_ACTIVITY', alert)
            
            return alerts
            
        except Exception as e:
            self.logger.error(f"Error checking suspicious activity: {e}")
            return []
    
    def _log_security_event(self, event_type, details):
        """Log security event to database"""
        try:
            log_entry = SystemLog(
                level='WARNING',
                message=f'Security Event: {event_type}',
                module='SecurityManager',
                error_details=details
            )
            
            db.session.add(log_entry)
            db.session.commit()
            
        except Exception as e:
            self.logger.error(f"Error logging security event: {e}")
    
    def get_security_status(self):
        """Get overall security status"""
        try:
            current_time = time.time()
            
            # Calculate metrics
            total_api_calls = sum(self.api_call_counts.values())
            total_failures = sum(self.failed_attempts.values())
            
            recent_alerts = self.check_suspicious_activity()
            
            # Rate limiting status
            active_rate_limits = len([
                identifier for identifier, times in self.rate_limits.items()
                if any(t > current_time - 60 for t in times)
            ])
            
            return {
                'encryption_enabled': True,
                'total_api_calls': total_api_calls,
                'total_failures': total_failures,
                'error_rate': (total_failures / total_api_calls * 100) if total_api_calls > 0 else 0,
                'active_rate_limits': active_rate_limits,
                'recent_alerts': recent_alerts,
                'secure': len(recent_alerts) == 0,
                'last_check': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error getting security status: {e}")
            return {
                'encryption_enabled': False,
                'secure': False,
                'error': str(e),
                'last_check': datetime.utcnow().isoformat()
            }
    
    def reset_security_counters(self):
        """Reset security counters (for maintenance)"""
        try:
            self.rate_limits.clear()
            self.failed_attempts.clear()
            self.api_call_counts.clear()
            self.api_call_windows.clear()
            
            self.logger.info("Security counters reset")
            self._log_security_event('COUNTERS_RESET', 'All security counters have been reset')
            
        except Exception as e:
            self.logger.error(f"Error resetting security counters: {e}")
    
    def generate_api_key_instructions(self):
        """Generate instructions for securing API keys"""
        return {
            'steps': [
                '1. Create MEXC API key with only spot trading permissions',
                '2. Whitelist your server IP address',
                '3. Enable only necessary permissions (no withdrawals)',
                '4. Set up environment variables for encrypted storage',
                '5. Test with small amounts first'
            ],
            'environment_variables': {
                'MEXC_API_KEY_ENCRYPTED': 'Your encrypted API key',
                'MEXC_API_SECRET_ENCRYPTED': 'Your encrypted API secret',
                'MEXC_ENCRYPTION_KEY': 'Encryption key for security'
            },
            'security_tips': [
                'Never share your API keys',
                'Monitor API usage regularly',
                'Set up IP whitelisting',
                'Use minimum required permissions',
                'Enable 2FA on your exchange account'
            ]
        }