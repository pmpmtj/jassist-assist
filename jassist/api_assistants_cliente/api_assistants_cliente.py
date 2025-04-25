"""
OpenAI Assistant Client

A centralized module for managing and interacting with OpenAI assistants.
"""

import os
import json
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, Tuple, List, Union, Callable

from openai import OpenAI

from jassist.logger_utils.logger_utils import setup_logger
from jassist.api_assistants_cliente.exceptions import AssistantError, ThreadError, RunError, ConfigError

logger = setup_logger("api_assistants_cliente", module="api_assistants_cliente")

class OpenAIAssistantClient:
    """
    Centralized client for managing OpenAI assistants across different modules.
    Handles creation, verification, recovery, and execution of assistants.
    """
    
    def __init__(
        self, 
        client: Optional[OpenAI] = None,
        config: Dict[str, Any] = None,
        config_path: Optional[Path] = None,
        assistant_name: Optional[str] = None,
        module_name: Optional[str] = None,
        model_name: Optional[str] = None,
        instructions: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None
    ):
        """
        Initialize the assistant client.
        
        Args:
            client: OpenAI client instance (will create one if not provided)
            config: Assistant configuration dictionary (alternative to config_path)
            config_path: Path to the config file where assistant data is stored
            assistant_name: Name of the assistant (used if not in config)
            module_name: Name of the module this assistant belongs to (used for config paths)
            model_name: OpenAI model to use (overrides config if provided)
            instructions: Instructions for the assistant (overrides config if provided)
            tools: List of tools for the assistant (overrides config if provided)
            
        Raises:
            ConfigError: If required configuration is missing
        """
        # Store module name
        self.module_name = module_name
        
        # Load config from path if provided
        if config_path and not config:
            config = self._load_config(config_path)
            
        if not config:
            raise ConfigError("No configuration provided")
        
        # Store config
        self.config = config
        
        # Initialize the OpenAI client
        self.client = client if client is not None else self._initialize_client(config)
        
        # Set assistant properties, with passed values taking precedence over config
        self.assistant_name = assistant_name or config.get('assistant_name')
        if not self.assistant_name:
            raise ConfigError("Assistant name must be provided either in config or as parameter")
            
        self.model_name = model_name or config.get('model')
        if not self.model_name:
            raise ConfigError("Model name must be provided either in config or as parameter")
            
        self.instructions = instructions or config.get('instructions', '')
        
        # Tools must be provided either in config or as parameter
        self.tools = tools or config.get('tools')
        if not self.tools:
            # Default to empty tools list rather than failing
            self.tools = []
        
        # Format the key for storing this specific assistant's ID
        self.assistant_key = f"assistant_id_{self.assistant_name.lower().replace(' ', '_')}"
    
    def _initialize_client(self, config: Dict[str, Any]) -> OpenAI:
        """
        Initialize the OpenAI client with API key from config or environment.
        
        Args:
            config: Configuration dict that may contain API key
            
        Returns:
            OpenAI: Initialized client
            
        Raises:
            ConfigError: If API key is missing
        """
        # Try to get API key from config
        api_key = config.get('api_key')
        
        # Fall back to environment variable
        if not api_key:
            api_key = os.environ.get('OPENAI_API_KEY')
            
        if not api_key:
            raise ConfigError("Missing OpenAI API key. Set it in config or as OPENAI_API_KEY environment variable.")
            
        return OpenAI(api_key=api_key)
    
    def _load_config(self, config_path: Path) -> Dict[str, Any]:
        """
        Load configuration from file.
        
        Args:
            config_path: Path to config file
            
        Returns:
            Dict: Configuration dictionary
            
        Raises:
            ConfigError: If the file doesn't exist or has parsing errors
        """
        if not config_path.exists():
            raise ConfigError(f"Config file not found: {config_path}")
            
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            raise ConfigError(f"Error loading config: {e}")
    
    def _save_config(self, config_path: Path) -> bool:
        """
        Save current configuration to file.
        
        Args:
            config_path: Path to save config
            
        Returns:
            bool: Success status
            
        Raises:
            ConfigError: If saving fails
        """
        try:
            # Ensure parent directories exist
            config_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=2)
            return True
        except Exception as e:
            raise ConfigError(f"Error saving config: {e}")
    
    def get_or_create_assistant(self) -> Tuple[str, bool]:
        """
        Get an existing assistant or create a new one if not found.
        
        This will always check if the assistant exists and create a new one
        if it cannot be found, regardless of whether we have an ID in the config.
        
        Returns:
            Tuple[str, bool]: (assistant_id, was_created)
            
        Raises:
            AssistantError: If assistant creation fails
        """
        # Look for an existing assistant ID in the config
        if self.assistant_key in self.config:
            assistant_id = self.config[self.assistant_key]
            
            # Verify the assistant exists
            try:
                assistant = self.client.beta.assistants.retrieve(assistant_id)
                logger.info(f"Using existing assistant: {assistant_id}")
                return assistant_id, False
            except Exception as e:
                logger.warning(f"Assistant no longer exists or error retrieving: {e}")
                # Continue to creating a new assistant
        
        # Create a new assistant
        logger.info(f"Creating new assistant: {self.assistant_name}")
        try:
            # Get response_format from config, defaulting to "auto"
            response_format = "auto"
            if "default_response_format" in self.config:
                if self.config["default_response_format"] == "json":
                    response_format = {"type": "json_object"}
            
            # Get temperature from config, defaulting to 1.0
            temperature = self.config.get("temperature", 1.0)
            
            assistant = self.client.beta.assistants.create(
                name=self.assistant_name,
                instructions=self.instructions,
                tools=self.tools,
                model=self.model_name,
                response_format=response_format,
                temperature=temperature
            )
            assistant_id = assistant.id
            
            # Save the new assistant ID
            self.config[self.assistant_key] = assistant_id
            
            # Save config if we have module_name
            if self.module_name:
                from .config_manager import get_module_dir
                try:
                    module_dir = get_module_dir(self.module_name)
                    config_file = module_dir / "config" / f"{self.module_name}_assistant_config.json"
                    self._save_config(config_file)
                    logger.info(f"Saved updated config to {config_file}")
                except Exception as e:
                    logger.warning(f"Could not save config to module directory: {e}")
            
            logger.info(f"Created new assistant with ID: {assistant_id}")
            return assistant_id, True
        except Exception as e:
            error_msg = f"Failed to create OpenAI assistant: {e}"
            logger.error(error_msg)
            raise AssistantError(error_msg)
    
    def delete_assistant(self, assistant_id: Optional[str] = None) -> bool:
        """
        Delete an assistant and remove it from the config.
        
        Args:
            assistant_id: Optional specific assistant ID to delete
                          (if not provided, use the one in the config)
        
        Returns:
            bool: True if deleted successfully
        """
        # If no ID provided, try to get it from config
        if not assistant_id:
            assistant_id = self.config.get(self.assistant_key)
            if not assistant_id:
                logger.info(f"No assistant ID found to delete for {self.assistant_name}")
                return True
        
        try:
            # Try to delete from OpenAI
            self.client.beta.assistants.delete(assistant_id)
            logger.info(f"Deleted assistant with ID: {assistant_id}")
        except Exception as e:
            logger.warning(f"Failed to delete assistant from OpenAI (may already be deleted): {e}")
        
        # Remove from config if we're using the assistant key
        if self.assistant_key in self.config and self.config[self.assistant_key] == assistant_id:
            del self.config[self.assistant_key]
        
        return True
    
    def get_or_create_thread(self, thread_key: str = "default", retention_days: int = 30, save_to_config: bool = True) -> str:
        """
        Get an existing thread or create a new one if needed.
        
        This will always check if the thread exists and create a new one if it cannot be found,
        regardless of whether we have an ID in the config.
        
        Args:
            thread_key: Key to identify this specific thread in the config
            retention_days: Number of days to keep a thread before rotating
            save_to_config: Whether to save the thread ID to config (set False for temporary threads)
            
        Returns:
            str: Thread ID
        """
        # Format the key for storing this specific thread
        full_thread_key = f"thread_id_{self.assistant_name.lower().replace(' ', '_')}_{thread_key}"
        created_at_key = f"{full_thread_key}_created_at"
        
        thread_id = self.config.get(full_thread_key)
        thread_needs_recreation = False
        
        if thread_id:
            try:
                thread = self.client.beta.threads.retrieve(thread_id)
                
                # Check if thread needs rotation
                if created_at_key in self.config:
                    try:
                        created_at = datetime.fromisoformat(self.config[created_at_key])
                        days_old = (datetime.now() - created_at).days
                        if days_old > retention_days:
                            thread_needs_recreation = True
                            logger.info(f"Thread is {days_old} days old, recreating due to retention policy")
                    except (ValueError, TypeError) as e:
                        logger.warning(f"Error parsing thread creation date: {e}")
                        thread_needs_recreation = True
            except Exception as e:
                logger.error(f"Error retrieving thread: {e}")
                thread_needs_recreation = True
        else:
            thread_needs_recreation = True
        
        if thread_needs_recreation:
            thread = self.client.beta.threads.create()
            thread_id = thread.id
            
            # Only save to config if requested (temporary threads won't be saved)
            if save_to_config:
                # Save the new thread ID and creation time
                self.config[full_thread_key] = thread_id
                self.config[created_at_key] = datetime.now().isoformat()
                
                # Save config if we have module_name
                if self.module_name:
                    from .config_manager import get_module_dir
                    try:
                        module_dir = get_module_dir(self.module_name)
                        config_file = module_dir / "config" / f"{self.module_name}_assistant_config.json"
                        self._save_config(config_file)
                        logger.info(f"Saved updated config to {config_file}")
                    except Exception as e:
                        logger.warning(f"Could not save config to module directory: {e}")
            else:
                logger.debug(f"Created temporary thread with ID: {thread_id} (not saved to config)")
            
            logger.info(f"Created new thread with ID: {thread_id}")
        
        return thread_id
    
    def run_assistant(
        self, 
        prompt: str,
        thread_id: Optional[str] = None,
        assistant_id: Optional[str] = None,
        max_retries: int = 1,
        poll_interval: float = 1.0,
        timeout: int = 300
    ) -> Optional[str]:
        """
        Run the assistant with the given prompt.
        
        Args:
            prompt: User prompt to send
            thread_id: Thread ID to use (will create if None)
            assistant_id: Assistant ID to use (will create if None)
            max_retries: Maximum number of times to retry on assistant errors
            poll_interval: How often to check run status in seconds
            timeout: Maximum seconds to wait for completion
            
        Returns:
            Optional[str]: The assistant's response or None if failed
            
        Raises:
            ThreadError: If thread operations fail
            RunError: If run operations fail
            TimeoutError: If run times out
        """
        # Get the assistant ID, creating if needed
        if not assistant_id:
            assistant_id, _ = self.get_or_create_assistant()
        
        # Get or create thread if not provided
        if not thread_id:
            thread_id = self.get_or_create_thread()
        
        # Create message
        try:
            self.client.beta.threads.messages.create(
                thread_id=thread_id,
                role="user",
                content=prompt
            )
        except Exception as e:
            error_msg = f"Error creating message in thread: {e}"
            logger.error(error_msg)
            raise ThreadError(error_msg)
        
        # Try to run with retries
        retries = 0
        last_error = None
        
        while retries <= max_retries:
            try:
                # Start the run
                run = self.client.beta.threads.runs.create(
                    thread_id=thread_id,
                    assistant_id=assistant_id
                )
                
                # Wait for completion with timeout
                start_time = time.time()
                while time.time() - start_time < timeout:
                    run_status = self.client.beta.threads.runs.retrieve(
                        thread_id=thread_id,
                        run_id=run.id
                    )
                    
                    # Check for completion or error
                    if run_status.status == "completed":
                        break
                    elif run_status.status in ["failed", "cancelled", "expired"]:
                        error_msg = f"Run failed with status {run_status.status}"
                        if hasattr(run_status, 'last_error'):
                            error_msg += f": {run_status.last_error}"
                        raise RunError(error_msg)
                    
                    # Wait before checking again
                    time.sleep(poll_interval)
                
                # Check for timeout
                if time.time() - start_time >= timeout:
                    raise TimeoutError(f"Assistant run timed out after {timeout} seconds")
                
                # Get messages
                messages = self.client.beta.threads.messages.list(thread_id=thread_id)
                for message in messages.data:
                    if message.role == "assistant":
                        # Handle text content
                        if hasattr(message, 'content') and message.content:
                            for content_part in message.content:
                                if hasattr(content_part, 'text') and content_part.text:
                                    return content_part.text.value
                
                # If we got here but found no response content
                return None
                
            except (RunError, ThreadError, TimeoutError) as e:
                # These errors are specific and should be re-raised
                last_error = e
                logger.error(f"Error during run (attempt {retries+1}/{max_retries+1}): {e}")
                retries += 1
                
            except Exception as e:
                # General errors
                last_error = e
                logger.error(f"Unexpected error during run (attempt {retries+1}/{max_retries+1}): {e}")
                retries += 1
        
        # If we reach here, all retries failed
        if last_error:
            raise RunError(f"All run attempts failed: {last_error}")
        
        return None
    
    def process_with_prompt_template(
        self,
        input_text: str,
        prompt_template: str,
        template_vars: Optional[Dict[str, Any]] = None,
        assistant_instructions: Optional[str] = None,
        assistant_id: Optional[str] = None,
        thread_id: Optional[str] = None
    ) -> str:
        """
        Process input text using a prompt template and the assistant.
        
        Args:
            input_text: The text to process
            prompt_template: Template string for the prompt
            template_vars: Variables to format the template with
            assistant_instructions: Optional override for assistant instructions (DEPRECATED - use only at creation time)
            assistant_id: Optional assistant ID to use for processing
            thread_id: Optional thread ID to use for processing
            
        Returns:
            str: The assistant's response
            
        Raises:
            ConfigError: If template variables are missing
            RunError: If the assistant run fails
        """
        # Prepare variables for template
        vars_dict = template_vars or {}
        vars_dict['input_text'] = input_text
        
        # Format prompt with all required parameters
        try:
            prompt = prompt_template.format(**vars_dict)
        except KeyError as e:
            error_msg = f"Missing template variable: {e}"
            logger.error(error_msg)
            raise ConfigError(error_msg)
        
        # NOTE: We no longer update instructions here - they should only be set at assistant creation time
        # if assistant_instructions:
        #     self.instructions = assistant_instructions
        
        # Run the assistant
        response = self.run_assistant(
            prompt=prompt,
            assistant_id=assistant_id,
            thread_id=thread_id
        )
        
        if not response:
            raise RunError("No assistant response received")
        
        return response 