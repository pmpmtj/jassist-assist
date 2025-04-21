# config_loader.py
import json
from pathlib import Path
from typing import Dict, Any
from jassist.logger_utils.logger_utils import setup_logger, ENCODING
from jassist.utils.path_utils import resolve_path, ensure_directory_exists

logger = setup_logger("config_loader", module="download_gdrive")

def load_config(config_path: Path) -> Dict[str, Any]:
    """
    Load configuration from the specified path.
    
    Args:
        config_path: Path to the configuration file
        
    Returns:
        Dict containing configuration
        
    Raises:
        FileNotFoundError: If config file doesn't exist
        ValueError: If config is missing required keys
    """
    def validate_config(config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate that config has all required keys."""
        required_keys = ["file_types", "folders", "download"]
        for key in required_keys:
            if key not in config:
                raise ValueError(f"Missing required config key: {key}")
        
        logger.debug(f"Config validated successfully with keys: {', '.join(config.keys())}")
        return config

    # Ensure path is properly resolved
    config_path = resolve_path(config_path)
    logger.debug(f"Resolved config path: {config_path}")
    
    # Ensure the directory exists
    ensure_directory_exists(config_path.parent, description="config directory")
    
    if config_path.exists():
        logger.debug(f"Loading configuration from: {config_path}")
        with open(config_path, "r", encoding=ENCODING) as f:
            config = json.load(f)
            logger.info(f"Configuration loaded successfully from {config_path}")
            return validate_config(config)
    else:
        logger.error(f"Configuration file not found: {config_path}")
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
