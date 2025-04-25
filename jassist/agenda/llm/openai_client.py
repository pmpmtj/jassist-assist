"""
OpenAI client for agenda processing.

This module handles interactions with the OpenAI API.
"""

import os
from datetime import datetime
from jassist.api_assistants_cliente.adapters.agenda_adapter import process_with_agenda_assistant
from jassist.logger_utils.logger_utils import setup_logger

logger = setup_logger("openai_client", module="agenda")

def process_with_openai_assistant(entry_content: str) -> str:
    """
    Process a agenda entry using OpenAI's assistant API.
    
    Args:
        entry_content: The agenda entry text to process
        
    Returns:
        str: The assistant's response
    """
    # Use the centralized assistant client through the agenda adapter
    response = process_with_agenda_assistant(entry_content)
    
    if not response:
        raise ValueError("No assistant response found")
    
    return response 