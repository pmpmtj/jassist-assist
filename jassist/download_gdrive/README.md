# Google Drive Downloader

This module allows downloading files from Google Drive according to configured criteria.

## Setup

1. Verify the credentials file exists:
   ```
   jassist/credentials/my_credentials.json
   ```

2. Configure the download settings in:
   ```
   jassist/download_gdrive/config/download_gdrive_config.json
   ```

## Usage

Run the module from the project root:

```
python -m jassist.download_gdrive
```

### Configuration Options

- `apis.drive.scopes`: Google API permissions to request (required)
- `auth`: Authentication settings
  - `credentials_file`: Should be set to "my_credentials.json"
  - `credentials_path`: Path to credentials directory (default: "credentials")
- `file_types.include`: File extensions to download
- `folders.target_folders`: Folders to search for files
- `download`: Download behavior settings
  - `add_timestamps`: Add timestamps to downloaded files
  - `delete_after_download`: Remove files from Google Drive after download
  - `dry_run`: If true, only simulate downloads

### Example Configuration

```json
{
    "auth": {
        "credentials_path": "credentials",
        "credentials_file": "my_credentials.json"
    },
    "apis": {
        "drive": {
            "scopes": ["https://www.googleapis.com/auth/drive"]
        }
    },
    "file_types": {
        "include": [".pdf", ".docx", ".xlsx"],
        "exclude": []
    },
    "folders": {
        "target_folders": ["root"]
    },
    "download": {
        "add_timestamps": true,
        "delete_after_download": false,
        "dry_run": true
    }
}
``` 