#!/usr/bin/env python
"""
Router CLI

Command-line utility for routing classified text to the appropriate processing module.
Takes the output from classification_cli.py and routes it to the corresponding module
based on the category determined by the classification.
"""

import sys
import json
import argparse
from pathlib import Path
import importlib
from typing import Dict, Any, Optional, Union

from jassist.logger_utils.logger_utils import setup_logger
from jassist.utils.path_utils import resolve_path

# Configure logger
logger = setup_logger("router_cli", module="router")

# Path to router config
SCRIPT_DIR = Path(__file__).resolve().parent
CONFIG_PATH = resolve_path("config/router_config.json", SCRIPT_DIR)

def load_config() -> Dict[str, Any]:
    """
    Load router configuration from JSON file.
    
    Returns:
        Dict containing the router configuration
    """
    try:
        if not Path(CONFIG_PATH).exists():
            logger.error(f"Router config file not found: {CONFIG_PATH}")
            return {
                "module_mapping": {},
                "debug_mode": False
            }
            
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            config = json.load(f)
            logger.debug(f"Loaded router configuration from {CONFIG_PATH}")
            return config
    except Exception as e:
        logger.error(f"Error loading router config: {e}")
        # Return a minimal default configuration
        return {
            "module_mapping": {},
            "debug_mode": False
        }

def parse_classification_result(result: str) -> Optional[Dict[str, Any]]:
    """
    Parse the classification result to determine the category and other metadata.
    
    Args:
        result: The classification result as string (JSON or structured text)
        
    Returns:
        Dict containing category and other metadata, or None if parsing failed
    """
    try:
        # Log the raw input
        logger.debug(f"Raw classification result: {result[:200]}...")
        
        # Extract JSON from markdown code blocks if present
        if "```json" in result:
            logger.debug("Detected markdown JSON code block, extracting JSON content")
            start_marker = "```json"
            end_marker = "```"
            start_pos = result.find(start_marker) + len(start_marker)
            end_pos = result.find(end_marker, start_pos)
            if start_pos > len(start_marker) - 1 and end_pos > start_pos:
                result = result[start_pos:end_pos].strip()
                logger.debug(f"Extracted JSON: {result[:200]}...")
        
        # Try parsing as JSON
        try:
            data = json.loads(result)
            logger.debug(f"Successfully parsed JSON data")
            
            # Handle nested classifications structure
            if "classifications" in data and isinstance(data["classifications"], list) and data["classifications"]:
                classification_entry = data["classifications"][0]
                if "category" in classification_entry:
                    return {
                        "category": classification_entry["category"],
                        "text": classification_entry.get("text", ""),
                        "original_data": data
                    }
            
            # If we have a category directly in the data, use it
            if "category" in data:
                return data
                
            # No recognized structure - log warning
            logger.warning("JSON structure doesn't contain expected category field")
            return data  # Return what we have and let caller handle missing category
            
        except json.JSONDecodeError:
            logger.debug("Classification result is not valid JSON, trying text parsing")
        
        # If not JSON, try to parse as text
        lines = result.strip().split('\n')
        data = {}
        
        for line in lines:
            if ':' in line:
                key, value = [part.strip() for part in line.split(':', 1)]
                data[key.lower()] = value
        
        # Look for category in various field names
        category_fields = ['category', 'type', 'classificação', 'categoria', 'tipo']
        for field in category_fields:
            if field in data:
                data['category'] = data[field]
                break
        
        logger.debug(f"Parsed classification result: {data}")
        return data
        
    except Exception as e:
        logger.error(f"Error parsing classification result: {str(e)}")
        logger.debug("Exception details", exc_info=True)
        return None

