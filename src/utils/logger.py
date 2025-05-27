import logging
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

def setup_logger(
    name: str,
    level: int = logging.INFO,
    log_file: Optional[Path] = None,
    console_output: bool = True
) -> logging.Logger:
    """Set up and configure a logger.
    
    Args:
        name (str): Name of the logger
        level (int): Logging level (default: INFO)
        log_file (Optional[Path]): Path to log file (default: None)
        console_output (bool): Whether to output to console (default: True)
        
    Returns:
        logging.Logger: Configured logger instance
    """
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Clear any existing handlers
    logger.handlers = []
    
    # Create formatters
    console_formatter = CustomFormatter(
        '%(asctime)s | %(levelname)s | %(name)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    file_formatter = logging.Formatter(
        '%(asctime)s | %(levelname)s | %(name)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Add console handler if requested
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
    
    # Add file handler if log_file is provided
    if log_file:
        # Create log directory if it doesn't exist
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    
    return logger

def get_logger(
    name: str,
    level: int = logging.INFO,
    log_dir: Optional[Path] = None
) -> logging.Logger:
    """Get a configured logger instance.
    
    Args:
        name (str): Name of the logger
        level (int): Logging level (default: INFO)
        log_dir (Optional[Path]): Directory for log files (default: None)
        
    Returns:
        logging.Logger: Configured logger instance
    """
    # Set up log file path if log_dir is provided
    log_file = None
    if log_dir:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_file = log_dir / f"{name}_{timestamp}.log"
    
    return setup_logger(name, level, log_file)

# Example usage:
if __name__ == "__main__":
    # Create a logger for testing
    test_logger = get_logger(
        "test",
        level=logging.DEBUG,
        log_dir=Path("logs")
    )
    
    # Test different log levels
    test_logger.debug("This is a debug message")
    test_logger.info("This is an info message")
    test_logger.warning("This is a warning message")
    test_logger.error("This is an error message")
    test_logger.critical("This is a critical message")
