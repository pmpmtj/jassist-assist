"""
Summary module adapter for OpenAI Assistant Client.

This module provides a specialized interface for text summarization
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
logger = setup_logger("sample_adapter", module="api_assistants_cliente")

# Global cache for prompts and configurations
_CONFIG_CACHE = {}
_PROMPTS_CACHE = {}

# Thread pool for reusing threads based on task type
_THREAD_POOL = {}
# Maximum number of threads to keep in pool
_MAX_POOL_SIZE = 3

class SummaryAssistantAdapter:
    """
    Adapter for using the OpenAI Assistant Client with text summarization.
    """
    
    def __init__(
        self,
        client: Optional[OpenAIAssistantClient] = None,
        config_file: Optional[Path] = None,
        prompts_file: Optional[Path] = None,
        use_cache: bool = True,
        use_thread_pool: bool = True
    ):
        """
        Initialize the summary assistant adapter.
        
        Args:
            client: Optional pre-configured OpenAI Assistant Client
            config_file: Optional path to a specific config file
            prompts_file: Optional path to a specific prompts file
            use_cache: Whether to use cached configurations and prompts
            use_thread_pool: Whether to use thread pooling for improved performance
            
        Raises:
            ConfigError: If required configuration or prompt files are missing
        """
        # Module name for this adapter
        self.module_name = "summary"
        self.use_thread_pool = use_thread_pool
        
        # Resolve prompts file path if provided
        self.prompts_key = None
        if prompts_file:
            self.prompts_key = str(prompts_file)
        
        # Load configuration
        self.config = None
        config_key = f"{self.module_name}_{config_file}" if config_file else self.module_name
        
        # Create or use the provided client
        if client:
            self.client = client
        else:
            # Try to get config from cache first
            if use_cache and config_key in _CONFIG_CACHE:
                logger.debug(f"Using cached configuration for {config_key}")
                config = _CONFIG_CACHE[config_key]
            else:
                # Load configuration if not in cache
                config = load_assistant_config(
                    module_name=self.module_name,
                    assistant_name="Text Summarizer",
                    config_file=config_file
                )
                # Cache the configuration
                if use_cache:
                    _CONFIG_CACHE[config_key] = config
                    logger.debug(f"Cached configuration for {config_key}")
            
            # Create client with summary-specific settings
            self.client = OpenAIAssistantClient(
                config=config,
                assistant_name="Text Summarizer",
                module_name=self.module_name
            )
            
            # Store config for future reference
            self.config = config
        
        # Load prompts - use either the provided file or the module's config file
        if prompts_file:
            prompts_path = prompts_file
        else:
            # Use the module's config path
            module_dir = resolve_path("../summary/config", SCRIPT_DIR)
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
        logger.debug("Cleared all summary adapter caches")
    
    @staticmethod
    def clear_thread_pool():
        """
        Clear the thread pool, forcing the creation of new threads.
        Useful when thread content might be affecting results.
        """
        global _THREAD_POOL
        _THREAD_POOL.clear()
        logger.debug("Cleared summary thread pool")
    
    def _get_thread_from_pool(self, task_type: str, assistant_id: str) -> Optional[str]:
        """
        Get a thread ID from the thread pool for the given task type and assistant.
        
        Args:
            task_type: The task type (e.g., "comprehensive", "bullet_points")
            assistant_id: The OpenAI assistant ID
            
        Returns:
            Optional[str]: A thread ID if available, None otherwise
        """
        if not self.use_thread_pool:
            return None
            
        pool_key = f"{assistant_id}_{task_type}"
        threads = _THREAD_POOL.get(pool_key, [])
        
        if threads:
            # Get the oldest thread (FIFO)
            thread_id = threads.pop(0)
            logger.debug(f"Reusing thread {thread_id} from pool for {pool_key}")
            
            # Put it back at the end (for round-robin reuse)
            threads.append(thread_id)
            _THREAD_POOL[pool_key] = threads
            
            return thread_id
        
        return None
    
    def _add_thread_to_pool(self, thread_id: str, task_type: str, assistant_id: str):
        """
        Add a thread ID to the thread pool.
        
        Args:
            thread_id: The thread ID to add
            task_type: The task type (e.g., "comprehensive", "bullet_points")
            assistant_id: The OpenAI assistant ID
        """
        if not self.use_thread_pool:
            return
            
        pool_key = f"{assistant_id}_{task_type}"
        threads = _THREAD_POOL.get(pool_key, [])
        
        # Only add if not already in the pool
        if thread_id not in threads:
            threads.append(thread_id)
            
            # Limit pool size
            if len(threads) > _MAX_POOL_SIZE:
                threads = threads[-_MAX_POOL_SIZE:]
            
            _THREAD_POOL[pool_key] = threads
            logger.debug(f"Added thread {thread_id} to pool for {pool_key}")
    
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
    
    def summarize_text(
        self, 
        text: str, 
        summary_type: str = "comprehensive", 
        target_length: int = 100,
        focus_areas: Optional[List[str]] = None,
        force_new_thread: bool = False
    ) -> str:
        """
        Summarize text using the OpenAI assistant.
        
        Args:
            text: The text to summarize
            summary_type: Type of summary (comprehensive, bullet_points, etc.)
            target_length: Target word count for summary
            focus_areas: Optional specific areas to focus on
            force_new_thread: Force creation of a new thread instead of reusing
            
        Returns:
            str: The summary
            
        Raises:
            AssistantClientError: If processing fails
            ConfigError: If required configuration is missing
        """
        start_time = time.time()
        
        try:
            # Get prompt template - no defaults, must exist
            prompt_template = self.get_prompt_template("summarize_text")
            
            # Get assistant instructions
            assistant_instructions = self.get_prompt_template("assistant_instructions")
            
            # Set up template variables
            template_vars = {
                "input_text": text,
                "summary_type": summary_type,
                "target_length": str(target_length),
                "focus_areas": ", ".join(focus_areas) if focus_areas else "the main points"
            }
            
            # Update client instructions
            self.client.instructions = assistant_instructions
            
            # Get or create assistant
            assistant_id, _ = self.client.get_or_create_assistant()
            
            # Get thread ID - either from pool or create new
            thread_id = None
            thread_key = "default"
            
            if force_new_thread:
                # Use a unique thread key to force creation of a new thread
                thread_key = f"new_{int(time.time())}"
                logger.debug(f"Forcing new thread with key: {thread_key}")
                
                # Create a temporary thread (don't save to config)
                thread_id = self.client.get_or_create_thread(
                    thread_key=thread_key, 
                    save_to_config=False
                )
            elif self.use_thread_pool:
                # Try to get a thread from our pool
                thread_id = self._get_thread_from_pool(summary_type, assistant_id)
            
            if not thread_id:
                # Get or create a thread with the appropriate key
                thread_id = self.client.get_or_create_thread(thread_key=thread_key)
                
                # Add to thread pool if using pool and not forcing new
                if self.use_thread_pool and not force_new_thread:
                    self._add_thread_to_pool(thread_id, summary_type, assistant_id)
            
            logger.info(f"Using assistant ID: {assistant_id}")
            logger.info(f"Using thread ID: {thread_id}")
            
            # Process with the client
            response = self.client.process_with_prompt_template(
                input_text=text,
                prompt_template=prompt_template,
                template_vars=template_vars,
                assistant_id=assistant_id,
                thread_id=thread_id
            )
            
            if not response:
                raise AssistantClientError("No response from summary assistant")
            
            elapsed_time = time.time() - start_time
            logger.info(f"Summarization successful: {response[:100]}... (completed in {elapsed_time:.2f}s)")
            return response
            
        except ConfigError as e:
            # Re-raise configuration errors
            elapsed_time = time.time() - start_time
            logger.error(f"Configuration error: {e} (after {elapsed_time:.2f}s)")
            raise
        except Exception as e:
            elapsed_time = time.time() - start_time
            error_msg = f"Error generating summary: {e} (after {elapsed_time:.2f}s)"
            logger.error(error_msg)
            raise AssistantClientError(error_msg)


def summarize_text(
    text: str, 
    summary_type: str = "comprehensive", 
    target_length: int = 100,
    focus_areas: Optional[List[str]] = None,
    force_new_thread: bool = False,
    use_thread_pool: bool = True
) -> str:
    """
    Summarize text using a summary assistant.
    
    This function provides a simple interface to summarize text
    without needing to manage the adapter instance directly.
    
    Args:
        text: The text to summarize
        summary_type: Type of summary (comprehensive, bullet_points, etc.)
        target_length: Target word count for summary
        focus_areas: Optional specific areas to focus on
        force_new_thread: Force creation of a new thread instead of reusing
        use_thread_pool: Whether to use thread pooling for improved performance
        
    Returns:
        str: The summary
        
    Raises:
        ConfigError: If required configuration is missing
        AssistantClientError: If processing fails
    """
    # The detailed timing and process logging is already handled in the adapter's method
    adapter = SummaryAssistantAdapter(use_thread_pool=use_thread_pool)
    return adapter.summarize_text(
        text=text,
        summary_type=summary_type,
        target_length=target_length,
        focus_areas=focus_areas,
        force_new_thread=force_new_thread
    ) 