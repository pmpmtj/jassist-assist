# Transcription Flow Diagram

```mermaid
graph TD
    %% Main Flow
    A[transcribe_cli.main] --> B[config_loader.load_env_variables]
    A --> C[config_loader.load_config]
    A --> D[model_handler.get_model]
    D --> E[model_handler.initialize_client]
    A --> G[transcribe_db.initialize_database]
    A --> H[transcribe_cli.setup_directories]
    A --> I[audio_files_processor.sort_files]
    A --> J{Process Each Audio File}
    
    %% Transcription Flow
    J --> K[transcriber.transcribe_audio]
    K --> L[transcriber.get_duration]
    K --> M[model_handler.get_model]
    K --> N[transcriber.prepare_transcription]
    N --> O[transcriber.submit_transcription]
    O --> P[transcribe_db.save_transcription]
    P --> Q[transcribe_db.save_raw_transcription]
    P --> R[transcribe_cli.save_to_file]
    
    %% Completion & Cleanup
    R --> S{More Files?}
    S -->|Yes| J
    S -->|No| T[transcribe_cli.report_completion]
    T --> U[transcribe_cli.cleanup_downloads]
    
    %% Styling with darker colors and black text
    classDef main fill:#e0a8c0,stroke:#333,stroke-width:1px,color:#000;
    classDef config fill:#cccccc,stroke:#333,stroke-width:1px,color:#000;
    classDef model fill:#a6d9e8,stroke:#333,stroke-width:1px,color:#000;
    classDef db fill:#f2d799,stroke:#333,stroke-width:1px,color:#000;
    classDef files fill:#8cd98c,stroke:#333,stroke-width:1px,color:#000;
    classDef trans fill:#d6b5e5,stroke:#333,stroke-width:1px,color:#000;
    classDef decision fill:#f0bc79,stroke:#333,stroke-width:1px,color:#000;
    
    class A,H,T,U main;
    class B,C config;
    class D,E,M model;
    class F,G,P,Q db;
    class I,R,S files;
    class J,K,L,N,O trans;
    class J,S decision;
```

## Component Descriptions

### Main CLI Components
- **transcribe_cli.main**: Entry point for the transcription CLI
- **transcribe_cli.setup_directories**: Sets up download and output directories
- **transcribe_cli.save_to_file**: Saves transcription to text file
- **transcribe_cli.report_completion**: Reports on completed transcriptions
- **transcribe_cli.cleanup_downloads**: Cleans up processed audio files

### Configuration
- **config_loader.load_env_variables**: Loads environment variables
- **config_loader.load_config**: Loads transcription configuration

### Model Handling
- **model_handler.get_model**: Fetches transcription model from config
- **model_handler.initialize_client**: Initializes OpenAI client

### Database Operations
- **transcribe_db.create_tables**: Creates database tables
- **transcribe_db.initialize_database**: Initializes database
- **transcribe_db.save_transcription**: Saves transcription to database
- **transcribe_db.save_raw_transcription**: Saves raw transcription data

### File Processing
- **audio_files_processor.sort_files**: Sorts audio files by timestamp
- **transcriber.get_duration**: Gets audio file duration

### Transcription Process
- **transcriber.transcribe_audio**: Main transcription function
- **transcriber.prepare_transcription**: Prepares transcription request
- **transcriber.submit_transcription**: Submits transcription to API

### Flow Summary
1. Configuration is loaded from files and environment
2. Model is initialized for transcription
3. Database is set up to store transcriptions
4. Audio files are processed one by one
5. Transcriptions are saved to database and files
6. Processed files are cleaned up after completion 