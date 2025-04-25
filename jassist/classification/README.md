# Classification Module

This module provides functionality for classifying text into different categories using OpenAI's assistants.

## Features

- Classifies text into various categories (diary, calendar, to_do, accounts, contacts, entities)
- Uses OpenAI's Assistants API with a specialized prompt system
- Flexible configuration with centralized JSON config files
- CLI interface for easy integration

## Usage

### Python API

```python
from jassist.classification.classification_processor import classify_text

# Classify a piece of text (uses default response format from config)
result = classify_text("Call John tomorrow at 10am about the budget proposal")
print(result)

# Override the default response format from config
json_result = classify_text("Call John tomorrow at 10am about the budget proposal", response_format="json")
print(json_result)
```

Expected output format (text mode):
```
text: "Call John tomorrow at 10am"
tag: calendar

text: "Call John"
tag: contacts

text: "about the budget proposal"
tag: to_do
```

JSON output format:
```json
{
  "classifications": [
    {
      "text": "Call John tomorrow at 10am",
      "category": "calendar"
    },
    {
      "text": "Call John",
      "category": "contacts"
    },
    {
      "text": "about the budget proposal",
      "category": "to_do"
    }
  ]
}
```

### Command Line Interface

```bash
# Classify text from a file (uses default response format from config)
python -m jassist.classification.classification_cli --input input.txt --file

# Classify text directly from argument
python -m jassist.classification.classification_cli --input "Call John tomorrow at 10am about the budget proposal"

# Pipe text to the CLI
echo "Call John tomorrow at 10am about the budget proposal" | python -m jassist.classification.classification_cli

# Override config and output in JSON format
python -m jassist.classification.classification_cli --input input.txt --file --json

# Save output to a file
python -m jassist.classification.classification_cli --input input.txt --file --output result.txt
```

## Configuration

The module uses configuration files located in the `jassist/classification/config` directory:

- `classification_assistant_config.json`: Configuration for the OpenAI assistant, including:
  - `model`: OpenAI model to use
  - `temperature`: Model temperature
  - `default_response_format`: Default output format ("text" or "json")
  - Other OpenAI assistant settings

- `prompts.yaml`: Prompt templates for classification

To change the default response format, edit the `default_response_format` field in `classification_assistant_config.json`.

### Classification Categories

The classification system currently supports these categories:

- `diary`: Personal reflections, moods, or subjective experiences
- `calendar`: Events with date/time information
- `to_do`: Tasks or action items
- `accounts`: Financial information like income or expenses
- `contacts`: Names, phone numbers, or emails
- `entities`: Organizations, companies, or web sites 