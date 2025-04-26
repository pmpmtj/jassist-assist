"""
Pipeline Module

Connects and executes the following modules in sequence:
1. Download - downloads audio files from Google Drive
2. Transcribe - transcribes audio files to text
3. Classify - classifies the transcribed text
4. Route - routes the classified text to the appropriate module

This pipeline does not create additional configurations, as all modules
are self-contained with their own configurations.
"""

import sys
import json
from pathlib import Path
from typing import Dict, Any, List, Optional

from jassist.download_gdrive.gdrive_downloader import run_download
from jassist.download_gdrive.config_loader import load_config as load_download_config
from jassist.transcribe.transcribe_cli import main as transcribe_main
from jassist.classification.classification_processor import classify_text
from jassist.router.router_cli import route_to_module, parse_classification_result
from jassist.logger_utils.logger_utils import setup_logger
from jassist.utils.path_utils import resolve_path, ensure_directory_exists

# Set up logger for the pipeline
logger = setup_logger("pipeline", module="pipeline")

def extract_category_from_classification(classification_result: str) -> Optional[Dict[str, Any]]:
    """
    Extract category from the classification result, handling the nested structure.
    
    Args:
        classification_result: The raw classification result string
        
    Returns:
        Dict with category and other metadata, or None if parsing failed
    """
    try:
        # Try to parse the result as JSON
        data = json.loads(classification_result)
        logger.debug("Successfully parsed classification result as JSON")
        
        # Check if it has the nested structure with "classifications" array
        if "classifications" in data and isinstance(data["classifications"], list) and len(data["classifications"]) > 0:
            # Get the first classification item
            first_classification = data["classifications"][0]
            
            # Extract the category
            if "category" in first_classification:
                # Create a new dict with the category at the top level for router compatibility
                result = {
                    "category": first_classification["category"],
                    "text": first_classification.get("text", ""),
                    # Include the original data for reference
                    "raw_data": data
                }
                logger.debug(f"Extracted category '{result['category']}' from nested classification")
                return result
        
        # If we couldn't find the nested structure, try the parse_classification_result from router
        # This serves as a fallback for other formats
        logger.debug("No nested structure found, using router's parser as fallback")
        return parse_classification_result(classification_result)
        
    except json.JSONDecodeError:
        logger.debug("Classification result is not valid JSON, using router's parser")
        return parse_classification_result(classification_result)
    except Exception as e:
        logger.error(f"Error parsing classification result: {e}")
        return None

def run_pipeline() -> bool:
    """
    Run the entire pipeline from download to routing.
    
    Returns:
        bool: True if the pipeline ran successfully, False otherwise
    """
    logger.info("Starting pipeline execution")
    
    # Step 1: Download files from Google Drive
    logger.info("STEP 1: Downloading files from Google Drive")
    
    # Get the path to the download config file
    script_dir = Path(__file__).resolve().parent
    download_config_path = resolve_path("../download_gdrive/config/download_gdrive_config.json", script_dir)
    
    logger.debug(f"Using download config from: {download_config_path}")
    download_config = load_download_config(config_path=download_config_path)
    download_success = run_download(download_config)
    
    if not download_success:
        logger.error("Download step failed, stopping pipeline")
        return False
    
    logger.info("Download completed successfully")
    
    # Step 2: Transcribe the downloaded audio files
    logger.info("STEP 2: Transcribing audio files")
    # transcribe_main runs the entire transcription process
    transcribe_main()
    
    # Get the path to the transcription output directory from the last step
    script_dir = Path(__file__).resolve().parent
    voice_diary_dir = script_dir.parent
    transcriptions_dir = resolve_path("transcriptions", voice_diary_dir)
    
    # Check if any transcriptions were generated
    if not transcriptions_dir.exists() or not any(transcriptions_dir.glob("*.txt")):
        logger.error("No transcriptions generated, stopping pipeline")
        return False
    
    logger.info("Transcription completed successfully")
    
    # Step 3: Process each transcription file
    transcription_files = list(transcriptions_dir.glob("*.txt"))
    logger.info(f"STEP 3: Processing {len(transcription_files)} transcription files")
    
    success_count = 0
    for transcription_file in transcription_files:
        try:
            logger.info(f"Processing transcription file: {transcription_file.name}")
            
            # Read the transcription content
            with open(transcription_file, "r", encoding="utf-8") as f:
                transcription_content = f.read()
            
            # Step 3: Classify the text
            logger.info(f"Classifying content from: {transcription_file.name}")
            classification_result = classify_text(transcription_content, response_format="json")
            
            if not classification_result:
                logger.error(f"Classification failed for file: {transcription_file.name}")
                continue
            
            # Parse the classification result with our specialized function
            parsed_result = extract_category_from_classification(classification_result)
            
            if not parsed_result or "category" not in parsed_result:
                logger.error(f"Failed to parse classification result for file: {transcription_file.name}")
                continue
            
            # Extract transcription ID from filename format: timestamp_original_filename.txt
            # For example: 20250426_102643_865908_20250426_102638_253758_Rua Diogo Domingos Alves.txt
            # Here we want to find the corresponding record in the database
            try:
                from jassist.db_utils.db_connection import db_connection_handler
                
                @db_connection_handler
                def find_transcription_id_by_filename(conn, filename: str) -> Optional[int]:
                    try:
                        # Since filenames follow a pattern with timestamp_original, we can check if the file
                        # contains the original filename pattern
                        cur = conn.cursor()
                        # Look for records that might match this filename
                        cur.execute("""
                            SELECT id FROM transcricoes
                            WHERE id = (
                                SELECT MAX(id) FROM transcricoes
                                WHERE etiqueta = 'transcricao_bruta'
                                  AND NOT processado
                            )
                        """)
                        result = cur.fetchone()
                        return result[0] if result else None
                    except Exception as e:
                        logger.error(f"Error finding transcription ID: {e}")
                        return None
                
                # Get DB ID for this transcription
                db_id = find_transcription_id_by_filename(transcription_file.name)
                if db_id:
                    logger.debug(f"Found transcription ID in database: {db_id}")
                    # Add the ID to the metadata
                    if not "db_id" in parsed_result:
                        parsed_result["db_id"] = db_id
                else:
                    logger.warning(f"Could not find transcription ID for file: {transcription_file.name}")
            except Exception as e:
                logger.warning(f"Error looking up transcription ID: {e}")
            
            # Step 4: Route the text to the appropriate module
            category = parsed_result["category"]
            logger.info(f"Routing to category: {category}")
            
            # Route to the appropriate module
            routing_success = route_to_module(
                category=category,
                input_data=transcription_content,
                metadata=parsed_result
            )
            
            if routing_success:
                logger.info(f"Successfully processed file: {transcription_file.name}")
                success_count += 1
            else:
                logger.error(f"Routing failed for file: {transcription_file.name}")
            
        except Exception as e:
            logger.error(f"Error processing file {transcription_file.name}: {e}", exc_info=True)
    
    # Pipeline summary
    logger.info(f"Pipeline completed: {success_count}/{len(transcription_files)} files processed successfully")
    return success_count > 0

def main():
    """
    Main entry point for running the pipeline from CLI.
    """
    try:
        logger.info("Starting pipeline from CLI")
        result = run_pipeline()
        
        if result:
            logger.info("Pipeline completed successfully")
            return 0
        else:
            logger.error("Pipeline failed")
            return 1
    
    except Exception as e:
        logger.error(f"Unhandled exception in pipeline: {e}", exc_info=True)
        return 1

if __name__ == "__main__":
    sys.exit(main())
