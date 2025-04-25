import logging
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
    duration = calculate_duration(file_path)
    logger.info(f"Estimated duration: {duration:.2f} seconds")

    max_duration = config.get("cost_management", {}).get("max_audio_duration_seconds", 300)
    if duration and duration > max_duration:
        logger.warning(f"Audio exceeds max allowed ({max_duration}s). Proceeding with caution...")

    model_name = get_transcription_model(config)
    model_config = config.get("model", {})
   
    language = model_config.get("language") 
    prompt = model_config.get("prompt") 
    # Prioritize model-specific response_format over default
    response_format = model_config.get("response_format") 

    logger.info(f"Using model: {model_name}")
    if prompt:
        logger.info(f"Using prompt: {prompt}")
    logger.info(f"Using response format: {response_format}")

    try:
        start_time = time.time()
        with open(file_path, "rb") as audio_file:
            params = {
                "model": model_name,
                "file": audio_file,
                "response_format": response_format
            }

            if prompt:
                params["prompt"] = prompt
            if language:
                params["language"] = language

            response = client.audio.transcriptions.create(**params)

        end_time = time.time()
        time_diff = end_time - start_time
        # Avoid division by zero
        if time_diff > 0:
            speed = duration / time_diff if duration else 0
            logger.info(f"Transcription done in {time_diff:.2f}s ({speed:.2f}x real-time)")
        else:
            logger.info(f"Transcription completed instantly")

        # Return raw dict (OpenAI Object is pydantic-based)
        if hasattr(response, 'model_dump'):
            return response.model_dump()
        return response

    except Exception as e:
        logger.error(f"Transcription failed: {e}", exc_info=True)
        return None
