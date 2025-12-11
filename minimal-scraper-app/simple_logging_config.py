import logging
import sys

def setup_simple_logging():
    """Set up simple logging for the minimal desktop app."""
    # Configure root logger
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )

def get_simple_logger(name: str) -> logging.Logger:
    """Get a logger with simple formatting."""
    setup_simple_logging()
    return logging.getLogger(name)