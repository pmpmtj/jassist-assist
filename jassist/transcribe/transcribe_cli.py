import datetime
from pathlib import Path

from jassist.transcribe.config_loader import load_config, load_environment
from jassist.transcribe.model_handler import get_openai_client, get_transcription_model
from jassist.transcribe.audio_files_processor import get_audio_files, calculate_duration
from jassist.transcribe.transcriber import transcribe_file
from jassist.utils.file_tools import clean_directory
from jassist.logger_utils.logger_utils import setup_logger
from jassist.transcribe.db.transcribe_db import initialize_transcription_db, save_raw_transcription
from jassist.utils.path_utils import resolve_path

logger = setup_logger("transcribe_cli", module="transcribe")

def save_to_text_file(transcription: str, output_dir: Path, prefix: str):
    """Save transcription text to a file with timestamp in the filename."""
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        filename = f"{timestamp}_{prefix}.txt"
        output_path = output_dir / filename
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(transcription)
        logger.info(f"Transcription saved to: {output_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to save transcription to file: {e}")
        return False

def main():
    logger.info("Starting transcription CLI...")

    # Step 1: Load config and env
    load_environment()
    config = load_config()

    # Get the model name that will be used for transcription
    model_name = get_transcription_model(config)
    logger.info(f"Using transcription model: {model_name}")

    # Step 2: Initialize OpenAI
    client = get_openai_client()
    if not client:
        logger.error("Cannot continue without OpenAI client.")
        return
    
    # Step 3: Initialize database
    if not initialize_transcription_db():
        logger.error("Failed to initialize database.")
        return

    # Step 4: Resolve paths
    script_dir = Path(__file__).resolve().parent
    voice_diary_dir = script_dir.parent

    # Hardcoded downloads directory path (design decision)
    downloads_dir = "downloaded"
    logger.info(f"Using hardcoded downloads directory: {downloads_dir}")
    
    # Get output directory from transcribe config's paths section
    output_dir_config = config.get("paths", {}).get("output_dir", "transcriptions")
    
    # Create absolute paths using the consistent resolver function
    downloads_dir = resolve_path(downloads_dir, voice_diary_dir)
    output_dir = resolve_path(output_dir_config, voice_diary_dir)
    
    logger.info(f"Using downloads directory: {downloads_dir}")
    logger.info(f"Using output directory: {output_dir}")

    # Verify the downloads directory exists
    if not downloads_dir.exists():
        logger.error(f"Downloads directory not found: {downloads_dir}. Cannot continue.")
        return

    # Step 5: Get files
    files = get_audio_files(downloads_dir)
    if not files:
        logger.warning("No audio files found.")
        return

    successful = 0
    failed = 0

    # Step 6: Process each file
    for file_path in files:
        logger.info(f"Processing file: {file_path.name}")
        try:
            duration = calculate_duration(file_path) or 0.0
            
            transcription = transcribe_file(client, file_path, config)
            if not transcription:
                logger.error(f"Failed to transcribe file: {file_path.name}")
                failed += 1
                continue

            # Get the text from the transcription
            transcription_text = transcription.get("text", "") if isinstance(transcription, dict) else transcription
            
            # Save raw transcription to database
            try:
                raw_db_id = save_raw_transcription(
                    conteudo=transcription_text,
                    nome_ficheiro=file_path.name,
                    caminho_audio=str(file_path),
                    duracao_segundos=duration,
                    modelo_usado=model_name
                )
                
                if not raw_db_id:
                    logger.error("Failed to save raw transcription to database.")
            except Exception as e:
                logger.error(f"Error saving raw transcription to database: {e}")
                # Continue processing even if database save fails
            
            # Save to text file
            if save_to_text_file(transcription_text, output_dir, file_path.stem):
                successful += 1
                logger.info(f"File processed successfully: {file_path.name}")
            else:
                logger.warning(f"Continuing processing despite file save error for {file_path.name}")
            
        except Exception as e:
            logger.error(f"Unhandled error processing file {file_path.name}: {e}")
            failed += 1

    # Step 7: Summary
    total = successful + failed
    logger.info(f"Completed {total} file(s): {successful} successful, {failed} failed.")

    # Step 8: Clean the downloads directory after processing
    if files:  # Only clean if there were files to process
        try:
            logger.info("Cleaning downloads directory...")
            clean_result = clean_directory(downloads_dir)
            if clean_result["status"] == "success":
                logger.info(f"{clean_result.get('files_deleted', 0)} files deleted from downloads directory.")
            else:
                logger.error(f"Failed to clean downloads directory: {clean_result.get('message', 'Unknown error')}")
        except Exception as e:
            logger.error(f"Error during downloads directory cleanup: {e}")

if __name__ == "__main__":
    main()
