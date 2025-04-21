# Test script for credential loading
import os
import sys
from pathlib import Path
import json

# Add the project root to the Python path if needed
script_dir = Path(__file__).resolve().parent
project_root = script_dir.parent.parent

if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from jassist.google_auth.auth_manager import get_service, load_auth_config
from jassist.logger_utils.logger_utils import setup_logger

logger = setup_logger("auth_test", module="google_auth")

def main():
    try:
        logger.info("Testing auth config loading...")
        auth_config = load_auth_config()
        
        if not auth_config:
            logger.error("❌ Failed to load auth config")
            return False
            
        logger.info("✅ Auth config loaded successfully")
        
        # Test drive service
        logger.info("Testing Google Drive service creation...")
        drive_service = get_service("drive", "v3")
        
        if drive_service:
            logger.info("✅ Drive service created successfully!")
            # Try a simple API call to test authentication
            about = drive_service.about().get(fields="user").execute()
            logger.info(f"Authenticated as: {about['user']['emailAddress']}")
            return True
        else:
            logger.error("❌ Failed to create Drive service")
            return False
            
    except Exception as e:
        logger.exception(f"Error testing auth: {e}")
        return False

if __name__ == "__main__":
    main() 