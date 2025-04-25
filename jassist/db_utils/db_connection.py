import psycopg2
from psycopg2 import pool
import traceback
import functools
from jassist.db_utils.db_env_utils import get_db_url
from jassist.logger_utils.logger_utils import setup_logger

logger = setup_logger("db_connection", module="db_utils")

# Global connection pool
connection_pool = None

def initialize_db():
    """Initialize the database connection pool"""
    global connection_pool

    try:
        db_url = get_db_url()
        if not db_url:
            logger.error("Cannot initialize database: DATABASE_URL is not set. Make sure .env file exists and is properly configured.")
            return False
            
        logger.debug(f"Initializing DB with URL: {db_url}")
        logger.info("Initializing DB with connection string (details hidden)")

        logger.info("Testing direct connection...")
        try:
            test_conn = psycopg2.connect(db_url)
            logger.info(f"Connected. PostgreSQL version: {test_conn.server_version}")
            test_conn.close()
        except Exception as conn_error:
            logger.error(f"Direct connection failed: {conn_error}")
            return False

        logger.info("Creating connection pool...")
        connection_pool = pool.SimpleConnectionPool(1, 10, db_url)
        logger.info("Connection pool created")
        return True

    except Exception as e:
        logger.error("DB initialization failed.")
        logger.error(traceback.format_exc())
        return False

def get_connection():
    """Get a connection from the pool"""
    global connection_pool
    if connection_pool is None:
        initialize_db()
    return connection_pool.getconn()

def return_connection(conn):
    """Return a connection to the pool"""
    if connection_pool is not None:
        connection_pool.putconn(conn)

def close_all_connections():
    """Close all connections in the pool"""
    global connection_pool
    if connection_pool:
        connection_pool.closeall()
        connection_pool = None
        logger.info("Closed all DB connections.")

def db_connection_handler(func):
    """
    Decorator for database operations that handles connection management.
    Automatically acquires a connection from the pool, handles exceptions,
    and returns the connection to the pool when done.
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        conn = None
        try:
            conn = get_connection()
            return func(conn, *args, **kwargs)
        except Exception as e:
            if conn and not kwargs.get('_skip_rollback', False):
                conn.rollback()
            logger.error(f"Database error in {func.__name__}: {str(e)}")
            logger.error(traceback.format_exc())
            
            # Return an appropriate default value based on the function's purpose
            if func.__name__.startswith('get_'):
                return [] if 'fetchall' in func.__code__.co_names else None
            elif func.__name__.startswith('save_'):
                return None
            elif func.__name__.startswith('update_') or func.__name__.startswith('delete_'):
                return False
            elif func.__name__.startswith('check_'):
                return False
            else:
                return None
        finally:
            if conn:
                return_connection(conn)
    return wrapper

if __name__ == "__main__":
    logger.info("Testing database connection...")
    if initialize_db():
        logger.info("Database connection successful")
        conn = get_connection()
        logger.info("Connection obtained from pool")
        return_connection(conn)
        close_all_connections()
    else:
        logger.error("Failed to connect to database") 