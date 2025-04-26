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

def insert_into_agenda(text: str, metadata=None) -> bool:
    """
    Process a voice entry for agenda insertion.
    
    This is the main entry point for the agenda module, 
    designed to be called from the route_transcription module.
    
    Args:
        text: The voice entry text
        metadata: Optional metadata from the router, may contain db_id
        
    Returns:
        bool: True if processing was successful, False otherwise
    """
    # Get logger instance
    logger = setup_logger("agenda", module="agenda")
    
    # Extract db_id from metadata if it exists
    db_id = None
    if isinstance(metadata, dict):
        if 'db_id' in metadata:
            db_id = metadata['db_id']
            logger.info(f"Found db_id in metadata: {db_id}")
        else:
            logger.warning(f"No db_id found in metadata: {metadata}")
    
    # Process the entry
    logger.info(f"Processing agenda entry with db_id: {db_id}")
    success, result = process_agenda_entry(text, db_id)
    
    if success:
        logger.info(f"Successfully processed agenda entry")
    else:
        logger.error(f"Failed to process agenda entry: {result}")
    
    return success

# Initialize logging when the package is imported
logger = setup_logger("agenda_init", module="agenda")

 