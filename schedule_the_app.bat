@echo on
REM Setup script to run FastAPI app at system startup

REM Get full script directory and app path
set "SCRIPT_DIR=%~dp0"
set "SCRIPT_PATH=%SCRIPT_DIR%app.py"
set "TASK_NAME=FastAPIRecorderOnStartup"

echo SCRIPT_DIR=%SCRIPT_DIR%
echo SCRIPT_PATH=%SCRIPT_PATH%
echo TASK_NAME=%TASK_NAME%

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

echo PYTHON_PATH=%PYTHON_PATH%

REM Create the task with absolute app.py path
schtasks /create /f /sc onstart /tn "%TASK_NAME%" /tr "\"%PYTHON_PATH%\" \"%SCRIPT_PATH%\"" /rl HIGHEST

echo ✅ Task Scheduler job '%TASK_NAME%' created to run on system startup!
pause
