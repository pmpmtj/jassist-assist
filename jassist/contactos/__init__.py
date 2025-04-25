"""
Contacts Module

This module processes voice entries containing contact information.
"""

from .contactos_processor import process_contact_entry

def insert_into_contacts(text: str, db_id=None):
    """
    Process a voice entry for contacts insertion.
    
    Args:
        text: The voice entry text
        db_id: Optional database ID of the transcription
        
    Returns:
        bool: True if processing was successful, False otherwise
    """
    return process_contact_entry(text, db_id) 