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
        "delete_after_download": false,
        "dry_run": true
    }
}
``` 