from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from threading import Thread, Event
import uvicorn
import time
from core import (
    screen_recorder_segment,
    upload_and_clean_recordings,
    logger,
    RECORDING_DIR,
    is_within_recording_hours
)

app = FastAPI(title="Screen Recorder Control")
recording_thread = None
stop_event = Event()
is_recording = False

# Mount static files directory
app.mount("/static", StaticFiles(directory="static"), name="static")

# Set up Jinja2 templates
templates = Jinja2Templates(directory="static/templates")

def record_loop():
    global is_recording
    is_recording = True
    logger.info("Recording thread started. Waiting for allowed hours (9 AM to 9 PM)...")
    try:
        while not stop_event.is_set():
            if is_within_recording_hours():
                logger.info("SUCCESS: Within allowed time. Starting a recording segment.")
                screen_recorder_segment(RECORDING_DIR, stop_event=stop_event)
            else:
                logger.info("⏳ Outside recording hours. Will check again in 60 seconds.")
                time.sleep(60)
                continue
            if not is_within_recording_hours():
                logger.info("🕘 Recording hours ended. Will stop until next allowed time.")
                break
            if stop_event.is_set():
                logger.info("STOP: Stop signal received. Exiting recording loop.")
                break
    except Exception as e:
        logger.exception("ERROR: An error occurred during the recording loop.")
    finally:
        is_recording = False
        upload_and_clean_recordings()
        logger.info("COMPLETE: Upload complete. Recording thread stopped.")

@app.on_event("startup")
def start_recording_on_startup():
    global recording_thread, stop_event
    if not is_recording:
        logger.info("Starting recording on FastAPI startup.")
        stop_event.clear()
        recording_thread = Thread(target=record_loop, daemon=True)
        recording_thread.start()

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(
        "index.html", 
        {"request": request, "is_recording": is_recording}
    )

@app.post("/start")
def start_recording():
    global recording_thread, stop_event

    if not is_within_recording_hours():
        return {"status": "Not a recording hour.","success": False}
    
    if is_recording:
        return {"status": "Already recording.", "success": True}
    
    stop_event.clear()
    recording_thread = Thread(target=record_loop, daemon=True)
    recording_thread.start()
    return {"status": "Recording started.", "success": True}

@app.post("/stop")
def stop_recording():
    global stop_event
    if not is_recording:
        return {"status": "Not currently recording.", "success": True}
    stop_event.set()
    return {"status": "Stopping recording...", "success": True}

@app.get("/status")
def status():
    current_time = time.strftime("%H:%M:%S")
    within_hours = is_within_recording_hours()
    return {
        "recording": is_recording if is_within_recording_hours() else False,
        "success": True,
        "time": current_time,
        "within_recording_hours": within_hours
    }

if __name__ == '__main__':
    uvicorn.run("app:app", host="0.0.0.0", port=8001)