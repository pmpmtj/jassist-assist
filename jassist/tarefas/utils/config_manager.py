"""
Configuration management utilities for task processing.

This module centralizes configuration loading from various sources.
"""

import json
import sys
import os
from pathlib import Path
from typing import Dict, Any
from jassist.logger_utils.logger_utils import setup_logger
from jassist.utils.path_utils import resolve_path

logger = setup_logger("config_manager", module="tarefas")

# Define the module directory path, handling both frozen and regular execution
if getattr(sys, 'frozen', False):
    # We're running in a PyInstaller bundle
    SCRIPT_DIR = Path(sys.executable).parent
else:
    # Normal Python execution
    SCRIPT_DIR = Path(__file__).resolve().parent

def get_config_dir() -> Path:
    """
    Get the configuration directory.
    
    Returns:
        Path: Path to the config directory
    """
    return SCRIPT_DIR.parent / "config"

def get_module_dir() -> Path:
    """
    Get the tarefas module directory.
    
    Returns:
        Path: Path to the tarefas module directory
    """
    return SCRIPT_DIR.parent

def load_json_config(file_name: str) -> Dict[str, Any]:
    """
    Load a JSON configuration file.
    
    Args:
        file_name: Name of the configuration file
        
    Returns:
        Dict containing the configuration
    """
    try:
        config_path = get_config_dir() / file_name
        
        if not config_path.exists():
            logger.error(f"Config file not found: {config_path}")
            return {}
            
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading config file {file_name}: {e}")
        return {} 