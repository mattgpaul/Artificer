import logging
import sys

class ColoredFormatter(logging.Formatter):
    """Add colors to log levels"""

    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green  
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
        'RESET': '\033[0m'      # Reset to normal
    }

    def format(self, record):
        # Get the original formatted message
        message = super().format(record)
        
        # Add color based on log level
        color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        reset = self.COLORS['RESET']
        
        return f"{color}{message}{reset}"

def _setup_global_logging():
    """Automatically configure logging when this module loads"""
    root_logger = logging.getLogger()
    
    # Only setup once
    if not root_logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = ColoredFormatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%H:%M:%S'
        )
        handler.setFormatter(formatter)
        root_logger.addHandler(handler)
        root_logger.setLevel(logging.INFO)

# This runs automatically when anyone imports this module
_setup_global_logging()

def get_logger(name: str) -> logging.Logger:
    """Get a colored logger - setup is automatic"""
    return logging.getLogger(name)
