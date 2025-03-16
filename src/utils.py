# src/utils.py
import logging
import os
import sys

import colorlog


def setup_logging(level_name="INFO"):
    """Set up logging configuration."""
    # Map string level to actual logging level
    level = getattr(logging, level_name.upper(), logging.INFO)
    
    # Create root logger
    logger = logging.getLogger()
    logger.setLevel(level)
    
    # Clear existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Create console handler with color formatting
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    
    # Color formatter
    color_formatter = colorlog.ColoredFormatter(
        "%(log_color)s%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        log_colors={
            'DEBUG': 'cyan',
            'INFO': 'green',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'red,bg_white',
        }
    )
    console_handler.setFormatter(color_formatter)
    
    # Create file handler
    logs_dir = os.path.join(os.getcwd(), 'logs')
    os.makedirs(logs_dir, exist_ok=True)
    
    file_handler = logging.FileHandler(os.path.join(logs_dir, 'grandmaster.log'))
    file_handler.setLevel(level)
    file_formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s", 
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(file_formatter)
    
    # Add handlers to logger
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
    # Create specific loggers for each component
    component_loggers = ['grandmaster', 'grandmaster.websocket', 'grandmaster.telegram', 'grandmaster.scheduler']
    for name in component_loggers:
        component_logger = logging.getLogger(name)
        component_logger.setLevel(level)
    
    return logger


def format_timedelta(seconds):
    """Format seconds into a human-readable time string."""
    days, remainder = divmod(seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    parts = []
    if days > 0:
        parts.append(f"{int(days)}d")
    if hours > 0:
        parts.append(f"{int(hours)}h")
    if minutes > 0:
        parts.append(f"{int(minutes)}m")
    if seconds > 0 or not parts:
        parts.append(f"{int(seconds)}s")
    
    return " ".join(parts)