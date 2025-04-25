# Database Utilities Flow Diagram

```mermaid
graph TD
    %% Main Flow
    A[setup_database.initialize] --> B[db_env_utils.get_env_variables]
    B --> C[db_env_utils.load_env_file]
    C --> D[db_env_utils.validate_db_url]
    D --> E[db_connection.initialize_db]
    E --> F[db_connection.test_connection]
    F --> G[db_connection.create_connection_pool]
    G --> H[setup_database.create_tables]
    H --> I[db_schema.create_tables_with_fts]
    
    %% Styling with darker colors and black text
    classDef main fill:#e0a8c0,stroke:#333,stroke-width:1px,color:#000;
    classDef env fill:#cccccc,stroke:#333,stroke-width:1px,color:#000;
    classDef conn fill:#a6d9e8,stroke:#333,stroke-width:1px,color:#000;
    classDef schema fill:#f2d799,stroke:#333,stroke-width:1px,color:#000;
    
    class A,H main;
    class B,C,D env;
    class E,F,G conn;
    class I schema;
```

## Component Descriptions

### Database Setup
- **setup_database.initialize**: Entry point for database initialization
- **setup_database.create_tables**: Triggers creation of database tables

### Environment Handling
- **db_env_utils.get_env_variables**: Retrieves environment variables from system
- **db_env_utils.load_env_file**: Loads variables from .env file
- **db_env_utils.validate_db_url**: Validates the database connection URL

### Database Connection
- **db_connection.initialize_db**: Initializes database connection
- **db_connection.test_connection**: Tests direct connection to PostgreSQL
- **db_connection.create_connection_pool**: Creates a connection pool for efficiency

### Schema Management
- **db_schema.create_tables_with_fts**: Creates all database tables with Full Text Search capability

### Flow Summary
1. Environment variables are loaded and validated
2. Database connection is established and tested
3. Connection pool is created for efficient database access
4. Database tables are created with Full Text Search support 