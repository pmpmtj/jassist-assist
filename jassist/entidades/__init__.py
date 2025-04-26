"""
Entidades Module

This module processes text entries to identify entities.
"""

from .entidades_processor import process_entity_entry

def extract_entities(text: str, db_id=None):
    """
    Process a text entry for entity extraction.
    
    Args:
        text: The text entry
        db_id: Optional database ID of the transcription
        
    Returns:
        bool: True if processing was successful, False otherwise
    """
    success, _ = process_entity_entry(text, db_id)
    return success 