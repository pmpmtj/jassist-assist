"""
File operation utilities for the jassist application.
"""

import os
import logging
from pathlib import Path
from jassist.logger_utils.logger_utils import setup_logger

logger = setup_logger("file_tools", module="utils")

def clean_directory(directory_path: str | Path) -> dict:
    """
    Deletes all files in the specified directory.
    
    Args:
        directory_path (str | Path): Path to the directory to clean
        
    Returns:
        dict: Result of the operation with status and message
    """
    try:
        # Convert to Path object if string
        directory = Path(directory_path) if isinstance(directory_path, str) else directory_path
        
        # Verify the directory exists
        if not directory.exists():
            return {
                "status": "error",
                "message": f"Directory does not exist: {directory}"
            }
        
        # Verify it's a directory
        if not directory.is_dir():
            return {
                "status": "error",
                "message": f"Not a directory: {directory}"
            }
        
        # Count files before deletion
        files = [f for f in directory.iterdir() if f.is_file()]
        file_count = len(files)
        
        # Delete all files
        deleted_count = 0
        for file_path in files:
            try:
                file_path.unlink()
                deleted_count += 1
                logger.info(f"Deleted file: {file_path}")
            except Exception as e:
                logger.error(f"Failed to delete file {file_path}: {str(e)}")
        
        return {
            "status": "success",
            "message": f"Cleaned directory: {directory}",
            "files_found": file_count,
            "files_deleted": deleted_count
        }
    
    except Exception as e:
        logger.error(f"Error cleaning directory {directory_path}: {str(e)}")
        return {
            "status": "error",
            "message": f"Error cleaning directory: {str(e)}"
        }

def ensure_file_exists(file_path: str | Path, default_content: dict = None) -> dict:
    """
    Ensures a JSON file exists at the given path. If not, creates it with default content.
    
    Args:
        file_path (str | Path): Path to the JSON file
        default_content (dict, optional): Default content to write if file doesn't exist
        
    Returns:
        dict: Result of the operation with status and message
    """
    import json
    
    try:
        # Convert to Path object if string
        path = Path(file_path) if isinstance(file_path, str) else file_path
        
        # Create parent directories if they don't exist
        path.parent.mkdir(parents=True, exist_ok=True)
        
        # Check if file exists
        if not path.exists():
            logger.info(f"File does not exist, creating: {path}")
            
            # Write default content
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(default_content or {}, f, indent=2)
                
            return {
                "status": "success",
                "message": f"Created file with default content: {path}",
                "created": True
            }
        
        return {
            "status": "success",
            "message": f"File already exists: {path}",
            "created": False
        }
        
    except Exception as e:
        logger.error(f"Error ensuring file exists {file_path}: {str(e)}")
        return {
            "status": "error",
            "message": f"Error ensuring file exists: {str(e)}"
        } 