"""
agenda package for jassist_rebuild.

This package provides functionality for processing agenda entries.
"""

from pathlib import Path
import sys

# Ensure the package directory is in the path
PACKAGE_DIR = Path(__file__).resolve().parent
if str(PACKAGE_DIR) not in sys.path:
    sys.path.append(str(PACKAGE_DIR.parent))

# Export the main functions
from jassist.agenda.agenda_processor import process_agenda_entry
from jassist.logger_utils.logger_utils import setup_logger

def insert_into_agenda(text: str, db_id: int = None) -> bool:
    """
    Process a voice entry for agenda insertion.
    
    This is the main entry point for the agenda module, 
    designed to be called from the route_transcription module.
    
    Args:
        text: The voice entry text
        db_id: Optional database ID of the transcription
        
    Returns:
        bool: True if processing was successful, False otherwise
    """
    # Get logger instance
    logger = setup_logger("agenda", module="agenda")
    
    # Process the entry
    success, _ = process_agenda_entry(text, db_id)
    return success

# Initialize logging when the package is imported
logger = setup_logger("agenda_init", module="agenda")

 