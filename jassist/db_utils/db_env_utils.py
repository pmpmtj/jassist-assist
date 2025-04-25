"""
Environment Utilities

Centralized module for environment variable management.
Handles loading from system environment with fallback to .env files.
"""

import os
import re
from pathlib import Path
from typing import Optional, Dict, Any
from dotenv import load_dotenv

from jassist.logger_utils.logger_utils import setup_logger
from jassist.utils.path_utils import resolve_path

logger = setup_logger("db_env_utils", module="db_utils")

# Default location for .env file
DEFAULT_ENV_PATH = Path(__file__).parents[1] / "credentials" / ".env"

# Define more flexible PostgreSQL connection string pattern
POSTGRES_URL_PATTERN = re.compile(
    r'^postgres(?:ql)?://.*$'  # Accept any string that starts with postgres:// or postgresql://
)

def load_environment(custom_env_path: Optional[Path] = None) -> Dict[str, str]:
    """
    Load environment variables, prioritizing system environment variables
    and falling back to .env file if variables aren't found.
    
    Args:
        custom_env_path: Optional custom path to .env file.
                         If None, uses DEFAULT_ENV_PATH.
    
    Returns:
        Dict of loaded environment variables
    """
    # Get initial system environment variables
    initial_env = dict(os.environ)
    logger.debug("Initial environment variables retrieved from system")
    
    # Determine .env file path
    env_path = custom_env_path if custom_env_path else DEFAULT_ENV_PATH
    env_path = resolve_path(env_path)
    
    # Load from .env file if it exists (with override=False to prioritize system variables)
    if env_path.exists():
        load_dotenv(dotenv_path=env_path, override=False)
        logger.info(f"Loaded .env from {env_path} (system variables take precedence)")
    else:
        logger.warning(f".env file not found at expected location: {env_path}")
        logger.info("Using only system environment variables")
    
    # Return new variables that were added
    new_env = {k: v for k, v in os.environ.items() if k not in initial_env or initial_env[k] != v}
    if new_env:
        logger.debug(f"Added {len(new_env)} environment variables from .env file")
    
    return new_env

def get_db_url() -> str:
    """
    Retrieves the DATABASE_URL from environment variables and validates it.
    Ensures environment is loaded first.

    Returns:
        str: A valid PostgreSQL connection string.

    Raises:
        EnvironmentError: If DATABASE_URL is missing or invalid.
    """
    # Load environment if needed
    load_environment()
    
    db_url = os.getenv('DATABASE_URL')

    # Raise if not found
    if not db_url:
        logger.critical("DATABASE_URL not found in environment. Aborting.")
        raise EnvironmentError(
            "Missing DATABASE_URL in environment variables. "
            "Ensure the credentials/.env file exists or the variable is set in the system environment."
        )

    # Validate format (basic PostgreSQL connection string structure)
    if not POSTGRES_URL_PATTERN.match(db_url):
        logger.critical(f"Invalid DATABASE_URL format: {db_url}")
        raise ValueError(
            "DATABASE_URL found, but format is invalid. "
            "It must start with 'postgresql://' or 'postgres://'"
        )

    logger.debug("Validated DB URL")
    logger.info("Using DB URL (validated and accepted)")
    return db_url

def get_env_variable(key: str, default: Any = None, required: bool = False) -> Any:
    """
    Get environment variable with proper error handling.
    
    Args:
        key: Environment variable name
        default: Default value if not found
        required: If True, raises error when not found
        
    Returns:
        Value of environment variable or default
        
    Raises:
        EnvironmentError: If required is True and variable not found
    """
    # Load environment if needed
    load_environment()
    
    value = os.getenv(key)
    
    if value is None:
        if required:
            logger.critical(f"Required environment variable {key} not found")
            raise EnvironmentError(f"Missing required environment variable: {key}")
        else:
            logger.debug(f"Environment variable {key} not found, using default: {default}")
            return default
    
    logger.debug(f"Retrieved environment variable: {key}")
    return value

def debug_db_url():
    """
    Debug helper for DATABASE_URL issues.
    Prints information about the DATABASE_URL without exposing sensitive data.
    """
    # Load environment
    load_environment()
    
    db_url = os.getenv('DATABASE_URL')
    
    if not db_url:
        logger.critical("DATABASE_URL is not set in environment")
        return
    
    # Check basic format
    if not db_url.startswith(('postgresql://', 'postgres://')):
        logger.critical("DATABASE_URL doesn't start with 'postgresql://' or 'postgres://'")
        logger.info(f"URL starts with: {db_url[:10]}...")
        return
    
    # Try to parse components
    try:
        # Split into components but don't log sensitive parts
        parts = db_url.split('@')
        if len(parts) != 2:
            logger.warning("DATABASE_URL doesn't have expected format with @ separator")
        else:
            # Extract host:port/dbname
            connection_part = parts[1]
            logger.info(f"Host part: {connection_part}")
            
            # Check for port
            host_parts = connection_part.split(':')
            if len(host_parts) != 2:
                logger.warning("Host:port format not as expected")
            else:
                port_db = host_parts[1].split('/')
                if len(port_db) != 2:
                    logger.warning("Port/database format not as expected")
                else:
                    logger.info(f"Port: {port_db[0]}, Database: {port_db[1]}")
        
        logger.info("DATABASE_URL structure analyzed (credentials hidden)")
    except Exception as e:
        logger.error(f"Error analyzing DATABASE_URL: {e}")
    
    # Check URL length
    logger.info(f"DATABASE_URL length: {len(db_url)} characters") 