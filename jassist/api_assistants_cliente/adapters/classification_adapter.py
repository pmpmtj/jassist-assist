"""
Classification adapter for OpenAI Assistant Client.

This module provides a specialized interface for text classification
using the OpenAI Assistant Client.
"""

from pathlib import Path
import time
from typing import Dict, Any, Optional, List, Union, Literal

from jassist.logger_utils.logger_utils import setup_logger
from jassist.api_assistants_cliente.api_assistants_cliente import OpenAIAssistantClient
from jassist.api_assistants_cliente.config_manager import load_assistant_config
from jassist.api_assistants_cliente.exceptions import AssistantClientError, ConfigError
from jassist.utils.path_utils import resolve_path

# Get the script directory
SCRIPT_DIR = Path(__file__).resolve().parent
logger = setup_logger("classification_adapter", module="api_assistants_cliente")

# Global cache for prompts and configurations
_CONFIG_CACHE = {}
_PROMPTS_CACHE = {}

# Persistent thread key for maintaining conversation context across multiple
# classification requests. This improves classification consistency and reduces
# token usage by leveraging previous context.
PERSISTENT_THREAD_KEY = "persistent"

class ClassificationAdapter:
    """
    Adapter for using the OpenAI Assistant Client with text classification.
    """
    
    def __init__(
        self,
        client: Optional[OpenAIAssistantClient] = None,
        config_file: Optional[Path] = None,
        prompts_file: Optional[Path] = None,
        use_cache: bool = True
    ):
        """
        Initialize the classification assistant adapter.
        
        Args:
            client: Optional pre-configured OpenAI Assistant Client
            config_file: Optional path to a specific config file
            prompts_file: Optional path to a specific prompts file
            use_cache: Whether to use cached configurations and prompts
            
        Raises:
            ConfigError: If required configuration or prompt files are missing
        """
        # Module name for this adapter
        self.module_name = "classification"
        
        # Resolve prompts file path if provided
        self.prompts_key = None
        if prompts_file:
            self.prompts_key = str(prompts_file)
        
        # Load configuration
        self.config = None
        config_key = f"{self.module_name}_{config_file}" if config_file else self.module_name
        
        if not client:
            # Try to get config from cache first
            if use_cache and config_key in _CONFIG_CACHE:
                logger.debug(f"Using cached configuration for {config_key}")
                self.config = _CONFIG_CACHE[config_key]
            else:
                # Load configuration if not in cache
                self.config = load_assistant_config(
                    module_name=self.module_name,
                    assistant_name="Classification Assistant",
                    config_file=config_file
                )
                # Cache the configuration
                if use_cache:
                    _CONFIG_CACHE[config_key] = self.config
                    logger.debug(f"Cached configuration for {config_key}")
            
        # Create or use the provided client
        if client:
            self.client = client
        else:
            # Create client with classification-specific settings
            self.client = OpenAIAssistantClient(
                config=self.config,
                assistant_name="Classification Assistant",
                module_name=self.module_name
            )
        
        # Load prompts - use either the provided file or the module's config file
        if prompts_file:
            prompts_path = prompts_file
        else:
            # Find the module's prompts file
            module_dir = resolve_path("../classification/config", SCRIPT_DIR)
            prompts_path = resolve_path("prompts.yaml", module_dir)
            self.prompts_key = str(prompts_path)
        
        # Load prompts from cache or file
        if use_cache and self.prompts_key in _PROMPTS_CACHE:
            logger.debug(f"Using cached prompts from {self.prompts_key}")
            self.prompts = _PROMPTS_CACHE[self.prompts_key]
        else:
            # Load prompts from the file
            self.prompts = self._load_prompt_file(prompts_path)
            # Cache the prompts
            if use_cache:
                _PROMPTS_CACHE[self.prompts_key] = self.prompts
                logger.debug(f"Cached prompts from {self.prompts_key}")
    
    @staticmethod
    def clear_cache():
        """
        Clear all cached configurations and prompts.
        Useful when configuration files have been updated.
        """
        global _CONFIG_CACHE, _PROMPTS_CACHE
        _CONFIG_CACHE.clear()
        _PROMPTS_CACHE.clear()
        logger.debug("Cleared all classification adapter caches")
    
    def _load_prompt_file(self, prompts_path: Path) -> Dict[str, Any]:
        """
        Load prompts from a specific file.
        
        Args:
            prompts_path: Path to the prompts file
            
        Returns:
            Dict: Prompts dictionary
            
        Raises:
            ConfigError: If the prompts file is missing or invalid
        """
        import yaml
        
        if not prompts_path.exists():
            raise ConfigError(f"Prompts file not found: {prompts_path}")
            
        try:
            with open(prompts_path, "r", encoding="utf-8") as f:
                prompts_data = yaml.safe_load(f)
                prompts = prompts_data.get('prompts', {})
                if not prompts:
                    raise ConfigError(f"No prompts found in file: {prompts_path}")
                return prompts
        except Exception as e:
            raise ConfigError(f"Error loading prompts file {prompts_path}: {e}")
    
    def get_prompt_template(self, prompt_name: str) -> str:
        """
        Get a prompt template by name.
        
        Args:
            prompt_name: Name of the prompt template
            
        Returns:
            str: The prompt template text
            
        Raises:
            ConfigError: If the prompt template is not found
        """
        prompt_data = self.prompts.get(prompt_name)
        if not prompt_data:
            raise ConfigError(f"Prompt '{prompt_name}' not found in {self.module_name} prompts")

        template = prompt_data.get("template")
        if not template:
            raise ConfigError(f"Template not found for prompt '{prompt_name}'")

        return template
    
    def classify_text(
        self, 
        text: Union[str, Dict[str, Any]], 
        force_new_thread: bool = False
    ) -> str:
        """
        Classify text using the OpenAI assistant.
        
        Args:
            text: The text to classify or a dict containing the text
            force_new_thread: Force creation of a new thread instead of reusing
            
        Returns:
            str: The classification result
            
        Raises:
            AssistantClientError: If processing fails
            ConfigError: If required configuration is missing
        """
        start_time = time.time()
        
        try:
            # Extract text content if input is a dictionary
            if isinstance(text, dict):
                content = text.get("text", "")
            else:
                content = text
                
            # Get prompt templates
            parse_prompt = self.get_prompt_template("parse_entry_prompt")
            
            # Always use the JSON instructions template
            assistant_instructions = self.get_prompt_template("assistant_instructions_json")
            
            # Set up template variables
            template_vars = {
                "entry_content": content
            }
            
            # Update client instructions
            self.client.instructions = assistant_instructions
            
            # Get or create assistant
            assistant_id, _ = self.client.get_or_create_assistant()
            
            # Get thread ID - either create new or use persistent thread
            thread_id = None
            
            if force_new_thread:
                # Use a unique thread key to force creation of a new thread
                thread_key = f"new_{int(time.time())}"
                logger.debug(f"Forcing new thread with key: {thread_key}")
                
                # Create a temporary thread (don't save to config)
                thread_id = self.client.get_or_create_thread(
                    thread_key=thread_key, 
                    save_to_config=False
                )
            else:
                # Always use the persistent thread key
                thread_id = self.client.get_or_create_thread(
                    thread_key=PERSISTENT_THREAD_KEY,
                    save_to_config=True  # Ensure it's saved to config
                )
                logger.debug(f"Using persistent thread with key: {PERSISTENT_THREAD_KEY}")
            
            logger.info(f"Using assistant ID: {assistant_id}")
            logger.info(f"Using thread ID: {thread_id}")
            
            # Process with the client
            response = self.client.process_with_prompt_template(
                input_text=content,
                prompt_template=parse_prompt,
                template_vars=template_vars,
                assistant_id=assistant_id,
                thread_id=thread_id
            )
            
            if not response:
                raise AssistantClientError("No response from classification assistant")
            
            elapsed_time = time.time() - start_time
            logger.info(f"Classification successful: {response[:100]}... (completed in {elapsed_time:.2f}s)")
            return response
            
        except ConfigError as e:
            # Re-raise configuration errors
            elapsed_time = time.time() - start_time
            logger.error(f"Configuration error: {e} (after {elapsed_time:.2f}s)")
            raise
        except Exception as e:
            elapsed_time = time.time() - start_time
            error_msg = f"Error during classification: {e} (after {elapsed_time:.2f}s)"
            logger.error(error_msg)
            raise AssistantClientError(error_msg)