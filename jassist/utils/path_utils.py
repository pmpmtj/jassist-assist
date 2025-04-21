"""
Path Utilities

Centralized utilities for consistent path resolution across all modules.
"""

from pathlib import Path
from typing import Union
import traceback
from jassist.logger_utils.logger_utils import setup_logger

logger = setup_logger("path_utils", module="utils")

def resolve_path(path_input: Union[str, Path], base_dir: Path = None) -> Path:
    """
    Consistently resolve a path string or Path object to an absolute Path.
    
    Args:
        path_input: The path string or Path object to resolve
        base_dir: Optional base directory to resolve relative paths from
                  If None, relative paths will be resolved from current directory
        
    Returns:
        An absolute Path object
    """
    # Convert to Path object if it's a string
    path = Path(path_input) if isinstance(path_input, str) else path_input
    
    # If already absolute, return it directly
    if path.is_absolute():
        return path
    
    # If no base_dir provided, use current working directory
    if base_dir is None:
        return path.resolve()
        
    # If path contains parent directory references (..), handle specially
    if isinstance(path_input, str) and "../" in path_input:
        return (base_dir / path_input).resolve()
    
    # Otherwise, simply join with the base directory
    return (base_dir / path).resolve() 


def ensure_directory_exists(dir_path: Path, description="directory"):
    """
    Ensure a directory exists, creating it if necessary.
    
    Args:
        dir_path: Path to check/create
        description: Description for logging
    """
    try:
        # Import the logger here to avoid circular imports
        from jassist.logger_utils.logger_utils import setup_logger
        logger = setup_logger("path_utils", module="utils")
        
        if not dir_path.exists():
            dir_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created {description} at: {dir_path}")
    except Exception as e:
        logger.error(f"Error ensuring {description}: {e}")
        logger.debug(traceback.format_exc())