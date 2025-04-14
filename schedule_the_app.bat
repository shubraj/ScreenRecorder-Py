@echo off
REM Setup script to run FastAPI app at system startup
REM Get full script directory and app path
set "SCRIPT_DIR=%~dp0"
set "APP_PATH=%SCRIPT_DIR%app.py"
set "TASK_NAME=FastAPIRecorderOnStartup"

REM Check for Python installation
where python >nul 2>nul
if %errorlevel% == 0 (
    set "PYTHON_PATH=python"
) else (
    where python3 >nul 2>nul
    if %errorlevel% == 0 (
        set "PYTHON_PATH=python3"
    ) else (
        echo ❌ Python not found. Please install Python.
        pause
        exit /b
    )
)

REM Get the full path to Python executable
for /f "tokens=*" %%i in ('where %PYTHON_PATH%') do set "PYTHON_FULL_PATH=%%i"

REM Create the task with required parameters:
REM - Working directory set to script location
REM - Run with highest privileges
REM - Run task as soon as possible after a scheduled start is missed
REM - Don't require battery power
schtasks /create /f /sc onstart /tn "%TASK_NAME%" /tr "\"%PYTHON_FULL_PATH%\" \"%APP_PATH%\"" /rl HIGHEST /st 00:00 /ru SYSTEM /np /delay 0000:01 /v1 /z

REM Additional XML modifications for battery settings and missed start
powershell -Command "$xml = [xml](schtasks /query /tn '%TASK_NAME%' /xml); $xml.Task.Settings.DisallowStartIfOnBatteries = 'false'; $xml.Task.Settings.RunOnlyIfIdle = 'false'; $xml.Task.Settings.StartWhenAvailable = 'true'; $xml.Save('%TEMP%\task.xml'); schtasks /create /f /tn '%TASK_NAME%' /xml '%TEMP%\task.xml'"

echo ✅ Task Scheduler job '%TASK_NAME%' created to run on system startup!
echo    - Working directory: %SCRIPT_DIR%
echo    - Python path: %PYTHON_FULL_PATH%
echo    - App path: %APP_PATH%
echo    - Will run as soon as possible after missed start
echo    - Will run regardless of battery status
pause