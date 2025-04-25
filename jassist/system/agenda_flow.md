# Agenda Processing Flow Diagram

```mermaid
graph TD
    %% Main Flow
    A[agenda_cli.process] --> B[agenda_processor.process_entry]
    
    %% OpenAI Integration
    B --> C[agenda_adapter.load_config]
    C --> D[agenda_adapter.load_prompts]
    D --> E[api_assistants_cliente.get_existing_assistant]
    E --> F[agenda_adapter.use_assistant]
    F --> G[api_assistants_cliente.run_assistant]
    
    %% Result Processing
    G --> H[agenda_processor.process_result]
    H --> I[json_extractor.extract_json]
    I --> J{JSON Valid?}
    J -->|No| K[json_extractor.parse_json_blocks]
    K --> L[agenda_processor.extract_event_data]
    J -->|Yes| L
    
    %% Database Storage
    L --> M[agenda_db.save_event]
    M --> N[agenda_db.insert_into_db]
    N --> O[agenda_processor.confirm_db_save]
    
    %% Google Calendar Integration
    O --> P[google_agenda.get_service]
    P --> Q[google_agenda.load_credentials]
    Q --> R{Token Exists?}
    R -->|Yes| S[google_agenda.verify_token]
    R -->|No| T[google_agenda.run_oauth_flow]
    S --> U[google_agenda.insert_event]
    T --> U
    U --> V[agenda_processor.confirm_calendar_event]
    
    %% Styling with darker colors and black text
    classDef main fill:#e0a8c0,stroke:#333,stroke-width:1px,color:#000;
    classDef api fill:#cccccc,stroke:#333,stroke-width:1px,color:#000;
    classDef json fill:#a6d9e8,stroke:#333,stroke-width:1px,color:#000;
    classDef db fill:#f2d799,stroke:#333,stroke-width:1px,color:#000;
    classDef calendar fill:#8cd98c,stroke:#333,stroke-width:1px,color:#000;
    classDef decision fill:#f0bc79,stroke:#333,stroke-width:1px,color:#000;
    
    class A,B main;
    class C,D,E,F,G api;
    class H,I,J,K,L json;
    class M,N,O db;
    class P,Q,R,S,T,U,V calendar;
    class J,R decision;
```

## Component Descriptions

### Main CLI Components
- **agenda_cli.process**: Entry point for the agenda processing
- **agenda_processor.process_entry**: Processes the agenda text entry

### OpenAI Assistant Integration
- **agenda_adapter.load_config**: Loads agenda assistant configuration
- **agenda_adapter.load_prompts**: Loads prompt templates from YAML file
- **api_assistants_cliente.get_existing_assistant**: Retrieves existing OpenAI assistant
- **agenda_adapter.use_assistant**: Sets up the assistant for use
- **api_assistants_cliente.run_assistant**: Runs the assistant with the agenda text

### JSON Processing
- **json_extractor.extract_json**: Attempts to extract JSON directly
- **json_extractor.parse_json_blocks**: Parses JSON from code blocks if direct parsing fails
- **agenda_processor.extract_event_data**: Extracts structured event data from the JSON

### Database Operations
- **agenda_db.save_event**: Prepares event data for database storage
- **agenda_db.insert_into_db**: Inserts the event into the database
- **agenda_processor.confirm_db_save**: Confirms successful database storage

### Google Calendar Integration
- **google_agenda.get_service**: Gets the Google Calendar service
- **google_agenda.load_credentials**: Loads Google API credentials
- **google_agenda.verify_token**: Verifies and refreshes the token if needed
- **google_agenda.run_oauth_flow**: Runs OAuth flow for new authentication if needed
- **google_agenda.insert_event**: Inserts the event into Google Calendar
- **agenda_processor.confirm_calendar_event**: Confirms calendar event creation

### Flow Summary
1. The agenda text is processed by the agenda processor
2. The OpenAI assistant is used to interpret the text into structured event data
3. JSON extraction is performed to get the event details
4. The event is saved to the database
5. The event is integrated with Google Calendar for external access
6. Success confirmation is returned to the user 