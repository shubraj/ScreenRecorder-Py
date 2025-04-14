@echo off
REM Setup script to run FastAPI app at system startup (minimized)

set "SCRIPT_DIR=%~dp0"
set "PY_FILE=%SCRIPT_DIR%app.py"
set "VBS_FILE=%SCRIPT_DIR%run_minimized.vbs"
set "TASK_NAME=FastAPIRecorderOnStartup"

REM Locate Python
for /f "delims=" %%i in ('where python 2^>nul') do set "PYTHON_PATH=%%i"
if not defined PYTHON_PATH (
    for /f "delims=" %%i in ('where python3 2^>nul') do set "PYTHON_PATH=%%i"
)
if not defined PYTHON_PATH (
    echo ❌ Python not found. Please install Python.
    pause
    exit /b
)

REM Create VBScript to launch Python minimized
> "%VBS_FILE%" echo Set WshShell = CreateObject("WScript.Shell")
>> "%VBS_FILE%" echo WshShell.Run Chr(34^) ^& "%PYTHON_PATH%" ^& Chr(34^) ^& " " ^& Chr(34^) ^& "%PY_FILE%" ^& Chr(34^), 7, False

REM Create Task Scheduler job
schtasks /create /f ^
    /tn "%TASK_NAME%" ^
    /sc onstart ^
    /rl HIGHEST ^
    /tr "\"wscript.exe\" \"%VBS_FILE%\"" ^
    /ru SYSTEM ^
    /np ^
    /it

echo ✅ Task '%TASK_NAME%' created to run minimized on system startup!
pause
