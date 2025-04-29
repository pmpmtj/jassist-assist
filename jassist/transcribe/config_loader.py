import json
from pathlib import Path
from typing import Dict, Any
from dotenv import load_dotenv
from jassist.logger_utils.logger_utils import setup_logger
from jassist.utils.path_utils import resolve_path

ENCODING = "utf-8"

logger = setup_logger("config_loader", module="transcribe")

# Define paths
MODULE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = resolve_path("config/config_transcribe.json", MODULE_DIR)
ENV_PATH = resolve_path("../credentials/.env", MODULE_DIR)

def convert_string_booleans(config_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively convert 'true'/'false' strings into Python booleans."""
    for key, value in config_dict.items():
        if isinstance(value, dict):
            convert_string_booleans(value)
        elif isinstance(value, str):
            if value.lower() == "true":
                config_dict[key] = True
            elif value.lower() == "false":
                config_dict[key] = False
    return config_dict

def load_config() -> Dict[str, Any]:
    """Load or create the transcription config."""
    if not CONFIG_PATH.exists():
        logger.warning(f"Config file not found at: {CONFIG_PATH}")
        return {}
        
    try:
        with open(CONFIG_PATH, "r", encoding=ENCODING) as f:
            config = json.load(f)
        logger.info(f"Loaded transcription config from: {CONFIG_PATH}")
        
        # Validate essential config sections
        if "model" not in config:
            logger.warning("Model section missing in config. Using defaults.")
            config["model"] = {"name": "gpt-4o-mini-transcribe"}
            
        if "paths" not in config:
            logger.warning("Paths section missing in config. Using defaults.")
            config["paths"] = {"output_dir": "./transcriptions"}
            
        if "cost_management" not in config:
            logger.warning("Cost management section missing in config. Using defaults.")
            config["cost_management"] = {
                "max_audio_duration_seconds": 300,
                "warn_on_large_files": True
            }
            
        return convert_string_booleans(config)
    except Exception as e:
        logger.error(f"Failed to parse config: {e}")
        return {}

def load_environment():
    """Load .env file for API keys and database config."""
    if ENV_PATH.exists():
        load_dotenv(dotenv_path=ENV_PATH)
        logger.info(f"Environment variables loaded from: {ENV_PATH}")
    else:
        logger.warning(f".env file not found at expected location: {ENV_PATH}")
