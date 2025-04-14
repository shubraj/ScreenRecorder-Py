@echo off
REM Setup script to run FastAPI app at system startup

REM Get full path to app.py
set SCRIPT_DIR=%~dp0
set SCRIPT_PATH=%SCRIPT_DIR%app.py
set TASK_NAME=FastAPIRecorderOnStartup

REM Check for Python installation
where python >nul 2>nul
if %errorlevel% == 0 (
    set PYTHON_PATH=python
) else (
    where python3 >nul 2>nul
    if %errorlevel% == 0 (
        set PYTHON_PATH=python3
    ) else (
        echo ❌ Python not found. Please install Python.
        pause
        exit /b
    )
)

REM Create Task Scheduler job
schtasks /create /f /sc onstart /tn "%TASK_NAME%" /tr "cmd /c \"cd /d %SCRIPT_DIR% && %PYTHON_PATH% app.py\"" /rl HIGHEST

echo ✅ Task Scheduler job '%TASK_NAME%' created to run on system startup!
pause
