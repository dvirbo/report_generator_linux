"""
Configuration Loader
Loads and validates configuration from config.ini
"""

import configparser
import os
from pathlib import Path
from typing import Dict, Any, Optional

try:
    import keyring
    KEYRING_AVAILABLE = True
except ImportError:
    KEYRING_AVAILABLE = False


class ConfigLoader:
    """
    Load and manage configuration
    
    >>> import tempfile
    >>> import configparser
    >>> from pathlib import Path
    >>> 
    >>> # Create a temporary config file for testing
    >>> with tempfile.NamedTemporaryFile(mode='w', suffix='.ini', delete=False) as f:
    ...     f.write('''[database]
    ... host = localhost
    ... port = 1521
    ... service_name = testdb
    ... username = testuser
    ... password = testpass
    ... 
    ... [email]
    ... smtp_server = smtp.example.com
    ... smtp_port = 587
    ... smtp_use_tls = True
    ... smtp_username = email@example.com
    ... smtp_password = emailpass
    ... from_email = sender@example.com
    ... from_name = Test Sender
    ... 
    ... [logging]
    ... level = INFO
    ... file_path = logs/test.log
    ... 
    ... [files]
    ... temp_directory = temp
    ... csv_encoding = utf-8-sig
    ... ''')
    ...     config_path = f.name
    ... 
    >>> try:
    ...     loader = ConfigLoader(config_path=config_path)
    ...     
    ...     # Test database config retrieval
    ...     db_config = loader.get_database_config()
    ...     db_config['host'] == 'localhost'
    ...     True
    ...     db_config['port'] == 1521
    ...     True
    ...     db_config['service_name'] == 'testdb'
    ...     True
    ...     
    ...     # Test email config retrieval
    ...     email_config = loader.get_email_config()
    ...     email_config['smtp_server'] == 'smtp.example.com'
    ...     True
    ...     email_config['smtp_port'] == 587
    ...     True
    ...     email_config['from_email'] == 'sender@example.com'
    ...     True
    ...     
    ...     # Test logging config retrieval
    ...     log_config = loader.get_logging_config()
    ...     log_config['level'] == 'INFO'
    ...     True
    ...     
    ...     # Test files config retrieval
    ...     files_config = loader.get_files_config()
    ...     files_config['temp_directory'] == 'temp'
    ...     True
    ...     files_config['csv_encoding'] == 'utf-8-sig'
    ...     True
    ...     
    ... finally:
    ...     # Cleanup
    ...     Path(config_path).unlink()
    """

    def __init__(self, config_path: str = None):
        """
        Initialize configuration loader
        
        Args:
            config_path: Path to config.ini file. If None, looks for config.ini in current directory.
        """
        if config_path is None:
            # Look for config.ini in current directory or parent directory
            current_dir = Path(__file__).parent.parent.parent
            config_path = current_dir / "config.ini"
        
        self.config_path = Path(config_path)
        self.config = configparser.ConfigParser()
        self._load_config()

    def _load_config(self):
        """Load configuration from file"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
        
        self.config.read(self.config_path, encoding='utf-8')

    def _resolve_secret(self, value: Optional[str]) -> Optional[str]:
        """
        Resolve secret value from keyring if it uses KEYRING: token format
        
        Args:
            value: Configuration value that may be a KEYRING: token
        
        Returns:
            Resolved secret value or original value if not a KEYRING token
        """
        if not value or not value.strip().startswith("KEYRING:"):
            return value
        
        if not KEYRING_AVAILABLE:
            raise ImportError(
                "keyring library is required for KEYRING: tokens. "
                "Install it with: pip install keyring"
            )
        
        # Parse KEYRING:service/account format
        token = value.strip().replace("KEYRING:", "", 1)
        parts = token.split("/", 1)
        
        if len(parts) != 2:
            raise ValueError(
                f"Invalid KEYRING token format: {value}. "
                "Expected format: KEYRING:service/account"
            )
        
        service, account = parts[0].strip(), parts[1].strip()
        
        if not service or not account:
            raise ValueError(
                f"Invalid KEYRING token format: {value}. "
                "Service and account must be non-empty"
            )
        
        secret = keyring.get_password(service, account)
        
        if secret is None:
            raise ValueError(
                f"No keyring entry found for service='{service}' account='{account}'. "
                f"Set it with: python tools/keyring_secrets.py set {account}"
            )
        
        return secret

    def get(self, section: str, key: str, fallback: Any = None) -> str:
        """Get configuration value (with keyring resolution if needed)"""
        raw_value = self.config.get(section, key, fallback=fallback)
        if raw_value is None:
            return None
        return self._resolve_secret(str(raw_value))

    def getint(self, section: str, key: str, fallback: int = None) -> int:
        """Get integer configuration value"""
        return self.config.getint(section, key, fallback=fallback)

    def getboolean(self, section: str, key: str, fallback: bool = None) -> bool:
        """Get boolean configuration value"""
        return self.config.getboolean(section, key, fallback=fallback)

    def get_database_config(self) -> Dict[str, Any]:
        """Get database configuration"""
        return {
            'host': self.get('database', 'host'),
            'port': self.getint('database', 'port', 1521),
            'service_name': self.get('database', 'service_name'),
            'username': self.get('database', 'username'),
            'password': self.get('database', 'password'),
            'connection_timeout': self.getint('database', 'connection_timeout', 30),
            'command_timeout': self.getint('database', 'command_timeout', 300),
        }

    def get_email_config(self) -> Dict[str, Any]:
        """Get email configuration"""
        return {
            'smtp_server': self.get('email', 'smtp_server'),
            'smtp_port': self.getint('email', 'smtp_port', 587),
            'smtp_use_tls': self.getboolean('email', 'smtp_use_tls', True),
            'smtp_username': self.get('email', 'smtp_username'),
            'smtp_password': self.get('email', 'smtp_password'),
            'from_email': self.get('email', 'from_email'),
            'from_name': self.get('email', 'from_name'),
            'max_email_size_kb': self.getint('email', 'max_email_size_kb', 10240),
        }

    def get_logging_config(self) -> Dict[str, Any]:
        """Get logging configuration"""
        return {
            'level': self.get('logging', 'level', 'INFO'),
            'file_path': self.get('logging', 'file_path', 'logs/report_generator.log'),
            'file_size_mb': self.getint('logging', 'file_size_mb', 100),
            'backup_count': self.getint('logging', 'backup_count', 30),
            'log_to_database': self.getboolean('logging', 'log_to_database', True),
            'log_to_file': self.getboolean('logging', 'log_to_file', True),
            'log_to_console': self.getboolean('logging', 'log_to_console', True),
        }

    def get_files_config(self) -> Dict[str, Any]:
        """Get file management configuration"""
        return {
            'temp_directory': self.get('files', 'temp_directory', 'temp'),
            'csv_encoding': self.get('files', 'csv_encoding', 'utf-8-sig'),
            'cleanup_temp_files': self.getboolean('files', 'cleanup_temp_files', True),
        }


