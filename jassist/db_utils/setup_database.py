#!/usr/bin/env python3
import os
import sys
import argparse
import logging
from pathlib import Path
from jassist.db_utils.db_connection import initialize_db
from jassist.db_utils.db_schema import create_tables
from jassist.logger_utils.logger_utils import setup_logger
from jassist.db_utils.db_env_utils import load_environment

logger = setup_logger("setup_database", module="db_utils")

def main():
    # Load environment variables
    load_environment()
    
    logger.info("Initializing database...")
    if initialize_db():
        logger.info("Creating database tables...")
        if create_tables():
            logger.info("Database setup completed successfully.")
        else:
            logger.error("Table creation failed.")
            sys.exit(1)
    else:
        logger.error("Database initialization failed.")
        sys.exit(1)

if __name__ == "__main__":
    main()
