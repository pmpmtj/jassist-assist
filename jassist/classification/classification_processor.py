"""
Classification Processor

Main module for classifying text into different categories using OpenAI Assistants.
"""

from pathlib import Path
import yaml
from typing import Dict, Any, Optional, Union, Literal

from jassist.api_assistants_cliente.adapters.classification_adapter import ClassificationAdapter
from jassist.logger_utils.logger_utils import setup_logger
from jassist.utils.path_utils import resolve_path

# Get the script directory
SCRIPT_DIR = Path(__file__).resolve().parent
logger = setup_logger("classification_processor", module="classification")

# Global singleton instance for reuse
_processor_instance = None

class ClassificationProcessor:
    """
    Processor for classifying text using the OpenAI Assistant.
    """
    
    def __init__(
        self, 
        config_file: Optional[Path] = None, 
        prompts_file: Optional[Path] = None
    ):
        """
        Initialize the classification processor with the adapter.
        
        Args:
            config_file: Optional path to a specific config file
            prompts_file: Optional path to a specific prompts file
        """
        # Set default config paths if none provided
        if not config_file:
            config_file = resolve_path("config/classification_assistant_config.json", SCRIPT_DIR)
            
        if not prompts_file:
            prompts_file = resolve_path("config/prompts.yaml", SCRIPT_DIR)
        
        # Create the classification adapter with caching enabled
        self.adapter = ClassificationAdapter(
            config_file=config_file,
            prompts_file=prompts_file,
            use_cache=True
        )
        
        logger.debug("ClassificationProcessor initialized")
    
    def classify_text(
        self, 
        text: Union[str, Dict[str, Any]], 
        force_new_thread: bool = False
    ) -> Optional[str]:
        """
        Classify the purpose of the transcribed text using the classification adapter.
        
        Args:
            text: The text to classify or a dict containing the text
            force_new_thread: Force creation of a new thread instead of reusing
            
        Returns:
            Optional[str]: Classification result or None if classification failed
        """
        try:
            # The adapter already logs the classification process details,
            # so we'll just add minimal process flow logging here
            logger.debug("Delegating classification to adapter...")
            
            # Use the adapter to classify the text
            result = self.adapter.classify_text(
                text, 
                force_new_thread=force_new_thread
            )
            
            if not result:
                logger.error("No response from classification assistant")
            
            return result
                
        except Exception as e:
            # Only log the processor-level error, adapter already logs its own errors
            logger.error(f"Classification processor encountered an error: {e}", exc_info=True)
            return None
    
    @staticmethod
    def clear_caches():
        """
        Clear all cached configurations and prompts.
        """
        ClassificationAdapter.clear_cache()
        logger.debug("Cleared all classification caches")


def get_processor(
    config_file: Optional[Path] = None, 
    prompts_file: Optional[Path] = None
) -> ClassificationProcessor:
    """
    Get or create a singleton instance of the ClassificationProcessor.
    
    Args:
        config_file: Optional path to a specific config file
        prompts_file: Optional path to a specific prompts file
        
    Returns:
        ClassificationProcessor: The singleton processor instance
    """
    global _processor_instance
    
    if _processor_instance is None:
        _processor_instance = ClassificationProcessor(
            config_file=config_file,
            prompts_file=prompts_file
        )
        logger.debug("Created singleton ClassificationProcessor instance")
    elif config_file is not None or prompts_file is not None:
        # If configs are specified but we already have an instance,
        # create a new non-singleton instance
        logger.debug("Creating custom ClassificationProcessor instance with specified config")
        return ClassificationProcessor(
            config_file=config_file,
            prompts_file=prompts_file
        )
    
    return _processor_instance


def classify_text(
    text: Union[str, Dict[str, Any]], 
    config_file: Optional[Path] = None,
    prompts_file: Optional[Path] = None,
    force_new_thread: bool = False
) -> Optional[str]:
    """
    Global function to classify text using the classification processor.
    
    Args:
        text: The text to classify or a dict containing the text
        config_file: Optional path to a specific config file
        prompts_file: Optional path to a specific prompts file
        force_new_thread: Force creation of a new thread instead of reusing
        
    Returns:
        Optional[str]: Classification result or None if classification failed
    """
    # Get or create the processor instance
    processor = get_processor(
        config_file, 
        prompts_file
    )
    
    # Classify the text
    return processor.classify_text(
        text, 
        force_new_thread=force_new_thread
    )
