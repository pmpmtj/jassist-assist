#!/usr/bin/env python
"""
Contactos CLI Module

This module provides a command-line interface and programmatic API
for processing contact entries.
"""

import sys
import json
import argparse
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, Union

from jassist.logger_utils.logger_utils import setup_logger

# Set up logger
logger = setup_logger("contactos_cli", module="contactos")

def parse_contactos_text(input_text: str, transcription_id: Optional[int] = None, 
                        test_mode: bool = False) -> Tuple[bool, Dict[str, Any]]:
    """
    Parse contactos text and return structured data.
    
    This function can be imported and used programmatically.
    
    Args:
        input_text: The text to parse for contact information
        transcription_id: Optional ID of associated transcription record
        test_mode: If True, skips database operations (for testing)
        
    Returns:
        Tuple containing (success status, contact data or error info)
    """
    try:
        logger.debug(f"Processing contactos text: {input_text[:50]}...")
        
        if test_mode:
            logger.debug("Running in test mode, skipping assistant processing")
            
            # For test mode, create a mock response to avoid API calls
            # This helps to test the pipeline without needing API credentials
            mock_response = {
                "nome_proprio": "Pedro",
                "apelido": "Julio",
                "telefone": "923329862",
                "email": "",
                "nota": "Created in test mode"
            }
            
            logger.debug(f"Generated mock contact data: {mock_response}")
            return True, mock_response
            
            # The following code is disabled in test mode
            # Import here to avoid circular imports
            # from jassist.contactos.utils.json_extractor import extract_json_from_text
            # from jassist.contactos.contactos_processor import process_with_assistant
            # 
            # Process with OpenAI to extract contact data
            # response = process_with_assistant(input_text)
            # 
            # Extract JSON from response
            # contact_data = extract_json_from_text(response)
            # if not contact_data:
            #     logger.error("Failed to extract JSON from LLM response")
            #     return False, {"error": "Failed to extract JSON from LLM response"}
            #    
            # return True, contact_data
        else:
            # Import here to avoid circular imports
            from jassist.contactos.contactos_processor import process_contact_entry
            
            try:
                # Process the entry
                success, contact_data = process_contact_entry(
                    text=input_text, 
                    db_id=transcription_id
                )
                
                if not success:
                    logger.error("Failed to process contact entry")
                    if isinstance(contact_data, dict) and "error" in contact_data:
                        return False, contact_data
                    return False, {"error": "Failed to process contact entry"}
                    
                return True, contact_data
            except Exception as e:
                import traceback
                error_traceback = traceback.format_exc()
                logger.error(f"Exception in process_contact_entry: {e}\n{error_traceback}")
                return False, {"error": str(e), "traceback": error_traceback}
        
    except Exception as e:
        import traceback
        error_traceback = traceback.format_exc()
        logger.exception(f"Error parsing contactos text: {e}")
        return False, {"error": str(e), "traceback": error_traceback}

def main():
    """
    Main entry point for the CLI.
    """
    parser = argparse.ArgumentParser(description="Process contact entries from text input")
    parser.add_argument("--input", "-i", type=str, help="Text input to process")
    parser.add_argument("--file", "-f", type=str, help="File containing text to process")
    parser.add_argument("--id", type=int, help="Optional transcription ID", default=None)
    parser.add_argument("--output", "-o", type=str, help="Output file (default: stdout)")
    parser.add_argument("--pretty", "-p", action="store_true", help="Pretty-print JSON output")
    parser.add_argument("--test", "-t", action="store_true", help="Test mode (skips database operations)")
    parser.add_argument("--debug", "-d", action="store_true", help="Enable debug mode with more verbose logs")
    
    args = parser.parse_args()
    
    # Set up debug logging if requested
    if args.debug:
        import logging
        for handler in logger.handlers:
            handler.setLevel(logging.DEBUG)
        logger.setLevel(logging.DEBUG)
        logger.debug("Debug logging enabled")
    
    # Check for input source
    if args.input:
        input_text = args.input
    elif args.file:
        try:
            with open(args.file, 'r', encoding='utf-8') as f:
                input_text = f.read()
        except Exception as e:
            logger.error(f"Error reading input file: {e}")
            print(f"Error: Could not read input file: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        parser.print_help()
        sys.exit(1)
        
    # Process the text
    success, result = parse_contactos_text(
        input_text=input_text, 
        transcription_id=args.id,
        test_mode=args.test
    )
    
    # Format output
    indent = 2 if args.pretty else None
    output = json.dumps(result, indent=indent, ensure_ascii=False)
    
    # Write output
    if args.output:
        try:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(output)
        except Exception as e:
            logger.error(f"Error writing output file: {e}")
            print(f"Error: Could not write output file: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        print(output)
    
    # Set exit code based on success
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
