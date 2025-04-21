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

from jassist.google_auth.auth_manager import get_credentials
from jassist.logger_utils.logger_utils import setup_logger

logger = setup_logger("auth_test", module="google_auth")

def main():
    try:
        # Test auth config
        auth_cfg = {
            "credentials_path": "credentials",
            "credentials_file": "my_credentials.json",
            "token_file": "token.pickle"
        }
        
        # Test scopes
        scopes = ["https://www.googleapis.com/auth/drive"]
        
        logger.info("Testing credential loading...")
        creds = get_credentials(auth_cfg, scopes)
        
        if creds:
            logger.info("✅ Credentials loaded successfully!")
            logger.info(f"Token expiry: {creds.expiry}")
            return True
        else:
            logger.error("❌ Failed to load credentials")
            return False
            
    except Exception as e:
        logger.exception(f"Error testing credentials: {e}")
        return False

if __name__ == "__main__":
    main() 