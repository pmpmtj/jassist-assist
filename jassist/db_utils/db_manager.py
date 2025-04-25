"""
Database Manager Module

This module serves as a facade for the database components.
It provides a centralized interface to the database operations.
"""

from jassist.db_utils.db_connection import (
    initialize_db, 
    close_all_connections,
    db_connection_handler
)
from jassist.db_utils.db_schema import create_tables
from jassist.logger_utils.logger_utils import setup_logger

logger = setup_logger("db_manager", module="db_utils")

# Re-export initialize_db to maintain backward compatibility
__all__ = [
    # Connection management
    'initialize_db',
    'close_all_connections',
    'create_tables',
    'db_connection_handler',
]
