@echo off
setlocal enabledelayedexpansion
title Bijou Local Dev Launcher

echo ======================================================================
echo                 BIJOU CAUSAL ENGINE - DEV LAUNCHER
echo ======================================================================

:: 1. Locate Python Interpreter
set "PYTHON_EXE="
if exist "%USERPROFILE%\.auraseed\apps\bijou\Scripts\python.exe" (
    set "PYTHON_EXE=%USERPROFILE%\.auraseed\apps\bijou\Scripts\python.exe"
) else if exist "C:\dev\auraseed\.bootstrapped_python\python.exe" (
    set "PYTHON_EXE=C:\dev\auraseed\.bootstrapped_python\python.exe"
) else (
    for /f "tokens=*" %%i in ('where python 2^>nul') do (
        if not defined PYTHON_EXE set "PYTHON_EXE=%%i"
    )
)

if not defined PYTHON_EXE (
    echo [Bijou Dev] Error: Could not locate a valid Python interpreter.
    pause
    exit /b 1
)

echo [Bijou Dev] Using Python: %PYTHON_EXE%

:: 2. Ensure uvicorn is installed in this Python environment
"%PYTHON_EXE%" -c "import uvicorn" >nul 2>&1
if errorlevel 1 (
    echo [Bijou Dev] uvicorn not found in %PYTHON_EXE%. Installing uvicorn...
    "%PYTHON_EXE%" -m pip install uvicorn
)

:: 3. Set PYTHONPATH to local dev source trees for immediate live reloading
set "BIJOU_ROOT=%~dp0"
if "%BIJOU_ROOT:~-1%"=="\" set "BIJOU_ROOT=%BIJOU_ROOT:~0,-1%"
set "PYTHONPATH=%BIJOU_ROOT%\src;%BIJOU_ROOT%\projects\bijou-pysdk\src;%BIJOU_ROOT%\projects\bijou-doc-ingest\src;%PYTHONPATH%"

:: 4. Configure storage pointing to %TEMP%\bijou_test
set "TEST_DIR=%TEMP%\bijou_test"
if not exist "%TEST_DIR%" mkdir "%TEST_DIR%"
set "DB_FILE=%TEST_DIR%\bijou_graph.db"
set "DUCK_FILE=%TEST_DIR%\bijou_telemetry.duckdb"

set "BIJOU_DB_URI=sqlite:///%TEST_DIR%\bijou_graph.db"
set "BIJOU_DUCKDB_PATH=%DUCK_FILE%"
set "BIJOU_BIND_HOST=0.0.0.0"
set "BIJOU_BIND_PORT=8000"

:: 5. Seed test data once per system session/restart
"%PYTHON_EXE%" "%BIJOU_ROOT%\scripts\dev_seed.py"
if errorlevel 1 (
    echo [Bijou Dev] Warning: Seeder exited with error code %ERRORLEVEL%.
)

:: 6. Launch uvicorn with live code & static assets auto-reload
echo.
echo ======================================================================
echo  Starting Uvicorn live development server on http://localhost:8000
echo  Watching for changes in: %BIJOU_ROOT%\src
echo  Press Ctrl+C to terminate.
echo ======================================================================
echo.

cd /d "%BIJOU_ROOT%"
"%PYTHON_EXE%" -m uvicorn bijou.api.app:app --host 0.0.0.0 --port 8000 --reload --reload-dir "%BIJOU_ROOT%\src"

pause
