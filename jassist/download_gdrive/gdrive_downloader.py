# gdrive_downloader.py
import datetime
import traceback
from pathlib import Path
from jassist.logger_utils.logger_utils import setup_logger
from jassist.google_auth.auth_manager import get_service
from jassist.utils.path_utils import resolve_path
from jassist.utils.path_utils import ensure_directory_exists
from jassist.download_gdrive.gdrive_utils import (
    find_folder_by_name,
    download_file,
    delete_file,
    generate_filename_with_timestamp
)

logger = setup_logger("gdrive_downloader", module="download_gdrive")

def run_download(config: dict) -> bool:
    """
    Run the Google Drive download process based on the provided configuration.
    
    Args:
        config: Dictionary containing download configuration
        
    Returns:
        bool: True if download was successful, False otherwise
    """
    try:
        logger.debug("Initializing Google Drive service")
        # Get service without passing config - auth config will be loaded from google_auth_config.json
        service = get_service("drive", "v3")
        if not service:
            logger.error("Google Drive authentication failed.")
            return False

        target_folders = config['folders'].get('target_folders', ['root'])
        dry_run = config.get('download', {}).get('dry_run', False)
        
        # Stats tracking
        stats = {
            "folders_processed": 0,
            "files_found": 0,
            "files_downloaded": 0,
            "files_deleted": 0,
            "errors": 0
        }

        if dry_run:
            logger.info("Running in DRY RUN mode")
            print("\n=== DRY RUN MODE - NO FILES WILL BE DOWNLOADED OR DELETED ===\n")

        for folder_name in target_folders:
            try:
                logger.debug(f"Looking for folder: {folder_name}")
                folder_id = 'root' if folder_name.lower() == 'root' else find_folder_by_name(service, folder_name)
                if not folder_id:
                    logger.warning(f"Folder '{folder_name}' not found. Skipping.")
                    continue

                logger.info(f"Processing folder: {folder_name} (ID: {folder_id})")
                folder_stats = process_folder(service, folder_id, folder_name, config, dry_run=dry_run)
                
                # Update statistics
                stats["folders_processed"] += 1
                stats["files_found"] += folder_stats.get("files_found", 0)
                stats["files_downloaded"] += folder_stats.get("files_downloaded", 0)
                stats["files_deleted"] += folder_stats.get("files_deleted", 0)
                stats["errors"] += folder_stats.get("errors", 0)
                
            except Exception as e:
                logger.error(f"Error processing folder '{folder_name}': {e}")
                logger.debug(traceback.format_exc())
                stats["errors"] += 1

        # Log summary
        logger.info("=== Google Drive Download Summary ===")
        logger.info(f"Folders processed: {stats['folders_processed']}")
        logger.info(f"Files found: {stats['files_found']}")
        logger.info(f"Files downloaded: {stats['files_downloaded']}")
        
        if config.get('download', {}).get('delete_after_download', False):
            logger.info(f"Files deleted from Google Drive: {stats['files_deleted']}")
            
        if stats["errors"] > 0:
            logger.warning(f"Errors encountered: {stats['errors']}")
            
        if dry_run:
            logger.info("THIS WAS A DRY RUN - No actual changes were made")

        return stats["errors"] == 0

    except Exception as e:
        logger.error(f"Unexpected error in run_download: {e}")
        logger.debug(traceback.format_exc())
        return False

def process_folder(service, folder_id, folder_name, config, dry_run=False):
    """
    Process a specific Google Drive folder, downloading files according to configuration.
    
    Args:
        service: Google Drive API service
        folder_id: ID of the folder to process
        folder_name: Name of the folder (for logging)
        config: Download configuration
        dry_run: If True, only simulate downloads without actual changes
        
    Returns:
        dict: Statistics about processing results
    """
    # Stats tracking
    stats = {
        "files_found": 0,
        "files_downloaded": 0,
        "files_deleted": 0,
        "errors": 0
    }
    
    try:
        logger.debug(f"Querying for files in folder: {folder_name}")
        query = f"'{folder_id}' in parents and mimeType != 'application/vnd.google-apps.folder' and trashed = false"
        results = service.files().list(
            q=query,
            fields="files(id, name, mimeType, size, modifiedTime, fileExtension)",
            pageSize=1000
        ).execute()

        all_items = results.get('files', [])
        logger.debug(f"Found {len(all_items)} files in folder {folder_name}")
        stats["files_found"] = len(all_items)
        
        # Filter files by extensions according to config
        file_extensions = config.get('file_types', {}).get('include', [])
        filtered_items = [item for item in all_items if any(item['name'].lower().endswith(ext) for ext in file_extensions)]
        logger.info(f"Found {len(filtered_items)} files matching configured extensions in folder {folder_name}")

        # Downloads directory is hardcoded as per design decision
        downloads_dir = "downloaded"
        script_dir = Path(__file__).resolve().parent
        jassist_dir = script_dir.parent
        
        # Use consistent path resolution
        base_download_dir = resolve_path(downloads_dir, jassist_dir)
        ensure_directory_exists(base_download_dir, "download directory")
        logger.debug(f"Download directory set to: {base_download_dir}")

        for item in filtered_items:
            item_id = item['id']
            item_name = item['name']
            output_filename = item_name

            if config.get('download', {}).get('add_timestamps', False):
                timestamp_format = config.get('download', {}).get('timestamp_format', '%Y%m%d_%H%M%S_%f')
                output_filename = generate_filename_with_timestamp(item_name, timestamp_format)
                logger.debug(f"Added timestamp to filename: {output_filename}")

            output_path = base_download_dir / output_filename
            logger.debug(f"Preparing to download {item_name} to {output_path}")

            if dry_run:
                logger.info(f"Would download: {item_name} -> {output_path}")
                if config.get('download', {}).get('delete_after_download', False):
                    logger.info(f"Would delete: {item_name} from Google Drive")
                continue

            result = download_file(service, item_id, str(output_path))
            if result['success']:
                logger.info(f"✅ Successfully downloaded: {item_name} -> {output_path}")
                stats["files_downloaded"] += 1
                
                if config.get('download', {}).get('delete_after_download', False):
                    logger.debug(f"Attempting to delete source file after successful download: {item_name}")
                    delete_result = delete_file(service, item_id, item_name)
                    
                    if delete_result:
                        logger.info(f"🔄 Download and delete completed for: {item_name}")
                        stats["files_deleted"] += 1
                    else:
                        logger.warning(f"⚠️ File downloaded but deletion failed: {item_name}")
                        stats["errors"] += 1
            else:
                logger.error(f"❌ Failed to download: {item_name}")
                logger.debug(f"Error: {result.get('error', 'Unknown error')}")
                stats["errors"] += 1

        logger.info(f"Finished processing folder: {folder_name}")
        return stats

    except Exception as e:
        logger.error(f"Error in process_folder for '{folder_name}': {e}")
        logger.debug(traceback.format_exc())
        stats["errors"] += 1
        return stats
