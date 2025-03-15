import logging
import os
from datetime import datetime
from pathlib import Path

# Create logs directory if it doesn't exist
LOGS_DIR = Path('logs')
LOGS_DIR.mkdir(exist_ok=True)

# Create a logger
logger = logging.getLogger('cv_generator')
logger.setLevel(logging.INFO)

# Create formatters
file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
console_formatter = logging.Formatter('%(levelname)s: %(message)s')

# Create and configure file handler
log_file = LOGS_DIR / f'cv_generator_{datetime.now().strftime("%Y%m%d")}.log'
file_handler = logging.FileHandler(log_file)
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(file_formatter)

# Create and configure console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(console_formatter)

# Add handlers to logger
logger.addHandler(file_handler)
logger.addHandler(console_handler)

def log_error(error_message: str, error: Exception = None):
    """Log an error message and optionally the exception details."""
    if error:
        logger.error(f"{error_message}: {str(error)}")
    else:
        logger.error(error_message)

def log_info(message: str):
    """Log an info message."""
    logger.info(message)

def log_warning(message: str):
    """Log a warning message."""
    logger.warning(message)

# Example usage
if __name__ == "__main__":
    log_info("Testing info message")
    log_warning("Testing warning message")
    try:
        raise ValueError("Test error")
    except Exception as e:
        log_error("An error occurred during testing", e) 