def route_to_module(category: str, input_data: str, metadata: Dict[str, Any]) -> bool:
    """
    Route the input data to the appropriate module based on the category.
    
    Args:
        category: The determined category from classification
        input_data: The original input text
        metadata: Additional metadata from classification
        
    Returns:
        True if routing was successful, False otherwise
    """
    config = load_config()
    module_mapping = config.get("module_mapping", {})
    debug_mode = config.get("debug_mode", False)
    
    # Normalize category name (lowercase, remove accents, etc.)
    normalized_category = category.lower().strip()
    
    # Find the module path for this category
    module_path = None
    matched_category = None
    
    # Try exact match first, then partial match
    if normalized_category in module_mapping:
        module_path = module_mapping[normalized_category]
        matched_category = normalized_category
        logger.debug(f"Found exact category match: {normalized_category}")
    else:
        # Try partial matching
        for key, path in module_mapping.items():
            if key.lower() in normalized_category or normalized_category in key.lower():
                module_path = path
                matched_category = key
                logger.debug(f"Found partial category match: {key} for input: {normalized_category}")
                break
    
    # No mapping found - log and return failure
    if not module_path:
        logger.error(f"No module mapping found for category: {category}")
        return False
    
    logger.info(f"Routing to module: {module_path} for category: {category} (matched: {matched_category})")
    
    try:
        # Split the module path into module and function parts
        module_parts = module_path.split('.')
        function_name = module_parts.pop()
        module_import_path = '.'.join(module_parts)
        
        # Import the module
        logger.debug(f"Importing module: {module_import_path}")
        module = importlib.import_module(module_import_path)
        
        # Get the function
        process_function = getattr(module, function_name)
        
        # Call the processing function with the input and metadata
        logger.debug(f"Calling {function_name} with input data and metadata")
        if debug_mode:
            logger.debug(f"Debug mode ON - would call {module_path} with metadata: {metadata}")
            return True
            
        result = process_function(input_data, metadata)
        logger.info(f"Successfully processed data with {module_path}")
        return True
        
    except ImportError as e:
        logger.error(f"Failed to import module {module_import_path}: {e}")
        return False
    except AttributeError as e:
        logger.error(f"Function {function_name} not found in module {module_import_path}: {e}")
        return False
    except Exception as e:
        logger.error(f"Error routing to module {module_path}: {e}")
        logger.debug("Exception details", exc_info=True)
        return False

def read_from_file_or_string(content: str, is_file: bool) -> str:
    """
    Read content from a file if is_file is True, otherwise return the content as is.
    
    Args:
        content: File path or string content
        is_file: Whether the content is a file path
        
    Returns:
        The read content as string
    """
    if is_file:
        logger.info(f"Reading from file: {content}")
        with open(content, "r", encoding="utf-8") as f:
            return f.read()
    return content

def main():
    """
    Entry point for the router CLI.
    """
    parser = argparse.ArgumentParser(description="Router for classified text")
    parser.add_argument("--input", "-i", help="Input classification result or file path")
    parser.add_argument("--file", "-f", action="store_true", help="Input is a file path")
    parser.add_argument("--original", "-o", help="Original text input or file path")
    parser.add_argument("--original-file", "-of", action="store_true", help="Original input is a file path")
    
    args = parser.parse_args()
    
    try:
        # Get classification result from file, argument, or stdin
        if args.input:
            classification_result = read_from_file_or_string(args.input, args.file)
        else:
            logger.info("Reading classification from stdin...")
            classification_result = sys.stdin.read()
        
        # Get original text if provided
        original_text = None
        if args.original:
            original_text = read_from_file_or_string(args.original, args.original_file)
        
        # Parse the classification result
        classification_data = parse_classification_result(classification_result)
        
        if not classification_data:
            logger.error("Failed to parse classification result")
            print("Error: Failed to parse classification result", file=sys.stderr)
            return 1
        
        # Get the category from the classification
        category = classification_data.get("category")
        if not category:
            logger.error("No category found in classification result")
            print("Error: No category found in classification result", file=sys.stderr)
            return 1
        
        logger.info(f"Determined category: {category}")
        
        # Use the original text if provided, otherwise use the text from classification data if available
        input_data = original_text
        if not input_data:
            input_data = classification_data.get("text", classification_result)
        
        # Route to the appropriate module
        success = route_to_module(category, input_data, classification_data)
        
        if success:
            logger.info("Successfully routed and processed data")
            return 0
        else:
            logger.error("Failed to route and process data")
            print("Error: Failed to route and process data", file=sys.stderr)
            return 1
    
    except Exception as e:
        logger.exception(f"Error during routing: {e}")
        print(f"Error: {e}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main())
