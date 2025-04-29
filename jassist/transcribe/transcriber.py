import json
import time
from pathlib import Path
from typing import Any, Dict, Optional, Union
from jassist.transcribe.audio_files_processor import calculate_duration
from jassist.transcribe.model_handler import get_transcription_model
from jassist.logger_utils.logger_utils import setup_logger
from jassist.utils.path_utils import resolve_path

logger = setup_logger("transcriber", module="transcribe")

def transcribe_file(
    client: Any,
    file_path: Union[str, Path],
    config: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """
    Transcribe a single audio file using OpenAI and return the full response JSON.
    """
    # Ensure file_path is a Path object
    file_path = resolve_path(file_path)
    
    if not client:
        logger.error("No OpenAI client provided.")
        return None

    logger.info(f"Beginning transcription for: {file_path.name}")
    
    # Only perform expensive JSON serialization if debug logging is enabled
    if logger.isEnabledFor(10):  # DEBUG level is 10
        logger.debug(f"Using configuration: {json.dumps({k: v for k, v in config.items() if k != 'model'}, default=str)}")
    
    duration = calculate_duration(file_path)
    logger.info(f"Estimated duration: {duration:.2f} seconds")

    # Get cost management settings
    cost_config = config.get("cost_management", {})
    max_duration = cost_config.get("max_audio_duration_seconds", 300)
    warn_on_large = cost_config.get("warn_on_large_files", True)
    
    # Only warn if configured to do so
    if duration and duration > max_duration and warn_on_large:
        logger.warning(f"Audio exceeds max allowed ({max_duration}s). Proceeding with caution...")

    # Get model configuration once and extract all needed values
    model_config = config.get("model", {})
    model_name = get_transcription_model(config)
    language = model_config.get("language")
    prompt = model_config.get("prompt")
    response_format = model_config.get("response_format", "json")

    logger.debug(f"Using model: {model_name}")
    if prompt:
        logger.debug(f"Using prompt: {prompt}")
    if language:
        logger.debug(f"Using language: {language}")
    logger.debug(f"Using response format: {response_format}")

    try:
        start_time = time.time()
        with open(file_path, "rb") as audio_file:
            # Build parameters dictionary with only valid parameters
            params = {
                "model": model_name,
                "file": audio_file,
                "response_format": response_format
            }

            if prompt:
                params["prompt"] = prompt
            if language:
                params["language"] = language

            logger.debug(f"Calling OpenAI API with parameters: {', '.join([f'{k}={v if k != 'file' else 'FILE_CONTENT'}' for k, v in params.items()])}")
            response = client.audio.transcriptions.create(**params)

        end_time = time.time()
        time_diff = end_time - start_time
        # Avoid division by zero
        if duration and time_diff > 0:
            speed = duration / time_diff
            logger.info(f"Transcription done in {time_diff:.2f}s ({speed:.2f}x real-time)")
        else:
            logger.info(f"Transcription completed in {time_diff:.2f}s")

        # Return response as dictionary (handles both pydantic and dict responses)
        result = response.model_dump() if hasattr(response, 'model_dump') else response
        logger.debug(f"Received transcription with {len(result.get('text', '')) if isinstance(result, dict) else 0} characters")
        return result

    except Exception as e:
        logger.error(f"Transcription failed: {e}", exc_info=True)
        return None
