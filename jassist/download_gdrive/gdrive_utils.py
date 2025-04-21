# gdrive_utils.py
import os
import datetime
import traceback
from pathlib import Path
from googleapiclient.http import MediaIoBaseDownload
from jassist.logger_utils.logger_utils import setup_logger

logger = setup_logger("gdrive_utils", module="download_gdrive")

def find_folder_by_name(service, folder_name):
    try:
        query = f"mimeType='application/vnd.google-apps.folder' and name='{folder_name}' and trashed=false"
        results = service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
        folders = results.get('files', [])
        if folders:
            folder_id = folders[0]['id']
            logger.info(f"Found folder '{folder_name}' with ID: {folder_id}")
            return folder_id
        logger.warning(f"No folder named '{folder_name}' found.")
    except Exception as e:
        logger.error(f"Error finding folder '{folder_name}': {e}")
        logger.debug(traceback.format_exc())
    return None

def download_file(service, file_id, file_path):
    try:
        request = service.files().get_media(fileId=file_id)
        with open(file_path, 'wb') as f:
            downloader = MediaIoBaseDownload(f, request)
            done = False
            while not done:
                status, done = downloader.next_chunk()
                logger.debug(f"Download {int(status.progress() * 100)}% complete for {file_path}")
        
        file_size = Path(file_path).stat().st_size
        readable_size = format_file_size(file_size)
        logger.info(f"Download completed: {file_path} ({readable_size})")
        return {"success": True, "path": str(file_path), "size": file_size}
    except Exception as e:
        logger.error(f"Failed to download file {file_id}: {e}")
        logger.debug(traceback.format_exc())
        return {"success": False, "error": str(e)}

def format_file_size(size_bytes):
    """Format file size in human-readable format"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0 or unit == 'GB':
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0

def delete_file(service, file_id, file_name=None):
    try:
        service.files().delete(fileId=file_id).execute()
        display_name = file_name or file_id
        logger.info(f"🗑️ Successfully deleted file from Google Drive: {display_name}")
        logger.debug(f"Deleted file with ID: {file_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to delete file {file_name or file_id}: {e}")
        logger.debug(traceback.format_exc())
        return False

def generate_filename_with_timestamp(filename, timestamp_format="%Y%m%d_%H%M%S_%f"):
    try:
        timestamp = datetime.datetime.now().strftime(timestamp_format)
        return f"{timestamp}_{filename}"
    except Exception as e:
        logger.error(f"Error generating timestamped filename for {filename}: {e}")
        logger.debug(traceback.format_exc())
        return filename
