@echo off
setlocal

REM Set script and task names
set "SCRIPT_DIR=%~dp0"
set "SCRIPT_PATH=%SCRIPT_DIR%app.py"

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
echo ✅ Found Python at: %PYTHON_PATH%

REM Run the script in a minimized window
start /min "" "%PYTHON_PATH%" "%SCRIPT_PATH%"

endlocal
exit /b
