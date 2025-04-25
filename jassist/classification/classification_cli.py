#!/usr/bin/env python
"""
Classification CLI

Command-line utility for classifying text using the classification module.
"""

import sys
import json
import argparse
from pathlib import Path
from typing import Optional, Dict, Any

from jassist.classification.classification_processor import classify_text
from jassist.logger_utils.logger_utils import setup_logger
from jassist.api_assistants_cliente.config_manager import cleanup_thread_config

# Configure logger to only log to file, not stdout
logger = setup_logger("classification_cli", module="classification")

def main():
    """
    Entry point for the classification CLI.
    """
    parser = argparse.ArgumentParser(description="Text classification utility")
    parser.add_argument("--input", "-i", help="Input text or file path")
    parser.add_argument("--file", "-f", action="store_true", help="Input is a file path")
    parser.add_argument("--output", "-o", help="Output file path")
    parser.add_argument("--json", "-j", action="store_true", 
                        help="Output in JSON format (overrides config setting)")
    parser.add_argument("--new-thread", "-n", action="store_true",
                        help="Force creation of a new thread instead of reusing existing ones")
    parser.add_argument("--no-thread-pool", action="store_true",
                        help="Disable thread pooling (may be slower but ensures fresh context)")
    parser.add_argument("--cleanup", action="store_true",
                        help="Clean up old thread entries from the config file (can be used alone)")
    parser.add_argument("--keep-days", type=int, default=7,
                        help="Number of days to keep thread entries (default: 7)")
    
    args = parser.parse_args()
    
    # Handle config cleanup request
    if args.cleanup:
        try:
            logger.info("Cleaning up thread entries from config file...")
            
            # Use direct file path to avoid module loading issues
            module_dir = Path(__file__).resolve().parent
            config_file = module_dir / "config" / "classification_assistant_config.json"
            
            if not config_file.exists():
                logger.warning(f"Config file not found: {config_file}")
                print(f"Config file not found: {config_file}")
            else:
                # Load the config file directly
                with open(config_file, "r", encoding="utf-8") as f:
                    config = json.load(f)
                
                # Look for temporary thread entries (with "new_" in the key)
                keys_to_remove = []
                for key in list(config.keys()):
                    if key.startswith("thread_id_") and "new_" in key and "_created_at" not in key:
                        keys_to_remove.append(key)
                        created_at_key = f"{key}_created_at"
                        if created_at_key in config:
                            keys_to_remove.append(created_at_key)
                
                # Remove the identified keys
                for key in keys_to_remove:
                    del config[key]
                
                # Save the updated config
                if keys_to_remove:
                    with open(config_file, "w", encoding="utf-8") as f:
                        json.dump(config, f, indent=2)
                    print(f"Successfully removed {len(keys_to_remove) // 2} temporary thread entries")
                    logger.info(f"Removed {len(keys_to_remove) // 2} temporary thread entries from config")
                else:
                    print("No temporary thread entries found")
                    logger.info("No temporary thread entries found")
            
            # If only cleanup was requested, exit
            if not args.input and not args.file:
                return 0
        except Exception as e:
            logger.error(f"Error cleaning up thread config: {e}")
            print(f"Error: Failed to clean up thread config: {e}", file=sys.stderr)
            # Continue with classification if requested
    
    try:
        # Get input text from file, argument, or stdin
        if args.file and args.input:
            logger.info(f"Reading from file: {args.input}")
            with open(args.input, "r", encoding="utf-8") as f:
                input_text = f.read()
        elif args.input:
            input_text = args.input
        elif not args.cleanup:  # Only try to read from stdin if not in cleanup-only mode
            logger.info("Reading from stdin...")
            input_text = sys.stdin.read()
        else:
            # No input text provided and in cleanup-only mode
            return 0
        
        # Classify the text
        logger.info("Processing classification...")
        
        # Command line argument --json overrides the config setting
        response_format = "json" if args.json else None
        result = classify_text(
            input_text, 
            response_format=response_format,
            force_new_thread=args.new_thread,
            use_thread_pool=not args.no_thread_pool
        )

        if result:
            # Output result
            if args.output:
                logger.info(f"Writing result to file: {args.output}")
                with open(args.output, "w", encoding="utf-8") as f:
                    f.write(result)
            else:
                # Print to stdout
                print("Start of result from classification_cli.py")
                print(result)
                print("End of result from classification_cli.py")
                
            logger.info("Classification completed successfully")
            return 0
        else:
            logger.error("Classification failed - no result returned")
            print("Error: Classification failed - no result returned", file=sys.stderr)
            return 1
            
    except Exception as e:
        logger.exception(f"Error during classification: {e}")
        print(f"Error: {e}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main()) 