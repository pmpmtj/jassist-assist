import logging
import os
from typing import Optional, Dict, Any
from jassist.logger_utils.logger_utils import setup_logger

logger = setup_logger("model_handler", module="transcribe")

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

def get_transcription_model(config: Dict[str, Any]) -> str:
    """
    Get the transcription model from the config file.
    """
    fallback_model = "gpt-4o-mini-transcribe"
    
    logger.info("Fetching transcription model from config...")
    
    model_config = config.get("model", {})
    if not model_config:
        logger.warning("No model defined in config. Using fallback model.")
        return fallback_model
    
    model_name = model_config.get("name", fallback_model)
    logger.info(f"Using model: {model_name}")
    return model_name

def get_openai_client() -> Optional["OpenAI"]:
    """
    Create and return an OpenAI client using API key from environment.
    """
    if not OPENAI_AVAILABLE:
        logger.error("OpenAI Python library is not installed. Install with `pip install openai`.")
        return None

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        logger.error("Missing OPENAI_API_KEY in environment.")
        return None

    try:
        client = OpenAI(api_key=api_key)
        logger.info("OpenAI client successfully initialized.")
        return client
    except Exception as e:
        logger.error(f"Failed to initialize OpenAI client: {e}")
        return None
