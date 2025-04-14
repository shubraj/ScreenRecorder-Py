@echo off
REM Setup script to run FastAPI app at system startup

REM Get full script directory and app path
set "SCRIPT_DIR=%~dp0"
set "SCRIPT_PATH=%SCRIPT_DIR%app.py"
set "TASK_NAME=FastAPIRecorderOnStartup"

REM Find Python installation
for /f "delims=" %%i in ('where python 2^>nul') do set "PYTHON_PATH=%%i"
if not defined PYTHON_PATH (
    for /f "delims=" %%i in ('where python3 2^>nul') do set "PYTHON_PATH=%%i"
)
if not defined PYTHON_PATH (
    echo ❌ Python not found. Please install Python.
    pause
    exit /b
)

REM Create task to run on startup
schtasks /create /f ^
    /tn "%TASK_NAME%" ^
    /sc onstart ^
    /rl HIGHEST ^
    /tr "\"%PYTHON_PATH%\" \"%SCRIPT_PATH%\"" ^
    /ru SYSTEM ^
    /d MON,TUE,WED,THU,FRI,SAT,SUN ^
    /it

REM Set working directory via registry (Task Scheduler doesn't allow directly setting working dir via schtasks)
REG ADD "HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Schedule\TaskCache\Tree\%TASK_NAME%" /v WorkingDirectory /t REG_SZ /d "%SCRIPT_DIR%" /f >nul 2>&1

echo ✅ Task '%TASK_NAME%' created to run app.py at startup from '%SCRIPT_DIR%'
pause
