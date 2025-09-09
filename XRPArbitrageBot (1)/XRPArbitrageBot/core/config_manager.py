import logging
from app import db
from models import TradingConfig

class ConfigManager:
    """Configuration management for trading system"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._ensure_default_config()
    
    def _ensure_default_config(self):
        """Ensure default configuration exists"""
        try:
            config = TradingConfig.query.first()
            if not config:
                default_config = TradingConfig(
                    spread_threshold=0.003,
                    trade_amount=100.0,
                    daily_max_volume=5000.0,
                    risk_buffer=0.1,
                    max_pending_orders=3
                )
                db.session.add(default_config)
                db.session.commit()
                self.logger.info("Created default trading configuration")
        except Exception as e:
            self.logger.error(f"Error ensuring default config: {e}")
            db.session.rollback()
    
    def get_config(self):
        """Get current trading configuration"""
        try:
            config = TradingConfig.query.first()
            if not config:
                self._ensure_default_config()
                config = TradingConfig.query.first()
            
            return config
        except Exception as e:
            self.logger.error(f"Error getting config: {e}")
            return None
    
    def update_config(self, config_data):
        """Update trading configuration"""
        try:
            config = TradingConfig.query.first()
            if not config:
                config = TradingConfig()
                db.session.add(config)
            
            # Update configuration fields
            if 'spread_threshold' in config_data:
                config.spread_threshold = float(config_data['spread_threshold'])
            
            if 'trade_amount' in config_data:
                config.trade_amount = float(config_data['trade_amount'])
            
            if 'daily_max_volume' in config_data:
                config.daily_max_volume = float(config_data['daily_max_volume'])
            
            if 'risk_buffer' in config_data:
                config.risk_buffer = float(config_data['risk_buffer'])
            
            if 'max_pending_orders' in config_data:
                config.max_pending_orders = int(config_data['max_pending_orders'])
            
            db.session.commit()
            self.logger.info("Configuration updated successfully")
            
            return config
            
        except Exception as e:
            self.logger.error(f"Error updating config: {e}")
            db.session.rollback()
            return None
    
    def get_config_dict(self):
        """Get configuration as dictionary"""
        try:
            config = self.get_config()
            if not config:
                return {}
            
            return {
                'spread_threshold': config.spread_threshold,
                'trade_amount': config.trade_amount,
                'daily_max_volume': config.daily_max_volume,
                'risk_buffer': config.risk_buffer,
                'max_pending_orders': config.max_pending_orders,
                'updated_at': config.updated_at.isoformat() if config.updated_at else None
            }
            
        except Exception as e:
            self.logger.error(f"Error getting config dict: {e}")
            return {}
    
    def validate_config(self, config_data):
        """Validate configuration parameters"""
        errors = []
        
        try:
            # Validate spread threshold
            if 'spread_threshold' in config_data:
                threshold = float(config_data['spread_threshold'])
                if threshold <= 0 or threshold >= 0.1:
                    errors.append("Spread threshold must be between 0 and 0.1 (10%)")
            
            # Validate trade amount
            if 'trade_amount' in config_data:
                amount = float(config_data['trade_amount'])
                if amount <= 0 or amount > 10000:
                    errors.append("Trade amount must be between 0 and 10,000 XRP")
            
            # Validate daily max volume
            if 'daily_max_volume' in config_data:
                volume = float(config_data['daily_max_volume'])
                if volume <= 0 or volume > 100000:
                    errors.append("Daily max volume must be between 0 and 100,000 XRP")
            
            # Validate risk buffer
            if 'risk_buffer' in config_data:
                buffer = float(config_data['risk_buffer'])
                if buffer < 0 or buffer > 0.5:
                    errors.append("Risk buffer must be between 0 and 0.5 (50%)")
            
            # Validate max pending orders
            if 'max_pending_orders' in config_data:
                max_orders = int(config_data['max_pending_orders'])
                if max_orders < 1 or max_orders > 10:
                    errors.append("Max pending orders must be between 1 and 10")
            
            # Cross-validation: trade amount vs daily volume
            if ('trade_amount' in config_data and 'daily_max_volume' in config_data):
                trade_amount = float(config_data['trade_amount'])
                daily_volume = float(config_data['daily_max_volume'])
                if trade_amount > daily_volume:
                    errors.append("Trade amount cannot exceed daily max volume")
            
        except ValueError as e:
            errors.append(f"Invalid number format: {e}")
        except Exception as e:
            errors.append(f"Validation error: {e}")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors
        }
    
    def reset_to_defaults(self):
        """Reset configuration to default values"""
        try:
            config = TradingConfig.query.first()
            if config:
                db.session.delete(config)
            
            self._ensure_default_config()
            self.logger.info("Configuration reset to defaults")
            
            return self.get_config()
            
        except Exception as e:
            self.logger.error(f"Error resetting config: {e}")
            db.session.rollback()
            return None
    
    def get_config_history(self, limit=10):
        """Get configuration change history"""
        try:
            # This would require a config history table in a real implementation
            # For now, return the current config
            configs = TradingConfig.query.order_by(TradingConfig.updated_at.desc()).limit(limit).all()
            
            history = []
            for config in configs:
                history.append({
                    'id': config.id,
                    'spread_threshold': config.spread_threshold,
                    'trade_amount': config.trade_amount,
                    'daily_max_volume': config.daily_max_volume,
                    'risk_buffer': config.risk_buffer,
                    'max_pending_orders': config.max_pending_orders,
                    'updated_at': config.updated_at.isoformat() if config.updated_at else None
                })
            
            return history
            
        except Exception as e:
            self.logger.error(f"Error getting config history: {e}")
            return []
