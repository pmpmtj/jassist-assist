# OpenAI Assistant Client Module

A centralized module for managing and interacting with OpenAI assistants across different features.

## Overview

This module provides a unified interface for working with OpenAI's Assistant API, allowing different features in the application to use assistants with their own specific configurations and prompt templates.

Key features:
- Centralized management of OpenAI assistant configurations
- Strict configuration validation with clear error messages
- Thread management with automatic rotation based on retention policy
- Robust error handling and retry logic
- Module-specific adapters for specialized use cases

## Architecture

The module is structured as follows:

```
api_assistants_cliente/
├── __init__.py                 # Module exports
├── api_assistants_cliente.py   # Main client class
├── api_assistants_cliente_cli.py  # CLI interface
├── config_manager.py           # Configuration loading/management
├── exceptions.py               # Custom exceptions
├── adapters/                   # Module-specific adapters
│   ├── __init__.py
│   ├── calendar_adapter.py     # Calendar-specific adapter
│   └── sample_adapter.py      # Summary-specific adapter
```

## Configuration Structure

Each module must maintain its own configuration files in a specific location:

```
jassist/voice_diary/module_name/
└── config/
    ├── openai_config.json    # OpenAI API settings
    └── prompts.yaml          # Prompt templates
```

Additionally, assistant-specific configurations can be stored in:

```
jassist/voice_diary/config/assistants/
└── module_name_Assistant_Name.json  # Assistant-specific configuration
```

## Required Configuration

The module requires specific configuration files to be present - there are no fallbacks or defaults. Each module must provide:

1. An `openai_config.json` file in its config directory with at minimum:
   ```json
   {
     "api_key": "your-api-key",
     "model": "gpt-4o-mini",
     "assistant_name": "Module Assistant"
   }
   ```

2. A `prompts.yaml` file in its config directory with required prompt templates:
   ```yaml
   prompts:
     prompt_name:
       template: |
         Your prompt template with {variable} placeholders
   ```

## Usage

### Basic Usage

```python
from jassist.voice_diary.api_assistants_cliente import OpenAIAssistantClient

# Create a client with required module name
client = OpenAIAssistantClient(
    module_name="my_module",
    assistant_name="My Assistant" 
)

# Run the assistant with a prompt
response = client.run_assistant("What's the weather today?")
```

### Using Module-Specific Adapters

```python
# Calendar adapter
from jassist.voice_diary.api_assistants_cliente.adapters.calendar_adapter import process_with_calendar_assistant

# Process a calendar entry
result = process_with_calendar_assistant("Schedule a meeting with John tomorrow at 3pm")

# Summary adapter
from jassist.voice_diary.api_assistants_cliente.adapters.sample_adapter import summarize_text

# Summarize text
summary = summarize_text(
    text="Long text to summarize...",
    summary_type="bullet_points",
    target_length=150
)
```

### Using Templates

```python
from jassist.voice_diary.api_assistants_cliente import OpenAIAssistantClient

client = OpenAIAssistantClient(module_name="my_module")

# Process with a template
response = client.process_with_prompt_template(
    input_text="Raw input text",
    prompt_template="Please analyze the following text: {input_text}",
    template_vars={"additional_var": "value"}
)
```

### Command Line Interface

The module includes a command-line interface:

```bash
# Process text with an assistant (requires module name)
python -m jassist.voice_diary.api_assistants_cliente.api_assistants_cliente_cli process "Text to process" --module calendar

# Process a file
python -m jassist.voice_diary.api_assistants_cliente.api_assistants_cliente_cli process input.txt --file --output result.txt --module calendar

# Delete an assistant
python -m jassist.voice_diary.api_assistants_cliente.api_assistants_cliente_cli delete --module calendar
```

## Error Handling

The module uses specific exception types to provide clear error messages:

- `ConfigError`: Raised when configuration files are missing or invalid
- `AssistantError`: Raised for issues with creating or managing assistants
- `ThreadError`: Raised for issues with thread operations
- `RunError`: Raised when assistant runs fail

## Creating a New Adapter

To create an adapter for a new module:

1. Create proper configuration files for your module:
   - `jassist/voice_diary/your_module/config/openai_config.json`
   - `jassist/voice_diary/your_module/config/prompts.yaml`

2. Create a new file in the `adapters` directory (e.g., `your_module_adapter.py`)

3. Create an adapter class that loads configuration and uses `OpenAIAssistantClient`:

```python
from jassist.voice_diary.api_assistants_cliente import OpenAIAssistantClient
from jassist.voice_diary.api_assistants_cliente.exceptions import ConfigError

class YourModuleAdapter:
    def __init__(self):
        self.module_name = "your_module"
        self.client = OpenAIAssistantClient(
            module_name=self.module_name,
            assistant_name="Your Assistant"
        )
    
    def process_something(self, input_text):
        # Load prompts and process with client
        return self.client.run_assistant(input_text)

# Convenience function
def process_with_your_module(input_text):
    adapter = YourModuleAdapter()
    return adapter.process_something(input_text)
``` 