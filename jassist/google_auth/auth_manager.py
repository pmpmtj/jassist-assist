# auth_manager.py
from pathlib import Path
import pickle
import traceback
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from jassist.logger_utils.logger_utils import setup_logger
from jassist.utils.path_utils import resolve_path

logger = setup_logger("auth_manager")

def get_credentials(auth_cfg: dict, scopes: list):
    credentials_file = resolve_path(auth_cfg.get("credentials_file", "google_credentials.json"), auth_cfg.get("credentials_path", "credentials"))
    token_file = credentials_file.parent / auth_cfg.get("token_file", "token.pickle")

    creds = None
    if token_file.exists():
        try:
            with open(token_file, 'rb') as token:
                creds = pickle.load(token)
        except Exception as e:
            logger.warning(f"Failed to load token: {e}")
            logger.debug(traceback.format_exc())

    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            with open(token_file, 'wb') as token:
                pickle.dump(creds, token)
            logger.info("Token refreshed.")
        except Exception as e:
            logger.warning(f"Token refresh failed: {e}")
            logger.debug(traceback.format_exc())
            creds = None

    if not creds:
        logger.info("Starting new OAuth flow.")
        flow = InstalledAppFlow.from_client_secrets_file(str(credentials_file), scopes=scopes)
        creds = flow.run_local_server(port=0)
        with open(token_file, 'wb') as token:
            pickle.dump(creds, token)
        logger.info("New credentials saved.")

    return creds

def get_service(api_name: str, api_version: str, config: dict):
    scopes = config.get("api", {}).get("scopes", [])
    creds = get_credentials(config.get("auth", {}), scopes)
    return build(api_name, api_version, credentials=creds)
