#!/usr/bin/env python
"""
Contas CLI Module

This module provides a command-line interface and programmatic API
for processing financial transactions.
"""

import sys
import json
import argparse
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, Union
from datetime import datetime

from jassist.logger_utils.logger_utils import setup_logger

# Set up logger
logger = setup_logger("contas_cli", module="contas")

def parse_contas_text(input_text: str, transcription_id: Optional[int] = None, 
                     test_mode: bool = False) -> Tuple[bool, Dict[str, Any]]:
    """
    Parse financial transaction text and return structured data.
    
    This function can be imported and used programmatically.
    
    Args:
        input_text: The text to parse for transaction information
        transcription_id: Optional ID of associated transcription record
        test_mode: If True, skips database operations (for testing)
        
    Returns:
        Tuple containing (success status, transaction data or error info)
    """
    try:
        logger.debug(f"Processing transaction text: {input_text[:50]}...")
        
        if test_mode:
            logger.debug("Running in test mode, skipping assistant processing")
            
            # For test mode, create a mock response to avoid API calls
            # This helps to test the pipeline without needing API credentials
            mock_response = {
                "tipo_lancamento": "despesa",
                "valor": 25.99,
                "moeda": "EUR",
                "nota": "Teste de transação - " + input_text[:30],
                "data": datetime.now().isoformat()
            }
            
            logger.debug(f"Generated mock transaction data: {mock_response}")
            return True, mock_response
        else:
            # Import here to avoid circular imports
            from jassist.contas.contas_processor import process_transaction_entry
            
            try:
                # Process the entry
                success, transaction_data = process_transaction_entry(
                    text=input_text, 
                    db_id=transcription_id
                )
                
                if not success:
                    logger.error("Failed to process transaction entry")
                    if isinstance(transaction_data, dict) and "error" in transaction_data:
                        return False, transaction_data
                    return False, {"error": "Failed to process transaction entry"}
                    
                return True, transaction_data
            except Exception as e:
                import traceback
                error_traceback = traceback.format_exc()
                logger.error(f"Exception in process_transaction_entry: {e}\n{error_traceback}")
                return False, {"error": str(e), "traceback": error_traceback}
        
    except Exception as e:
        import traceback
        error_traceback = traceback.format_exc()
        logger.exception(f"Error parsing transaction text: {e}")
        return False, {"error": str(e), "traceback": error_traceback}

def main():
    """
    Main entry point for the CLI.
    """
    parser = argparse.ArgumentParser(description="Process financial transactions from text input")
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
    success, result = parse_contas_text(
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
