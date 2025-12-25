"""
Logging configuration
"""
import logging
import os
from datetime import datetime


def get_logger(name: str) -> logging.Logger:
    """
    Logger oluştur
    
    Kullanım:
        logger = get_logger(__name__)
        logger.info("User logged in", extra={'user_id': 1})
    """
    logger = logging.getLogger(name)
    
    if not logger.handlers:
        logger.setLevel(logging.DEBUG)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_format = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(console_format)
        logger.addHandler(console_handler)
        
        # File handler (logs klasörüne)
        log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'logs')
        os.makedirs(log_dir, exist_ok=True)
        
        log_file = os.path.join(log_dir, f'{datetime.now().strftime("%Y-%m-%d")}.log')
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_format = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_format)
        logger.addHandler(file_handler)
    
    return logger


# Game events logger
game_logger = get_logger('game_api.games')

# Auth events logger
auth_logger = get_logger('game_api.auth')

# Admin events logger
admin_logger = get_logger('game_api.admin')

# Error logger
error_logger = get_logger('game_api.errors')

