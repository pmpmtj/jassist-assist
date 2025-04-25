"""
contactos module adapter for OpenAI Assistant Client.

This module provides a specialized interface for contacts processing
using the OpenAI Assistant Client.
"""

from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
import yaml

from jassist.logger_utils.logger_utils import setup_logger
from ..api_assistants_cliente import OpenAIAssistantClient
from ..config_manager import load_assistant_config
from ..exceptions import AssistantClientError, ConfigError

logger = setup_logger("contactos_adapter", module="api_assistants_cliente")

class ContactosAssistantAdapter:
    """
    Adapter for using the OpenAI Assistant Client with contacts processing.
    """
    
    def __init__(
        self,
        client: Optional[OpenAIAssistantClient] = None,
        config_file: Optional[Path] = None,
        prompts_file: Optional[Path] = None
    ):
        """
        Initialize the contactos assistant adapter.
        
        Args:
            client: Optional pre-configured OpenAI Assistant Client
            config_file: Optional path to a specific config file
            prompts_file: Optional path to a specific prompts file
            
        Raises:
            ConfigError: If required configuration or prompt files are missing
        """
        # Module name for this adapter
        self.module_name = "contactos"
        
        # Create or use the provided client
        if client:
            self.client = client
        else:
            # Default config file path - use contactos_assistant_config.json in the contactos module
            if config_file is None:
                jassist_dir = Path(__file__).resolve().parent.parent.parent.parent
                config_file = jassist_dir / "jassist" / "contactos" / "config" / "contactos_assistant_config.json"
                logger.info(f"Using contactos module config file: {config_file}")
            
            # Load configuration
            config = load_assistant_config(
                module_name=self.module_name,
                assistant_name="Assistente de Contactos",
                config_file=config_file
            )
            
            if not config:
                raise ConfigError(f"No configuration found for {self.module_name} module.")
            
            # Create client with contactos-specific settings
            self.client = OpenAIAssistantClient(
                config=config,
                assistant_name="Assistente de Contactos",
                module_name=self.module_name
            )
        
        # Load prompts - use either the provided file or the module's config file
        if prompts_file:
            prompts_path = prompts_file
        else:
            # Use the module's config path - FIXED PATH CONSTRUCTION
            # Get the jassist directory
            jassist_dir = Path(__file__).resolve().parent.parent.parent.parent
            
            # Log the path to help with debugging
            logger.info(f"jassist directory: {jassist_dir}")
            
            # Construct path to the contactos module's prompts file in the jassist directory
            prompts_path = jassist_dir / "jassist" / "contactos" / "config" / "prompts.yaml"
            
            # Log the final path to help with debugging
            logger.info(f"Using prompts path: {prompts_path}")
        
        # Load prompts from the file
        self.prompts = self._load_prompt_file(prompts_path)
        
        if not self.prompts:
            raise ConfigError(f"No prompt templates found for {self.module_name} module at {prompts_path}")
    
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
    
    def process_contact_entry(self, entry_content: str) -> str:
        """
        Process a contact entry using the OpenAI assistant.
        
        Args:
            entry_content: The contact entry text to process
            
        Returns:
            str: The assistant's structured response
            
        Raises:
            AssistantClientError: If processing fails
            ConfigError: If required configuration is missing
        """
        try:
            # Get prompt template and instructions - no defaults, must exist
            prompt_template = self.get_prompt_template("parse_entry_prompt")
            assistant_instructions = self.get_prompt_template("assistant_instructions")
            
            # Set up template variables
            now = datetime.now()
            template_vars = {
                "entry_content": entry_content,
                "current_date": now.strftime("%Y-%m-%d"),
                "current_time": now.strftime("%H:%M:%S")
            }
            
            # Update client instructions
            self.client.instructions = assistant_instructions
            
            # Always verify assistant and thread before processing
            assistant_id, was_created = self.client.get_or_create_assistant()
            thread_id = self.client.get_or_create_thread()
            
            logger.info(f"Using assistant ID: {assistant_id} (newly created: {was_created})")
            logger.info(f"Using thread ID: {thread_id}")
            
            # Process with the client
            response = self.client.process_with_prompt_template(
                input_text=entry_content,
                prompt_template=prompt_template,
                template_vars=template_vars,
                assistant_id=assistant_id,
                thread_id=thread_id
            )
            
            return response
            
        except ConfigError as e:
            # Re-raise configuration errors
            logger.error(f"Configuration error: {e}")
            raise
        except Exception as e:
            error_msg = f"Error processing contact entry: {e}"
            logger.error(error_msg)
            raise AssistantClientError(error_msg)


def process_with_contactos_assistant(entry_content: str) -> str:
    """
    Process a contact entry using a contacts assistant.
    
    This function provides a simple interface to process contact entries
    without needing to manage the adapter instance directly.
    
    Args:
        entry_content: The contact entry text to process
        
    Returns:
        str: The assistant's structured response
        
    Raises:
        ConfigError: If required configuration is missing
        AssistantClientError: If processing fails
    """
    adapter = ContactosAssistantAdapter()
    return adapter.process_contact_entry(entry_content) 