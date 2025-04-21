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
    try:
        service = get_service(config)
        if not service:
            logger.error("Google Drive authentication failed.")
            return False

        target_folders = config['folders'].get('target_folders', ['root'])
        dry_run = config.get('download', {}).get('dry_run', False)

        if dry_run:
            logger.info("Running in DRY RUN mode")
            print("\n=== DRY RUN MODE - NO FILES WILL BE DOWNLOADED OR DELETED ===\n")

        for folder_name in target_folders:
            try:
                folder_id = 'root' if folder_name.lower() == 'root' else find_folder_by_name(service, folder_name)
                if not folder_id:
                    logger.warning(f"Folder '{folder_name}' not found. Skipping.")
                    continue

                logger.info(f"Processing folder: {folder_name} (ID: {folder_id})")
                process_folder(service, folder_id, folder_name, config, dry_run=dry_run)
            except Exception as e:
                logger.error(f"Error processing folder '{folder_name}': {e}")
                logger.debug(traceback.format_exc())

        logger.info("Google Drive download process completed.")
        return True

    except Exception as e:
        logger.error(f"Unexpected error in run_download: {e}")
        logger.debug(traceback.format_exc())
        return False

def process_folder(service, folder_id, folder_name, config, dry_run=False):
    try:
        query = f"'{folder_id}' in parents and mimeType != 'application/vnd.google-apps.folder' and trashed = false"
        results = service.files().list(
            q=query,
            fields="files(id, name, mimeType, size, modifiedTime, fileExtension)",
            pageSize=1000
        ).execute()

        all_items = results.get('files', [])
        audio_extensions = config.get('audio_file_types', {}).get('include', [])
        audio_items = [item for item in all_items if any(item['name'].lower().endswith(ext) for ext in audio_extensions)]

        # Downloads directory is hardcoded as per design decision
        downloads_dir = "downloaded"
        script_dir = Path(__file__).resolve().parent
        voice_diary_dir = script_dir.parent
        
        # Use consistent path resolution
        base_download_dir = resolve_path(downloads_dir, voice_diary_dir)
        ensure_directory_exists(base_download_dir, "download directory")

        for item in audio_items:
            item_id = item['id']
            item_name = item['name']
            output_filename = item_name

            if config.get('download', {}).get('add_timestamps', False):
                timestamp_format = config.get('download', {}).get('timestamp_format', '%Y%m%d_%H%M%S_%f')
                output_filename = generate_filename_with_timestamp(item_name, timestamp_format)

            output_path = base_download_dir / output_filename

            if dry_run:
                logger.info(f"Would download: {item_name} -> {output_path}")
                continue

            result = download_file(service, item_id, str(output_path))
            if result['success'] and config.get('download', {}).get('delete_after_download', False):
                delete_file(service, item_id, item_name)

        logger.info(f"Finished processing folder: {folder_name}")

    except Exception as e:
        logger.error(f"Error in process_folder for '{folder_name}': {e}")
        logger.debug(traceback.format_exc())
