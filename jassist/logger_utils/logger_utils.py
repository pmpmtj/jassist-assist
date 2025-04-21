import logging
import os
import json
from pathlib import Path
from utils.path_utils import resolve_path
from logging.handlers import RotatingFileHandler

ENCODING = "utf-8"
DEFAULT_LOG_LEVEL = "INFO"
DEFAULT_LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Base directory for the project
PROJECT_DIR = resolve_path(Path(__file__).parents[1])

# Logger config file (relative to current file's parent)
LOGGER_CONFIG_PATH = resolve_path("config/logger_config.json", base_dir=Path(__file__).parent)

# Logs directory (ensures it's absolute)
LOGS_DIR = resolve_path("logs", base_dir=PROJECT_DIR)


def load_logger_config():
    """Load logger configuration from JSON file if it exists."""
    # Ensure config exists first
    if LOGGER_CONFIG_PATH.exists():
        try:
            with open(LOGGER_CONFIG_PATH, "r", encoding=ENCODING) as f:
                return json.load(f)
        except Exception as e:
            print(f"[Logger] Failed to load config: {e}")
    return {}

def setup_logger(name="jassist", module=None):
    """
    Set up a logger with configuration from the config file.
    
    Args:
        name: The base name for the logger
        module: Optional module name to use module-specific config
        
    Returns:
        A configured logger instance
    """
    config = load_logger_config()
    logging_config = config.get("logging", {})
    
    # Get the logger instance
    logger = logging.getLogger(name)
    
    # Prevent duplicate handlers if already configured
    if logger.hasHandlers():
        return logger
    
    # Determine if we should use module-specific configuration
    module_config = None
    if module and module in logging_config.get("modules", {}):
        module_config = logging_config["modules"][module]
    
    # Set up console handler
    console_config = logging_config.get("console", {})
    console_level = getattr(logging, console_config.get("level", DEFAULT_LOG_LEVEL).upper(), logging.INFO)
    console_format = console_config.get("format", DEFAULT_LOG_FORMAT)
    console_date_format = console_config.get("date_format", DEFAULT_DATE_FORMAT)
    
    console_formatter = logging.Formatter(
        fmt=console_format,
        datefmt=console_date_format
    )
    
    console_handler = logging.StreamHandler()
    console_handler.setLevel(console_level)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # Set up file handler with rotation
    file_config = logging_config.get("file", {})
    
    # Override with module-specific config if available
    if module_config:
        for key in ["level", "log_filename"]:
            if key in module_config:
                file_config[key] = module_config[key]
    
    file_level = getattr(logging, file_config.get("level", DEFAULT_LOG_LEVEL).upper(), logging.INFO)
    file_format = file_config.get("format", DEFAULT_LOG_FORMAT)
    file_date_format = file_config.get("date_format", DEFAULT_DATE_FORMAT)
    log_filename = file_config.get("log_filename", "voice_diary.log")
    max_bytes = file_config.get("max_size_bytes", 1048576)  # Default 1MB
    backup_count = file_config.get("backup_count", 5)
    encoding = file_config.get("encoding", ENCODING)
    
    # Ensure log directory exists and get absolute path
    log_path = resolve_path(log_filename, base_dir=LOGS_DIR)

    file_formatter = logging.Formatter(
        fmt=file_format,
        datefmt=file_date_format
    )
    
    file_handler = RotatingFileHandler(
        filename=log_path,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding=encoding
    )
    file_handler.setLevel(file_level)
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    
    # Set logger level to the most verbose of the handlers
    logger.setLevel(min(console_level, file_level))
    
    return logger
