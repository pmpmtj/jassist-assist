from pathlib import Path
from jassist.download_gdrive.config_loader import load_config
from jassist.download_gdrive.gdrive_downloader import run_download
from jassist.logger_utils.logger_utils import setup_logger
from jassist.utils.path_utils import resolve_path

logger = setup_logger("download_gdrive_cli", module="download_gdrive")

def main():
    try:
        # Get base directory paths
        script_dir = Path(__file__).resolve().parent
        jassist_dir = script_dir.parent
        
        # Path to config using consistent resolution - corrected path
        config_path = resolve_path("download_gdrive/config/download_gdrive_config.json", jassist_dir)

        logger.info(f"Loading configuration from {config_path}")
        config = load_config(config_path)

        logger.info("Starting download process...")
        success = run_download(config)

        if success:
            logger.info("Download process completed successfully.")
        else:
            logger.warning("Download process finished with warnings or partial failure.")
    except Exception as e:
        logger.exception(f"Fatal error in CLI: {e}")

if __name__ == "__main__":
    main()
