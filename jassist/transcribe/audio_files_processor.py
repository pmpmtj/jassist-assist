import os
import re
import subprocess
import logging
import datetime
from pathlib import Path
from typing import List, Union
from jassist.logger_utils.logger_utils import setup_logger
from jassist.utils.path_utils import resolve_path

logger = setup_logger("audio_files_processor", module="transcribe")

def get_audio_files(directory: Union[str, Path]) -> List[Path]:
    """
    Locate all audio files in a directory and sort them chronologically.
    """
    # Define common audio file extensions
    AUDIO_EXTENSIONS = {'.mp3', '.wav', '.m4a', '.flac', '.aac', '.ogg', '.wma', '.mp4', '.aiff', '.opus'}
    
    # Ensure directory is a Path object
    directory = resolve_path(directory)
    
    if not directory.exists():
        logger.error(f"Audio directory does not exist: {directory}")
        return []

    # Filter for only audio files using the extensions
    files = [f for f in directory.glob("*") if f.is_file() and f.suffix.lower() in AUDIO_EXTENSIONS]
    if not files:
        logger.warning(f"No audio files found in {directory}. Looking for files with extensions: {', '.join(AUDIO_EXTENSIONS)}")
        return []

    def extract_timestamp(path: Path):
        match = re.search(r"(\d{8}_\d{6})", path.name)
        if match:
            try:
                return datetime.datetime.strptime(match.group(1), "%Y%m%d_%H%M%S")
            except ValueError:
                pass
        return datetime.datetime.fromtimestamp(path.stat().st_ctime)

    sorted_files = sorted(files, key=extract_timestamp)
    logger.info(f"{len(sorted_files)} audio files sorted by timestamp.")
    return sorted_files

def calculate_duration(file_path: Union[str, Path]) -> float:
    """
    Calculate audio duration in seconds using ffprobe.
    """
    # Ensure file_path is a Path object
    file_path = resolve_path(file_path)
    
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                str(file_path)
            ],
            capture_output=True,
            text=True
        )
        if result.returncode == 0 and result.stdout.strip():
            return float(result.stdout.strip())
        else:
            logger.warning(f"ffprobe failed on {file_path}: {result.stderr.strip()}")
    except Exception as e:
        logger.error(f"Error getting duration of {file_path}: {e}")

    # Fallback: estimate based on file size (very rough)
    try:
        size_mb = os.path.getsize(file_path) / (1024 * 1024)
        return (size_mb / 3) * 60  # assume 3MB per min
    except:
        return 0.0
