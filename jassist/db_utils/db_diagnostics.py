#!/usr/bin/env python3
"""
Database diagnostics helper script.

Run this script to troubleshoot database connection issues.
It provides diagnostics without exposing sensitive credentials.
"""

import os
import sys
from pathlib import Path
import traceback

# Add parent directory to path if running directly
parent_dir = Path(__file__).resolve().parent.parent.parent
if str(parent_dir) not in sys.path:
    sys.path.append(str(parent_dir))

from jassist.db_utils.db_env_utils import debug_db_url, load_environment
from jassist.logger_utils.logger_utils import setup_logger

logger = setup_logger("db_diagnostics", module="db_utils")

def run_diagnostics():
    """Run database connection diagnostics"""
    logger.info("=== Running Database Connection Diagnostics ===")
    
    # Check system environment
    logger.info("Checking system environment...")
    python_version = sys.version.replace('\n', ' ')
    logger.info(f"Python version: {python_version}")
    logger.info(f"Platform: {sys.platform}")
    
    # Load environment
    logger.info("\nLoading environment variables...")
    load_environment()
    
    # Debug DATABASE_URL
    logger.info("\nAnalyzing DATABASE_URL...")
    debug_db_url()
    
    # Check for required packages
    logger.info("\nChecking for required packages...")
    try:
        import psycopg2
        logger.info(f"psycopg2 version: {psycopg2.__version__}")
    except ImportError:
        logger.error("psycopg2 package not found. Install with: pip install psycopg2-binary")
    except Exception as e:
        logger.error(f"Error importing psycopg2: {e}")
    
    # Check for PostgreSQL connectivity (without exposing credentials)
    logger.info("\nTesting basic connection ability...")
    try:
        import socket
        db_url = os.getenv('DATABASE_URL', '')
        if '@' in db_url:
            # Extract host and port
            host_part = db_url.split('@')[1].split('/')[0]
            if ':' in host_part:
                host, port_str = host_part.split(':')
                port = int(port_str)
                logger.info(f"Testing connection to {host}:{port}...")
                
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(5)
                try:
                    s.connect((host, port))
                    logger.info(f"✅ Successfully connected to {host}:{port}")
                    s.close()
                except Exception as e:
                    logger.error(f"❌ Cannot connect to {host}:{port} - {e}")
            else:
                logger.warning("Could not extract port from DATABASE_URL")
        else:
            logger.warning("Could not extract host from DATABASE_URL")
    except Exception as e:
        logger.error(f"Error testing connection: {e}")
    
    logger.info("\n=== Diagnostics Complete ===")

if __name__ == "__main__":
    try:
        run_diagnostics()
    except Exception as e:
        logger.error(f"Diagnostics failed: {e}")
        logger.debug(traceback.format_exc()) 