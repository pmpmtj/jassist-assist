# auth_manager.py
import json
from pathlib import Path
import pickle
import traceback
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from jassist.logger_utils.logger_utils import setup_logger
from jassist.utils.path_utils import resolve_path, ensure_directory_exists

logger = setup_logger("auth_manager", module="google_auth")

def load_auth_config():
    """Load auth configuration from the dedicated config file."""
    try:
        # Get path to auth config file
        config_file = Path(__file__).resolve().parent / "config" / "google_auth_config.json"
        logger.debug(f"Loading auth config from: {config_file}")
        
        if not config_file.exists():
            logger.error(f"Auth config file not found: {config_file}")
            return {}
            
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
            logger.debug(f"Auth config loaded successfully")
            return config
    except Exception as e:
        logger.error(f"Failed to load auth config: {e}")
        logger.debug(traceback.format_exc())
        return {}

def get_credentials(auth_cfg: dict, scopes: list):
    """
    Get Google API credentials, refreshing or creating new ones if needed.
    
    Args:
        auth_cfg: Dictionary containing auth configuration
        scopes: List of API scopes to request
        
    Returns:
        Google API credentials object or None if authentication failed
    """
    try:
        # Get the jassist directory path
        jassist_dir = Path(__file__).resolve().parent.parent
        
        # Resolve credentials path relative to jassist directory
        credentials_path = jassist_dir / auth_cfg.get("credentials_path", "credentials")
        credentials_file = credentials_path / auth_cfg.get("credentials_file", "my_credentials.json")
        token_file = credentials_path / auth_cfg.get("token_file", "token.pickle")
        
        logger.debug(f"Using credentials file: {credentials_file}")
        logger.debug(f"Using token file: {token_file}")
        
        # Ensure the credentials directory exists
        ensure_directory_exists(credentials_path, "credentials directory")

        creds = None
        if token_file.exists():
            try:
                logger.debug("Loading existing token")
                with open(token_file, 'rb') as token:
                    creds = pickle.load(token)
                logger.debug(f"Token loaded, expired: {creds.expired if creds else 'N/A'}")
            except Exception as e:
                logger.warning(f"Failed to load token: {e}")
                logger.debug(traceback.format_exc())

        if creds and creds.expired and creds.refresh_token:
            try:
                logger.debug("Refreshing expired token")
                creds.refresh(Request())
                with open(token_file, 'wb') as token:
                    pickle.dump(creds, token)
                logger.info("Token refreshed.")
            except Exception as e:
                logger.warning(f"Token refresh failed: {e}")
                logger.debug(traceback.format_exc())
                creds = None

        if not creds:
            if not credentials_file.exists():
                logger.error(f"Credentials file not found: {credentials_file}")
                return None
                
            logger.info("Starting new OAuth flow.")
            flow = InstalledAppFlow.from_client_secrets_file(str(credentials_file), scopes=scopes)
            creds = flow.run_local_server(port=0)
            with open(token_file, 'wb') as token:
                pickle.dump(creds, token)
            logger.info("New credentials saved.")

        return creds
        
    except Exception as e:
        logger.error(f"Unexpected error in get_credentials: {e}")
        logger.debug(traceback.format_exc())
        return None

def get_service(api_name: str, api_version: str, config: dict = None):
    """
    Get authenticated Google API service.
    
    Args:
        api_name: Name of the API (e.g., 'drive')
        api_version: Version of the API (e.g., 'v3')
        config: Optional configuration dictionary (if not provided, will load from auth config)
        
    Returns:
        Google API service or None if authentication failed
    """
    try:
        logger.debug(f"Setting up {api_name} {api_version} service")
        
        # Load auth config if not provided
        auth_config = load_auth_config()
        if not auth_config:
            logger.error("Failed to load auth configuration")
            return None
            
        # Get scopes from auth config
        if "apis" in auth_config and api_name in auth_config["apis"] and "scopes" in auth_config["apis"][api_name]:
            scopes = auth_config["apis"][api_name]["scopes"]
            logger.debug(f"Using scopes from auth config: {scopes}")
        else:
            logger.error(f"No scopes defined for {api_name} API in auth configuration")
            return None
                
        # Get credentials using auth config
        creds = get_credentials(auth_config.get("auth", {}), scopes)
        
        if not creds:
            logger.error("Failed to obtain credentials")
            return None
            
        service = build(api_name, api_version, credentials=creds)
        logger.debug(f"{api_name} {api_version} service created successfully")
        return service
        
    except Exception as e:
        logger.error(f"Failed to create {api_name} service: {e}")
        logger.debug(traceback.format_exc())
        return None
