"""
JSON extraction utilities for task processing.

This module extracts structured JSON data from text responses.
"""

import json
import re
from typing import Dict, Any, Optional

from jassist.logger_utils.logger_utils import setup_logger

logger = setup_logger("json_extractor", module="tarefas")

def extract_json_from_text(text: str) -> Optional[Dict[str, Any]]:
    """
    Extract a JSON object from text, handling different formats.
    
    Args:
        text: The text to extract JSON from
        
    Returns:
        Dict: The extracted JSON object, or None if extraction failed
    """
    if not text:
        logger.error("No text provided for JSON extraction")
        return None
        
    try:
        # Try direct JSON parsing first
        try:
            parsed_json = json.loads(text)
            logger.debug("Successfully parsed text as direct JSON")
            return parsed_json
        except json.JSONDecodeError as e:
            logger.debug(f"Direct JSON parsing failed: {e.msg} at line {e.lineno}, column {e.colno}")

        # Try to extract code blocks with ```json syntax
        json_block_matches = re.findall(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
        if json_block_matches:
            logger.debug(f"Found {len(json_block_matches)} potential JSON code blocks")
            for i, match in enumerate(json_block_matches):
                try:
                    parsed_json = json.loads(match)
                    logger.debug(f"Successfully parsed JSON from code block #{i+1}")
                    return parsed_json
                except json.JSONDecodeError as e:
                    logger.debug(f"Code block #{i+1} parsing failed: {e.msg} at line {e.lineno}, column {e.colno}")
        else:
            logger.debug("No JSON code blocks found in text")

        # Try to find anything between curly braces
        curly_match = re.search(r'({[\s\S]*})', text)
        if curly_match:
            try:
                curly_content = curly_match.group(1)
                logger.debug(f"Found content between curly braces (length: {len(curly_content)})")
                parsed_json = json.loads(curly_content)
                logger.debug("Successfully parsed JSON from curly braces content")
                return parsed_json
            except json.JSONDecodeError as e:
                logger.debug(f"Curly braces content parsing failed: {e.msg} at line {e.lineno}, column {e.colno}")
        else:
            logger.debug("No content between curly braces found in text")

        # If we get here, we've tried all extraction methods and failed
        logger.error("Failed to extract valid JSON from text with any method")
        # Log a snippet of the text for debugging (avoid logging massive text)
        text_sample = text[:100] + "..." if len(text) > 100 else text
        logger.debug(f"Text sample: {text_sample}")
        return None
        
    except Exception as e:
        logger.error(f"Unexpected error during JSON extraction: {e}")
        return None 