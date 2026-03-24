"""
Configuration Loader
Loads and validates configuration from config.ini
"""

import configparser
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List

# Import PasswordManager from secure_password_store
try:
    from secure_password_store.password_manager import PasswordManager
    PASSWORD_MANAGER_AVAILABLE = True
except ImportError:
    PASSWORD_MANAGER_AVAILABLE = False

logger = logging.getLogger(__name__)


class ConfigLoader:
    """
    Load and manage configuration
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
        
        # Initialize PasswordManager for secure password retrieval
        self._password_manager = None
        if PASSWORD_MANAGER_AVAILABLE:
            try:
                self._password_manager = PasswordManager()
                logger.debug("PasswordManager initialized successfully")
            except Exception as e:
                logger.warning(f"Failed to initialize PasswordManager: {e}. "
                             "Falling back to plain text passwords in config.")

    def _load_config(self):
        """Load configuration from file"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
        
        self.config.read(self.config_path, encoding='utf-8')

    def _get_secure_password(self, password_key: str) -> Optional[str]:
        """
        Retrieve password from secure_password_store using the given key
        
        Args:
            password_key: The identifier/key to look up in PasswordManager
        
        Returns:
            The decrypted password, or None if not found or PasswordManager unavailable
        """
        if not password_key:
            return None
        
        if not self._password_manager:
            logger.warning(f"PasswordManager not available, cannot retrieve password for key: {password_key}")
            return None
        
        try:
            password = self._password_manager.get_password(password_key)
            if password:
                logger.debug(f"Successfully retrieved password for key: {password_key}")
            else:
                logger.warning(f"No password found in secure store for key: {password_key}")
            return password
        except Exception as e:
            logger.error(f"Error retrieving password for key '{password_key}': {e}")
            return None

    def get(self, section: str, key: str, fallback: Any = None) -> str:
        """Get configuration value"""
        raw_value = self.config.get(section, key, fallback=fallback)
        if raw_value is None:
            return None
        return str(raw_value)

    def getint(self, section: str, key: str, fallback: int = None) -> int:
        """Get integer configuration value"""
        return self.config.getint(section, key, fallback=fallback)

    def getboolean(self, section: str, key: str, fallback: bool = None) -> bool:
        """Get boolean configuration value"""
        return self.config.getboolean(section, key, fallback=fallback)

    def get_database_config(self) -> Dict[str, Any]:
        """Get database configuration"""
        # Try to get password from secure store using password_key
        password = None
        password_key = self.get('database', 'password_key', fallback=None)
        if password_key:
            password = self._get_secure_password(password_key)
        
        # Fall back to plain text password if secure retrieval failed
        if not password:
            password = self.get('database', 'password', fallback=None)
            if password and password_key:
                logger.warning("Using fallback plain text password for database")
        
        port = self.getint('database', 'port', fallback=None)
        if port is None:
            raise ValueError(
                "[database] port must be set in config.ini for your environment "
                "(e.g. 1521 for dev, 1531 for UAT). Do not rely on code defaults."
            )
        return {
            'host': self.get('database', 'host'),
            'port': port,
            'service_name': self.get('database', 'service_name'),
            'username': self.get('database', 'username'),
            'password': password,
            'connection_timeout': self.getint('database', 'connection_timeout', 30),
            'command_timeout': self.getint('database', 'command_timeout', 300),
        }

    def get_email_config(self) -> Dict[str, Any]:
        """Get email configuration"""
        # Try to get SMTP password from secure store using smtp_password_key
        smtp_password = None
        smtp_password_key = self.get('email', 'smtp_password_key', fallback=None)
        if smtp_password_key:
            smtp_password = self._get_secure_password(smtp_password_key)
        
        # Fall back to plain text password if secure retrieval failed
        if not smtp_password:
            smtp_password = self.get('email', 'smtp_password', fallback=None)
            if smtp_password and smtp_password_key:
                logger.warning("Using fallback plain text password for SMTP")
        
        return {
            'smtp_server': self.get('email', 'smtp_server'),
            'smtp_port': self.getint('email', 'smtp_port', 587),
            'smtp_use_tls': self.getboolean('email', 'smtp_use_tls', True),
            'smtp_username': self.get('email', 'smtp_username'),
            'smtp_password': smtp_password,
            'smtp_require_auth': self.getboolean('email', 'smtp_require_auth', True),
            'from_email': self.get('email', 'from_email'),
            'from_name': self.get('email', 'from_name'),
            'max_email_size_kb': self.getint('email', 'max_email_size_kb', 10240),
            # Whether to attach the CSV file (HTML body still includes a table rendering)
            'attach_csv': self.getboolean('email', 'attach_csv', True),
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
    
    def get_manager_bu_list(self) -> List[str]:
        """
        Get list of BU identifiers that use manager-based processing
        
        Returns:
            List of BU identifier strings (e.g., ['461', '462', '463'])
        """
        bu_list_str = self.get('branches', 'manager_bu_list', '')
        if not bu_list_str:
            return []
        
        # Parse comma-separated list and strip whitespace
        bu_list = [bu.strip() for bu in bu_list_str.split(',') if bu.strip()]
        return bu_list


