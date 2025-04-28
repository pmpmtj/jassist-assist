"""
Google agenda integration module.

This module handles interactions with the Google agenda API.
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from .utils.config_manager import load_agenda_config, get_module_dir
from jassist.utils.path_utils import resolve_path, ensure_directory_exists
from jassist.logger_utils.logger_utils import setup_logger

logger = setup_logger("google_agenda", module="agenda")

# Define the scopes required for Google agenda
SCOPES = ['https://www.googleapis.com/auth/calendar']

def get_credentials_path() -> Path:
    """
    Get path to Google API credentials.
    
    Returns:
        Path: Path to the credentials directory
    """
    config = load_agenda_config()
    
    # Get the current module's directory
    module_dir = get_module_dir()
    
    # Get credentials directory from config or use default
    credentials_dir = config.get('paths', {}).get('credentials_directory', 'credentials')
    credentials_path = resolve_path(credentials_dir, module_dir)
    
    # Create directory if it doesn't exist
    ensure_directory_exists(credentials_path, "credentials directory")
    
    return credentials_path

def get_agenda_service():
    """
    Get an authenticated Google agenda service.
    
    Returns:
        Resource: Google agenda service
        
    Raises:
        ValueError: If credentials_filename is missing from config
        FileNotFoundError: If credentials file not found
        Exception: For other authentication errors
    """
    creds = None
    credentials_dir = get_credentials_path()
    token_path = credentials_dir / "token.json"
    
    # Load the path to the client secrets file from config
    config = load_agenda_config()
    credentials_filename = config.get('google_agenda', {}).get('credentials_filename', '')
    
    if not credentials_filename:
        logger.error("No credentials filename specified in config")
        raise ValueError("Missing credentials_filename in config - update agenda_config.json")
    
    logger.debug(f"Looking for credentials file: {credentials_filename}")
    
    # Look for credentials in module credentials directory first
    credentials_path = credentials_dir / credentials_filename
    
    # Fallback to the main jassist credentials directory if not found
    if not credentials_path.exists():
        project_root = Path(__file__).resolve().parent.parent.parent
        alt_path = project_root / "jassist" / "credentials" / credentials_filename
        logger.debug(f"Credentials not found at {credentials_path}, checking {alt_path}")
        if alt_path.exists():
            credentials_path = alt_path
    
    # Check if token already exists and try to load it
    if token_path.exists():
        try:
            logger.debug(f"Loading existing token from {token_path}")
            creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
            logger.debug(f"Token loaded successfully. Valid: {creds.valid}, Expired: {getattr(creds, 'expired', 'N/A')}")
        except Exception as e:
            logger.warning(f"Error loading existing token, will create new one: {e}")
            # Continue with flow to create new token
    else:
        logger.debug("No existing token found, will create new one")

    # If there are no valid credentials, let the user log in
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                logger.debug("Refreshing expired token")
                creds.refresh(Request())
                logger.debug("Token refreshed successfully")
            except Exception as e:
                logger.warning(f"Token refresh failed, will create new one: {e}")
                # Fall through to create new token
        else:
            if not credentials_path.exists():
                error_msg = (
                    f"Google API credentials not found at {credentials_path}. "
                    "Download credentials.json from the Google Developer Console "
                    "and place it in the credentials directory."
                )
                logger.error(error_msg)
                raise FileNotFoundError(error_msg)
            
            logger.info(f"Using credentials file: {credentials_path}")
            try:
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(credentials_path), SCOPES)
                creds = flow.run_local_server(port=0)
                logger.info("New authentication successful")
            except Exception as e:
                logger.error(f"Authentication flow failed: {e}")
                raise Exception(f"Failed to authenticate with Google: {e}")
            
        # Save the credentials for the next run
        try:
            with open(token_path, 'w') as token_file:
                token_file.write(creds.to_json())
            logger.debug(f"Token saved to {token_path}")
        except Exception as e:
            # Non-fatal error - we can continue with the credential in memory
            logger.warning(f"Failed to save token to {token_path}: {e}")

    try:
        service = build('calendar', 'v3', credentials=creds)
        return service
    except Exception as e:
        logger.error(f"Failed to build calendar service: {e}")
        raise Exception(f"Failed to initialize Google Calendar API: {e}")

def insert_event_into_google_agenda(event_data: Dict[str, Any]) -> Optional[str]:
    """
    Insert an event into Google agenda.
    
    Args:
        event_data: Dictionary containing event data
        
    Returns:
        str: URL to the created event, or None if creation failed
    """
    config = load_agenda_config()
    
    # Check if Google agenda integration is enabled
    use_google_agenda = config.get('google_agenda', {}).get('use_google_agenda', True)
    if not use_google_agenda:
        logger.info("Google agenda integration is disabled in config")
        return None
    
    agenda_id = config.get('google_agenda', {}).get('agenda_id', 'primary')
    logger.debug(f"Using calendar ID: {agenda_id}")
    
    # Check and fix attendees with missing email addresses
    if "attendees" in event_data and event_data["attendees"]:
        logger.debug(f"Checking {len(event_data['attendees'])} attendees for missing email addresses")
        for i, attendee in enumerate(event_data["attendees"]):
            if not attendee.get("email"):
                logger.warning(f"Attendee #{i+1} missing email, adding dummy email: dummy@example.com")
                attendee["email"] = "dummy@example.com"
    
    logger.debug(f"Event data for Google Calendar: {event_data}")
    
    try:
        logger.info("Getting Google Calendar service...")
        service = get_agenda_service()
        logger.info("Inserting event into Google Calendar...")
        event = service.events().insert(
            calendarId=agenda_id,
            body=event_data
        ).execute()

        logger.info(f"Event created: {event.get('htmlLink')}")
        return event.get("htmlLink")
        
    except HttpError as error:
        logger.error(f"Google Calendar API error inserting event: {error}")
        return None
    except Exception as e:
        logger.exception(f"Unexpected error inserting event: {e}")
        return None 