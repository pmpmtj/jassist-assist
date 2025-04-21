# Google Drive Downloader

This module allows downloading files from Google Drive according to configured criteria.

## Setup

1. Verify the credentials file exists:
   ```
   jassist/credentials/my_credentials.json
   ```

2. Verify the Google Auth configuration:
   ```
   jassist/google_auth/config/google_auth_config.json
   ```

3. Configure the download settings in:
   ```
   jassist/download_gdrive/config/download_gdrive_config.json
   ```

## Usage

Run the module from the project root:

```
python -m jassist.download_gdrive
```

Or test the authentication:
```
python -m jassist.google_auth
```

### Features

- Filter files by extension (`.pdf`, `.mp3`, etc.)
- Target specific folders in Google Drive
- Add timestamps to downloaded filenames
- Delete files from Google Drive after successful download
- Dry-run mode to simulate operations
- Detailed logging with download progress and statistics

### Configuration

#### Google Auth Config (`google_auth_config.json`)
Contains authentication settings and API scopes:

```json
{
    "auth": {
        "credentials_path": "credentials",
        "credentials_file": "my_credentials.json",
        "token_file": "token.pickle"
    },
    "apis": {
        "drive": {
            "scopes": ["https://www.googleapis.com/auth/drive"]
        }
    }
}
```

#### Downloader Config (`download_gdrive_config.json`)
Contains download behavior settings:

```json
{
    "file_types": {
        "include": [".pdf", ".docx", ".xlsx"],
        "exclude": []
    },
    "folders": {
        "target_folders": ["root"]
    },
    "download": {
        "add_timestamps": true,
        "timestamp_format": "%Y%m%d_%H%M%S_%f",
        "delete_after_download": false,
        "dry_run": true
    }
}
```

### Logging

The module provides detailed logging including:

- Download progress and file sizes
- Successful and failed file deletions
- End-of-run statistics showing:
  - Number of folders processed
  - Number of files found
  - Number of files downloaded
  - Number of files deleted from Google Drive
  - Any errors encountered

### Security

- The module requires Google API credentials with appropriate permissions
- Deletion operations are only performed after successful download
- Dry-run mode allows testing configuration without making changes 