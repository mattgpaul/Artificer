import logging
import sys

class ColoredFormatter(logging.Formatter):
    """Add colors to log levels"""

    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[90m',    # Grey
        'INFO': '\033[32m',     # Green  
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
        'RESET': '\033[0m'      # Reset to normal
    }

    def format(self, record):
        # Format timestamp
        timestamp = self.formatTime(record, self.datefmt)
        
        # Add color only to log level
        color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        reset = self.COLORS['RESET']
        colored_level = f"{color}{record.levelname:<8}{reset}"
        
        # Build message with pipe separators and alignment
        return f"{timestamp} | {colored_level} | {record.name} | {record.getMessage()}"

def _setup_global_logging():
    """Automatically configure logging when this module loads"""
    import os
    root_logger = logging.getLogger()
    
    # Only setup once
    if not root_logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = ColoredFormatter(
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        root_logger.addHandler(handler)
        
        # Set log level from environment variable or default to INFO
        log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
        level = getattr(logging, log_level, logging.INFO)
        root_logger.setLevel(level)
        
        # Also set level on all existing loggers
        for name in logging.root.manager.loggerDict:
            logging.getLogger(name).setLevel(level)

# This runs automatically when anyone imports this module
_setup_global_logging()

def get_logger(name: str) -> logging.Logger:
    """Get a colored logger - setup is automatic"""
    logger = logging.getLogger(name)
    
    # Set log level from environment variable each time
    import os
    log_level = os.getenv('LOG_LEVEL', 'INFO').upper() 
    level = getattr(logging, log_level, logging.INFO)
    logger.setLevel(level)
    
    return logger
