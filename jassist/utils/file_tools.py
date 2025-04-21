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