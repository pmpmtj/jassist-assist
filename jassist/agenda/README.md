# Agenda Processing Module

This module allows you to process natural language text into structured calendar events and add them to your database and Google Calendar.

## Features

- Process natural language descriptions into structured calendar event data
- Store events in a database
- Automatically add events to Google Calendar
- CLI interface for easy integration with other tools

## Setup

### Prerequisites

- Python 3.8+
- PostgreSQL database
- Google Cloud Platform account (for Google Calendar API)

### Database Setup

The module requires a PostgreSQL database with the following tables:

1. `eventos_calendario` - Stores calendar events
2. `transcricoes` - Tracks voice transcriptions (optional)

### Google Calendar API Setup

1. Create a project in the [Google Cloud Console](https://console.cloud.google.com/)
2. Enable the Google Calendar API
3. Create OAuth 2.0 credentials
4. Download the credentials JSON file
5. Save it to `jassist/agenda/credentials/credentials.json`

When you first run the application, it will prompt you to authorize access to your Google Calendar.

## Usage

### Command Line Interface

The module provides a command-line interface for processing agenda entries:

```bash
# Basic usage - process text into calendar event
python -m jassist.agenda.agenda_cli --input "make a booking at the barber at 3pm tomorrow" --complete

# Test mode - only extract structured data, don't save to DB or calendar
python -m jassist.agenda.agenda_cli --input "lunch with John on Friday at noon" --test

# Save to database only
python -m jassist.agenda.agenda_cli --input "team meeting on Monday at 10am" --db-only

# Add to Google Calendar only
python -m jassist.agenda.agenda_cli --input "call with client on Thursday at 2pm" --calendar-only

# Process from file
python -m jassist.agenda.agenda_cli --file input.txt --complete

# Pretty-print output
python -m jassist.agenda.agenda_cli --input "dentist appointment next Tuesday at 9am" --test --pretty

# Save output to file
python -m jassist.agenda.agenda_cli --input "weekly report due on Friday" --test --output event.json
```

### Programmatic Usage

You can also use the module programmatically in your Python code:

```python
from jassist.agenda.agenda_cli import parse_agenda_text

# Test mode - just get structured data
success, event_data = parse_agenda_text(
    "meeting with team tomorrow at 3pm", 
    test_mode=True
)

# Complete processing - parse, save to DB, add to calendar
success, event_data = parse_agenda_text(
    "lunch with client on Friday at noon",
    test_mode=False
)

# Only save to database
success, event_data = parse_agenda_text(
    "flight to New York on Monday at 8am",
    db_only=True
)

# Only add to Google Calendar
success, event_data = parse_agenda_text(
    "conference call on Thursday at 2pm",
    calendar_only=True
)
```

## Troubleshooting

### Google Calendar Authorization Issues

If you encounter authorization issues:

1. Delete the `token.json` file from the credentials directory
2. Run the application again to trigger a new authorization flow

### Database Connection Issues

Ensure your database connection settings are correctly configured in your environment variables or configuration files.

## Directory Structure

```
jassist/agenda/
├── __init__.py           # Package initialization
├── agenda_cli.py         # Command-line interface
├── agenda_processor.py   # Main processing logic
├── google_agenda.py      # Google Calendar integration
├── db/                   # Database operations
├── llm/                  # LLM integration
├── utils/                # Utility functions
├── config/               # Configuration files
└── credentials/          # API credentials
``` 