"""
Logging Utility
Configures and manages logging for NEXUS system
"""

import logging
import os
from datetime import datetime
import src.config as config


def setup_logger(name: str = "NEXUS", 
                log_file: str = None,
                level: int = logging.INFO) -> logging.Logger:
    """
    Setup and configure logger
    
    Args:
        name: Logger name
        log_file: Optional log file path
        level: Logging level
    
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Clear existing handlers
    logger.handlers = []
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # File handler (if specified)
    if log_file:
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(level)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    
    return logger


def get_simulation_logger() -> logging.Logger:
    """Get logger for simulation runs"""
    log_file = os.path.join(
        config.LOGS_DIR,
        f"simulation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    )
    return setup_logger("NEXUS_Simulation", log_file)


class ProgressTracker:
    """Track and display progress of long-running operations"""
    
    def __init__(self, total: int, description: str = "Processing"):
        self.total = total
        self.current = 0
        self.description = description
        self.start_time = datetime.now()
    
    def update(self, increment: int = 1):
        """Update progress"""
        self.current += increment
        percentage = (self.current / self.total) * 100
        
        # Calculate ETA
        elapsed = (datetime.now() - self.start_time).total_seconds()
        if self.current > 0:
            eta_seconds = (elapsed / self.current) * (self.total - self.current)
            eta_str = f"ETA: {int(eta_seconds)}s"
        else:
            eta_str = "ETA: --"
        
        print(f"\r{self.description}: {self.current}/{self.total} ({percentage:.1f}%) - {eta_str}", end="")
    
    def complete(self):
        """Mark as complete"""
        elapsed = (datetime.now() - self.start_time).total_seconds()
        print(f"\r{self.description}: Complete! ({self.total}/{self.total}) - Took {elapsed:.1f}s")
