import logging
from pathlib import Path
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional

class CustomFormatter(logging.Formatter):
    """Custom formatter with colors and detailed formatting."""
    
    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',     # Cyan
        'INFO': '\033[32m',      # Green
        'WARNING': '\033[33m',   # Yellow
        'ERROR': '\033[31m',     # Red
        'CRITICAL': '\033[41m',  # Red background
        'RESET': '\033[0m'       # Reset
    }

    def format(self, record: logging.LogRecord) -> str:
        """Format the log record with colors and custom formatting."""
        # Add color to level name
        levelname = record.levelname
        if levelname in self.COLORS:
            record.levelname = f"{self.COLORS[levelname]}{levelname}{self.COLORS['RESET']}"
        
        # Format the message
        return super().format(record)

class SystemLogger:
    """Singleton logger class to ensure all modules write to the same log file."""
    _instance = None
    _initialized = False
    _log_file = None
    _logger = None
    _DEFAULT_LOG_DIR = Path('./logs')
    _config = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SystemLogger, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._initialized:
            self._initialized = True
            self._setup_logger()

    def _get_config(self):
        """Lazy load the Config class to avoid circular imports."""
        if self._config is None:
            from src.utils.config import Config
            self._config = Config()
        return self._config

    def _get_log_level(self) -> int:
        """Get the appropriate log level based on environment."""
        config = self._get_config()
        return logging.DEBUG if config.is_test else logging.INFO

    def _setup_logger(self):
        """Set up the system logger with a new log file."""
        # Create logs directory if it doesn't exist
        self._DEFAULT_LOG_DIR.mkdir(parents=True, exist_ok=True)

        # Create a new log file with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self._log_file = self._DEFAULT_LOG_DIR / f"system_{timestamp}.log"

        # Create logger
        self._logger = logging.getLogger('system')
        self._logger.setLevel(self._get_log_level())
        
        # Clear any existing handlers
        self._logger.handlers = []
        
        # Create formatters
        console_formatter = CustomFormatter(
            '%(asctime)s | %(levelname)s | %(name)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        file_formatter = logging.Formatter(
            '%(asctime)s | %(levelname)s | %(name)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Add console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(console_formatter)
        self._logger.addHandler(console_handler)
        
        # Add file handler
        file_handler = logging.FileHandler(self._log_file)
        file_handler.setFormatter(file_formatter)
        self._logger.addHandler(file_handler)
        
        # Log the initialization
        config = self._get_config()
        self._logger.info(f"Logger initialized in {config.env} environment. Log file: {self._log_file}")

    @property
    def logger(self) -> logging.Logger:
        """Get the system logger instance."""
        return self._logger

    @property
    def log_file(self) -> Path:
        """Get the current log file path."""
        return self._log_file

    @property
    def log_dir(self) -> Path:
        """Get the log directory path."""
        return self._DEFAULT_LOG_DIR

def get_logger(name: str) -> logging.Logger:
    """Get a logger instance that writes to the system log file.
    
    Args:
        name (str): Name of the logger/module
        
    Returns:
        logging.Logger: Configured logger instance
    """
    # Get the system logger instance
    system_logger = SystemLogger()
    
    # Create a new logger with the module name
    logger = logging.getLogger(name)
    logger.setLevel(system_logger.logger.level)  # Use the same level as system logger
    
    # Clear any existing handlers
    logger.handlers = []
    
    # Add the same handlers as the system logger
    for handler in system_logger.logger.handlers:
        logger.addHandler(handler)
    
    return logger

# Example usage:
if __name__ == "__main__":
    # Create loggers for different modules
    test_logger1 = get_logger("module1")
    test_logger2 = get_logger("module2")
    
    # Test different log levels
    test_logger1.debug("This is a debug message from module1")
    test_logger1.info("This is an info message from module1")
    test_logger2.warning("This is a warning message from module2")
    test_logger2.error("This is an error message from module2")
    test_logger1.critical("This is a critical message from module1")
