# Google Drive Download Flow Diagram

```mermaid
graph TD
    %% Main Flow
    A[download_gdrive_cli.main] --> B[load_config]
    A --> C[run_download]
    
    %% Authentication Flow
    C --> D[get_service - auth_manager]
    D --> E[load_auth_config]
    D --> F[get_credentials]
    F --> G{Token Exists?}
    G -->|Yes| H{Token Expired?}
    H -->|Yes| I[Refresh Token]
    H -->|No| J[Use Existing Token]
    G -->|No| K[Run OAuth Flow]
    I --> L[Save Refreshed Token]
    K --> M[Save New Token]
    L --> N[Return Credentials]
    M --> N
    J --> N
    N --> O[build API Service]
    
    %% Download Flow
    C --> P[Process Target Folders]
    P --> Q[find_folder_by_name]
    P --> R[process_folder]
    R --> S[Query for Files]
    S --> T[Filter by Extension]
    T --> U[Prepare Download Directory]
    U --> V{For Each File}
    V --> W{Add Timestamp?}
    W -->|Yes| X[generate_filename_with_timestamp]
    W -->|No| Y[Use Original Filename]
    X --> Z[download_file]
    Y --> Z
    Z --> AA{Delete After Download?}
    AA -->|Yes| AB[delete_file]
    AA -->|No| AC[Continue to Next File]
    AB --> AC
    AC --> AD{More Files?}
    AD -->|Yes| V
    AD -->|No| AE[Log Download Summary]
    
    %% Return Flow
    AE --> AF[Return Success Status]
    AF --> AG[CLI Reports Completion]
    
    %% Styling with darker colors and black text
    classDef main fill:#e0a8c0,stroke:#333,stroke-width:1px,color:#000;
    classDef auth fill:#cccccc,stroke:#333,stroke-width:1px,color:#000;
    classDef process fill:#a6d9e8,stroke:#333,stroke-width:1px,color:#000;
    classDef decision fill:#f2d799,stroke:#333,stroke-width:1px,color:#000;
    classDef file fill:#8cd98c,stroke:#333,stroke-width:1px,color:#000;
    
    class A,B,C,AG main;
    class D,E,F,G,H,I,J,K,L,M,N,O auth;
    class P,Q,R,S,T,U,V,X,Y,Z,AA,AB,AC,AD,AE,AF process;
    class G,H,W,AA,AD decision;
```

## Component Descriptions

### Main CLI Components
- **download_gdrive_cli.main**: Entry point for the download from Google Drive CLI
- **load_config**: Loads configuration from download_gdrive_config.json
- **run_download**: Main function that orchestrates the download process

### Authentication Components
- **get_service**: Creates authenticated API service
- **load_auth_config**: Loads authentication configuration
- **get_credentials**: Retrieves or refreshes Google API credentials
- **OAuth Flow**: User authentication if needed

### Download Process
- **find_folder_by_name**: Locates target Google Drive folders
- **process_folder**: Processes files in a specific folder
- **download_file**: Downloads individual files from Google Drive
- **delete_file**: Optionally deletes files after download
- **generate_filename_with_timestamp**: Adds timestamps to filenames

### File Processing
- Files are filtered based on configured file extensions
- Timestamps can be added to filenames during download
- Files can be optionally deleted from Google Drive after download 