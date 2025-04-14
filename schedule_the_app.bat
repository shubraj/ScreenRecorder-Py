@echo off
REM Setup script to run FastAPI app at system startup

REM Get full script directory and app path
set "SCRIPT_DIR=%~dp0"
set "SCRIPT_PATH=%SCRIPT_DIR%app.py"
set "TASK_NAME=FastAPIRecorderOnStartup"

REM Check for Python installation and get full path
for /f "usebackq delims=" %%i in (`where python`) do (
    set "PYTHON_PATH=%%i"
    goto :found
)

for /f "usebackq delims=" %%i in (`where python3`) do (
    set "PYTHON_PATH=%%i"
    goto :found
)

echo ❌ Python not found. Please install Python.
pause
exit /b

:found

REM Create the task with absolute app.py path
schtasks /create /f /sc onstart /tn "%TASK_NAME%" /tr "\"%PYTHON_PATH%\" \"%SCRIPT_PATH%\"" /rl HIGHEST

echo ✅ Task Scheduler job '%TASK_NAME%' created to run on system startup!
pause
