import logging
import sys
import os

def setup_logger(name: str = "AI_Core"):
    logger = logging.getLogger(name)
    if not logger.handlers:
        # Ensure logs directory exists
        os.makedirs("logs", exist_ok=True)
        
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        # File handler
        file_handler = logging.FileHandler('logs/session.log')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        logger.setLevel(logging.INFO)
    return logger