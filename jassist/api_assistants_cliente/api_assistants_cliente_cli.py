"""
Command-line interface for the OpenAI Assistant Client.

This module provides command-line tools for working with OpenAI assistants.
"""

import sys
import argparse
from pathlib import Path
from typing import Dict, Any, List, Optional, Union

from openai import OpenAI

from jassist.logger_utils.logger_utils import setup_logger
from jassist.utils.path_utils import resolve_path
from jassist.api_assistants_cliente.api_assistants_cliente import OpenAIAssistantClient
from jassist.api_assistants_cliente.config_manager import load_assistant_config
from jassist.api_assistants_cliente.exceptions import AssistantClientError, ConfigError

logger = setup_logger("api_assistants_cliente_cli", module="api_assistants_cliente")


def create_client(
    module_name: str,
    assistant_name: Optional[str] = None, 
    config_file: Optional[Union[str, Path]] = None
) -> OpenAIAssistantClient:
    """
    Create an assistant client with configuration.
    
    Args:
        module_name: Name of the module this assistant belongs to
        assistant_name: Optional specific assistant name
        config_file: Optional specific config file path
        
    Returns:
        OpenAIAssistantClient: Configured client
        
    Raises:
        ConfigError: If configuration is missing or invalid
    """
    # Load configuration
    config = load_assistant_config(
        module_name=module_name,
        assistant_name=assistant_name,
        config_file=config_file
    )
    
    # Assistant name can come from config if not provided
    if not assistant_name and 'assistant_name' in config:
        assistant_name = config['assistant_name']
    
    # Create the client
    return OpenAIAssistantClient(
        config=config,
        assistant_name=assistant_name,
        module_name=module_name
    )


def get_prompt_template(
    module_name: str,
    prompt_name: str,
    prompts_file: Path
) -> str:
    """
    Get a prompt template by name.
    
    Args:
        module_name: Name of the module
        prompt_name: Name of the prompt template
        prompts_file: Path to the prompts file
        
    Returns:
        str: The prompt template text
        
    Raises:
        ConfigError: If the prompts file is missing or the template is not found
    """
    # Import here to avoid circular import
    import yaml
    
    if not prompts_file.exists():
        raise ConfigError(f"Prompts file not found: {prompts_file}")
    
    try:
        with open(prompts_file, "r", encoding="utf-8") as f:
            prompts_data = yaml.safe_load(f)
            prompts = prompts_data.get('prompts', {})
    except Exception as e:
        raise ConfigError(f"Error loading prompts file {prompts_file}: {e}")
    
    if not prompts:
        raise ConfigError(f"No prompts found in {prompts_file}")

    prompt_data = prompts.get(prompt_name)
    if not prompt_data:
        raise ConfigError(f"Prompt '{prompt_name}' not found in prompts")

    template = prompt_data.get("template")
    if not template:
        raise ConfigError(f"Template not found for prompt '{prompt_name}'")

    return template


def process_with_assistant(
    input_text: str,
    module_name: str,
    assistant_name: Optional[str] = None,
    prompt_template_name: Optional[str] = None,
    prompt_template: Optional[str] = None,
    template_vars: Optional[Dict[str, Any]] = None,
    config_file: Optional[Union[str, Path]] = None,
    prompts_file: Optional[Union[str, Path]] = None
) -> str:
    """
    Process input text with an OpenAI assistant.
    
    Args:
        input_text: The text to process
        module_name: Name of the module this assistant belongs to
        assistant_name: Optional specific assistant name
        prompt_template_name: Optional name of a prompt template to use
        prompt_template: Optional explicit prompt template string
        template_vars: Optional variables for prompt template
        config_file: Optional specific config file path
        prompts_file: Optional specific prompts file path
        
    Returns:
        str: The assistant's response
        
    Raises:
        ConfigError: If configuration is missing or invalid
        AssistantClientError: If processing fails
    """
    # Create the client
    client = create_client(
        module_name=module_name,
        assistant_name=assistant_name,
        config_file=config_file
    )
    
    # Get the prompt template if specified by name
    if prompt_template_name and not prompt_template:
        if not prompts_file:
            # If prompts file not provided, use module's config path
            module_dir = Path(__file__).resolve().parent.parent.parent
            prompts_file = resolve_path(f"{module_name}/config/prompts.yaml", module_dir)
            
        prompt_template = get_prompt_template(
            module_name=module_name,
            prompt_name=prompt_template_name,
            prompts_file=Path(prompts_file) if isinstance(prompts_file, str) else prompts_file
        )
    
    # If we have a prompt template, use it
    if prompt_template:
        return client.process_with_prompt_template(
            input_text=input_text,
            prompt_template=prompt_template,
            template_vars=template_vars
        )
    
    # Otherwise just use the input text directly
    return client.run_assistant(prompt=input_text)


def main():
    """Command-line entry point."""
    parser = argparse.ArgumentParser(description="OpenAI Assistant Client")
    
    # Common arguments
    parser.add_argument("--module", "-m", required=True, help="Module name (required)")
    parser.add_argument("--assistant", "-a", help="Assistant name")
    parser.add_argument("--config", "-c", help="Path to config file")
    
    # Subcommands
    subparsers = parser.add_subparsers(dest="command", help="Command")
    
    # Process command
    process_parser = subparsers.add_parser("process", help="Process text with an assistant")
    process_parser.add_argument("input", nargs="?", help="Input text or file path")
    process_parser.add_argument("--prompt", "-p", help="Prompt template name")
    process_parser.add_argument("--file", "-f", action="store_true", help="Input is a file path")
    process_parser.add_argument("--output", "-o", help="Output file path")
    process_parser.add_argument("--prompts-file", help="Path to prompts file")
    
    # Delete command
    delete_parser = subparsers.add_parser("delete", help="Delete an assistant")
    delete_parser.add_argument("--id", help="Specific assistant ID to delete")
    
    args = parser.parse_args()
    
    try:
        if args.command == "process":
            # Get input from file or argument
            if args.file and args.input:
                with open(args.input, "r", encoding="utf-8") as f:
                    input_text = f.read()
            elif args.input:
                input_text = args.input
            else:
                # Read from stdin if no input provided
                input_text = sys.stdin.read()
            
            # Process the input
            response = process_with_assistant(
                input_text=input_text,
                module_name=args.module,
                assistant_name=args.assistant,
                prompt_template_name=args.prompt,
                config_file=args.config,
                prompts_file=args.prompts_file
            )
            
            # Output the response
            if args.output:
                with open(args.output, "w", encoding="utf-8") as f:
                    f.write(response)
            else:
                print(response)
                
        elif args.command == "delete":
            # Create client
            client = create_client(
                module_name=args.module,
                assistant_name=args.assistant,
                config_file=args.config
            )
            
            # Delete the assistant
            success = client.delete_assistant(args.id if args.id else None)
            if success:
                print("Assistant deleted successfully")
            else:
                print("Failed to delete assistant")
                
        else:
            parser.print_help()
            sys.exit(1)
            
    except ConfigError as e:
        logger.error(f"Configuration error: {e}")
        print(f"Configuration error: {e}", file=sys.stderr)
        sys.exit(1)
    except AssistantClientError as e:
        logger.error(f"Assistant error: {e}")
        print(f"Assistant error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()





