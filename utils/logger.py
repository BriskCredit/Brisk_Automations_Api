import logging
import sys
from typing import Optional


def setup_logging(level: int = logging.INFO) -> None:
    """
    Configure logging for the application.
    
    Args:
        level: The logging level to use (default: INFO)
    """
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Get a logger instance with the specified name.
    
    Args:
        name: The name for the logger (default: None for root logger)
        
    Returns:
        A configured logger instance
    """
    return logging.getLogger(name)
