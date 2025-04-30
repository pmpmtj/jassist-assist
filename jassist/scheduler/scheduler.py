import json
import os
import sys
import time
import traceback
import threading
from datetime import datetime, timedelta
import subprocess
from pathlib import Path
from jassist.logger_utils.logger_utils import setup_logger
from jassist.pipeline.pipeline import run_pipeline as execute_pipeline
from jassist.utils.file_tools import clean_directory, ensure_file_exists

# === Constants ===
SCRIPT_DIR = Path(__file__).resolve().parent
STATE_FILE = SCRIPT_DIR / 'pipeline_state.json'
CONFIG_FILE = SCRIPT_DIR / 'config' / 'scheduler_config.json'
SECOND_SCRIPT = SCRIPT_DIR / 'second_script.py'
TRANSCRIPTIONS_DIR = Path(__file__).resolve().parent.parent / 'transcriptions'

# Set up logger
logger = setup_logger("scheduler", module="scheduler")

# === Config Handling ===
def load_config():
    if not os.path.exists(CONFIG_FILE):
        logger.error(f"Config file not found at: {CONFIG_FILE}")
        sys.exit(1)
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = json.load(f)
        if "scheduler" not in config:
            raise ValueError("Missing 'scheduler' section in scheduler_config.json")
        return config
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        sys.exit(1)

def validate_config(config):
    scheduler = config.get("scheduler", {})
    if "runs_per_day" not in scheduler:
        raise ValueError("Missing 'runs_per_day' in scheduler section")
    if not isinstance(scheduler["runs_per_day"], (int, float)):
        raise ValueError("runs_per_day must be a number")

# === Interval Calculation ===
def calculate_interval_seconds(runs_per_day):
    return 0 if runs_per_day == 0 else int(86400 / runs_per_day)

def calculate_next_run_time(interval_seconds):
    now = datetime.now()
    return now + timedelta(seconds=interval_seconds)

# === State Saving ===
def update_pipeline_state(state_file, updates):
    try:
        with open(state_file, 'w') as f:
            json.dump(updates, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to update state file: {e}")
        raise

# === Clean Transcriptions Directory ===
def clean_transcriptions():
    logger.debug(f"Cleaning transcriptions directory: {TRANSCRIPTIONS_DIR}")
    result = clean_directory(TRANSCRIPTIONS_DIR)
    if result["status"] == "success":
        logger.info(f"Cleaned transcriptions directory: {result['files_deleted']} files removed")
    else:
        logger.warning(f"Failed to clean transcriptions directory: {result['message']}")
    return result

# === Main Pipeline Execution ===
def run_pipeline():
    logger.info("Executing main pipeline...")
    try:
        # Execute the pipeline module
        success = execute_pipeline()
        
        # Update state with run results
        state = {
            "last_run_time": datetime.now().isoformat(),
            "last_run_status": "success" if success else "failed"
        }
        update_pipeline_state(STATE_FILE, state)
        return success
    except Exception as e:
        logger.error(f"Pipeline execution error: {e}", exc_info=True)
        state = {
            "last_run_time": datetime.now().isoformat(),
            "last_run_status": "error",
            "error_message": str(e)
        }
        update_pipeline_state(STATE_FILE, state)
        return False

# === Second Script Logic (Placeholder) ===
def run_second_script():
    logger.info("Second script scheduler triggered - implementation pending")
    # Pass function for now - will be implemented later
    pass

# === Second Script Scheduler ===
def get_seconds_until_2355():
    now = datetime.now()
    target_today = now.replace(hour=23, minute=55, second=0, microsecond=0)
    midnight = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    seconds_until_midnight = (midnight - now).total_seconds()

    if now < target_today:
        if seconds_until_midnight < 5 * 60:
            target = target_today + timedelta(days=1)
        else:
            target = target_today
    else:
        target = target_today + timedelta(days=1)

    return (target - now).total_seconds()

def second_script_scheduler():
    while True:
        sleep_time = get_seconds_until_2355()
        logger.info(f"Next second script run scheduled in {sleep_time:.0f} seconds (at 23:55).")
        time.sleep(sleep_time)
        run_second_script()

# === Main Scheduler ===
def main():
    logger.info("Starting scheduler...")

    try:
        # Ensure pipeline state file exists
        default_state = {
            "last_run_time": datetime.now().isoformat(),
            "last_run_status": "pending"
        }
        state_result = ensure_file_exists(STATE_FILE, default_state)
        if state_result["status"] == "success" and state_result["created"]:
            logger.info(f"Created pipeline state file: {STATE_FILE}")
        elif state_result["status"] == "error":
            logger.error(f"Failed to ensure pipeline state file: {state_result['message']}")
        
        config = load_config()
        validate_config(config)
        interval = calculate_interval_seconds(config["scheduler"]["runs_per_day"])

        # Start second script scheduler in parallel thread
        second_thread = threading.Thread(target=second_script_scheduler, daemon=True)
        second_thread.start()
        logger.info("Started second script scheduler thread.")

        if interval == 0:
            logger.info("Main pipeline: Running once and exiting")
            run_pipeline()
            clean_transcriptions()
        else:
            # Main loop for recurring execution
            while True:
                run_pipeline()
                
                # Clean the transcriptions directory after pipeline run
                clean_transcriptions()
                
                # Calculate and display next run time
                next_run = calculate_next_run_time(interval)
                logger.info(f"Next main pipeline run at: {next_run.strftime('%Y-%m-%d %H:%M:%S')}")
                time.sleep(interval)

    except KeyboardInterrupt:
        logger.info("Scheduler interrupted by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        logger.error(traceback.format_exc())
    finally:
        input("Press Enter to exit...")

if __name__ == "__main__":
    main()
