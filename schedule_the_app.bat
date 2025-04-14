@echo off
REM Setup script to run FastAPI app at system startup

REM Set path to your main script
set SCRIPT_PATH=%~dp0app.py
set TASK_NAME=FastAPIRecorderOnStartup

REM Check if Python is available
where python >nul 2>nul
if %errorlevel% == 0 (
    set PYTHON_PATH=python
) else (
    where python3 >nul 2>nul
    if %errorlevel% == 0 (
        set PYTHON_PATH=python3
    ) else (
        echo Python not found. Please install Python.
        pause
        exit /b
    )
)

REM Create a task in Task Scheduler to run at system startup
schtasks /create /f /sc onstart /tn "%TASK_NAME%" /tr "\"%PYTHON_PATH%\" \"%SCRIPT_PATH%\"" /rl HIGHEST

echo ✅ Task Scheduler job '%TASK_NAME%' created to run on system startup!
pause
