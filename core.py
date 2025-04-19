import cv2
import numpy as np
import mss
import time
import os
import logging
import re
from logging.handlers import RotatingFileHandler
from datetime import datetime, timedelta
from pathlib import Path
import platform
from dotenv import load_dotenv
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from PIL import Image

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env", override=True)
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(parents=True,exist_ok=True)
RECORDING_DIR = BASE_DIR / "recordings"
RECORDING_DIR.mkdir(parents=True,exist_ok=True)
FOLDER_ID = os.getenv("FOLDER_ID")
RETENTION_DAYS = int(os.getenv("RETENTION_DAYS",7))
MAX_THREADS = int(os.getenv("MAX_THREADS",3))

def setup_logger(name="screen_recorder", log_file="screen_recorder.log"):
    """
    Set up a logger with a RotatingFileHandler and StreamHandler.
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    
    # Rotating file handler (5 MB per file, up to 5 backup files)
    file_handler = RotatingFileHandler(LOG_DIR / log_file, maxBytes=5*1024*1024, backupCount=5,encoding='utf-8')
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG)

    # Stream handler (console)
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    stream_handler.setLevel(logging.INFO)

    # Avoid duplicate logs
    if not logger.hasHandlers():
        logger.addHandler(file_handler)
        logger.addHandler(stream_handler)
    
    return logger

logger = setup_logger()

def upload_to_google_drive_service(folder_id = None, file_path = None):
    """
    Upload a file to Google Drive using a service account.
    Checks if a file with the same name already exists before uploading.
    """
    SERVICE_ACCOUNT_FILE = BASE_DIR / 'service_account.json'
    SCOPES = ['https://www.googleapis.com/auth/drive.file']

    try:
        credentials = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE,
            scopes=SCOPES
        )

        service = build('drive', 'v3', credentials=credentials)
        file_name = os.path.basename(file_path)

        # Build query to check for file with the same name
        query = f"name = '{file_name}' and trashed = false"
        if folder_id:
            query += f" and '{folder_id}' in parents"

        results = service.files().list(
            q=query,
            spaces='drive',
            fields="files(id, name)",
            pageSize=1
        ).execute()

        if results.get('files'):
            logger.info(f"File '{file_name}' already exists in Drive. Skipping upload.")
            return

        file_metadata = {'name': file_name}
        if folder_id:
            file_metadata['parents'] = [folder_id]

        media = MediaFileUpload(file_path, mimetype='video/mp4')
        uploaded_file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id, name, webViewLink'
        ).execute()

        logger.info(f"Uploaded to Google Drive: {uploaded_file['name']}")
        logger.info(f"View link: {uploaded_file['webViewLink']}")
    except Exception as e:
        logger.exception(f"Failed to upload to Google Drive: {e}")

def delete_old_drive_files(days_old=7, folder_id=None):
    """
    Deletes files older than `days_old` days from Google Drive.
    Optionally, restricts deletion to a specific folder.
    """
    SERVICE_ACCOUNT_FILE = BASE_DIR / 'service_account.json'
    SCOPES = ['https://www.googleapis.com/auth/drive']

    try:
        credentials = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE,
            scopes=SCOPES
        )
        service = build('drive', 'v3', credentials=credentials)

        # Calculate cutoff datetime in RFC 3339 format
        cutoff_date = (datetime.utcnow() - timedelta(days=days_old)).isoformat() + 'Z'

        # Build query
        query = f"modifiedTime < '{cutoff_date}' and trashed = false"
        if folder_id:
            query += f" and '{folder_id}' in parents"

        logger.info(f"Looking for files older than {days_old} days (before {cutoff_date})")

        page_token = None
        deleted_count = 0

        while True:
            results = service.files().list(
                q=query,
                spaces='drive',
                fields='nextPageToken, files(id, name, modifiedTime)',
                pageToken=page_token
            ).execute()

            files = results.get('files', [])

            for file in files:
                file_id = file['id']
                file_name = file['name']
                mod_time = file['modifiedTime']
                service.files().delete(fileId=file_id).execute()
                deleted_count += 1
                logger.info(f"Deleted '{file_name}' last modified on {mod_time}")

            page_token = results.get('nextPageToken', None)
            if not page_token:
                break

        logger.info(f"Finished deleting. Total files deleted: {deleted_count}")
    except Exception as e:
        logger.exception(f"Error deleting old files from Google Drive: {e}")

def delete_old_recordings(days_old=7):
    "Delete the recordings the local device"
    today = datetime.now().date()
    cutoff_date = today - timedelta(days=days_old)

    logger.info(f"Starting cleanup. Retention: {RETENTION_DAYS} days. Cutoff date: {cutoff_date}")

    # Pattern: screen_recording_YYYYMMDD_HHMMSS.mp4
    pattern = re.compile(r"screen_recording_(\d{8})_\d{6}\.mp4")

    deleted_count = 0
    skipped_count = 0

    for file_path in RECORDING_DIR.glob("*.mp4"):
        try:
            match = pattern.match(file_path.name)
            if match:
                file_date = datetime.strptime(match.group(1), "%Y%m%d").date()
                if file_date < cutoff_date:
                    logger.info(f"Deleting old file: {file_path.name} (Date: {file_date})")
                    file_path.unlink()
                    deleted_count += 1
                else:
                    logger.debug(f"Skipping recent file: {file_path.name} (Date: {file_date})")
                    skipped_count += 1
            else:
                logger.warning(f"Filename doesn't match pattern, skipping: {file_path.name}")
                skipped_count += 1
        except Exception as e:
            logger.exception(f"Error processing file {file_path.name}: {e}")

    logger.info(f"Cleanup complete. Deleted: {deleted_count}, Skipped: {skipped_count}")

def screen_recorder_segment(output_directory="recordings", resolution=(1280, 720), fps=1, recording_end_time="9pm" ,segment_duration_minutes=60, compression_quality=100,stop_event=None):
    """
    Record the screen for a specified duration and save it as a compressed MP4 file.
    """
    
    current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = os.path.join(output_directory, f"screen_recording_{current_time}.mp4")
    
    system_platform = platform.system()
    if system_platform == "Windows":
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # More reliable on Windows
    elif system_platform == "Darwin":  # macOS
        fourcc = cv2.VideoWriter_fourcc(*'avc1')  # H.264 compatible on most Macs
    else:
        logger.warning("Unknown platform. Falling back to 'mp4v'")
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, resolution)
    
    logger.info(f"Recording started: {output_path}")
    logger.debug(f"Resolution: {resolution}, FPS: {fps}, Duration: {segment_duration_minutes} minutes")
    
    start_time = time.time()
    end_time = start_time + (segment_duration_minutes * 60)
    frames_captured = 0

    try:
        with mss.mss() as sct:
            monitor_combined = sct.monitors[0]
            while time.time() < end_time:
                now = datetime.now().time()
                if now >= datetime.strptime(recording_end_time, "%I%p").time():
                    logger.info("It's past 9:00 PM. Ending current recording segment early.")
                    break

                if stop_event and stop_event.is_set():
                    logger.info("Stop event triggered. Ending recording early.")
                    break

                screenshot = sct.grab(monitor_combined)
                img = Image.frombytes("RGB", screenshot.size, screenshot.rgb)
                frame = np.array(img)
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                frame = cv2.resize(frame, resolution)

                encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), compression_quality]
                _, buffer = cv2.imencode('.jpg', frame, encode_param)
                frame = cv2.imdecode(buffer, cv2.IMREAD_COLOR)

                out.write(frame)
                frames_captured += 1
                time.sleep(1 / fps)

    except KeyboardInterrupt:
        logger.warning("Recording interrupted by user")
        raise KeyboardInterrupt
    except Exception as e:
        logger.exception(f"Error during recording: {e}")
    finally:
        out.release()
        elapsed_time = time.time() - start_time
        file_size_mb = os.path.getsize(output_path) / (1024 * 1024)

        logger.info("Recording finished")
        logger.info(f"Elapsed time: {elapsed_time:.2f} seconds")
        logger.info(f"Frames captured: {frames_captured}")
        logger.info(f"Average FPS: {frames_captured / elapsed_time:.2f}")
        logger.info(f"File size: {file_size_mb:.2f} MB")
        logger.info(f"Video saved to: {output_path}")
        upload_to_google_drive_service(folder_id=FOLDER_ID,file_path=output_path)

def upload_and_clean_recordings():
    logger.info("Starting the process to upload and clean recordings.")
    try:
        with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
            for _ in executor.map(partial(upload_to_google_drive_service, FOLDER_ID), list(RECORDING_DIR.glob("*.mp4"))):
                pass
    finally:
        delete_old_drive_files(days_old=RETENTION_DAYS, folder_id=FOLDER_ID)
        logger.info(f"Old files on Google Drive deleted (older than {RETENTION_DAYS} days).")
        
        delete_old_recordings(days_old=RETENTION_DAYS)
        logger.info(f"Old local recordings deleted (older than {RETENTION_DAYS} days).")

def is_within_recording_hours(start_hour=9, end_hour=21):
    now = datetime.now().time()
    return now >= datetime.strptime(f"{start_hour}:00", "%H:%M").time() and \
           now < datetime.strptime(f"{end_hour}:00", "%H:%M").time()

def main():
    logger.info("Screen recorder started.")
    try:
        while True:
            if is_within_recording_hours():
                logger.info("Within allowed time. Starting a recording segment.")
                try:
                    screen_recorder_segment(RECORDING_DIR)
                except KeyboardInterrupt:
                    break
            else:
                logger.info("Outside recording hours. Sleeping until next check.")
                time.sleep(60)  # Check every minute
                continue

            # After each segment (1 hour), check time again before recording next
            if not is_within_recording_hours():
                logger.info("Recording hours ended. Exiting loop.")
                break

    except Exception as e:
        logger.exception("An error occurred during the recording loop.")

    finally:
        upload_and_clean_recordings()
        logger.info("Upload and cleanup complete.")
if __name__ == "__main__":
    main()