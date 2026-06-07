@echo off
setlocal

REM Resolve script directory and switch there
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

echo Checking Python...
where python >nul 2>&1
if errorlevel 1 (
  echo Python was not found. Install Python 3.x and ensure it is on your PATH.
  pause
  exit /b 1
)

echo Checking pip...
python -m pip --version >nul 2>&1
if errorlevel 1 (
  echo pip was not found. Ensure Python and pip are installed.
  pause
  exit /b 1
)

echo Installing Python requirements if needed...
python -m pip install -r requirements.txt
if errorlevel 1 (
  echo Failed to install Python requirements.
  pause
  exit /b 1
)

echo Checking Node.js...
where node >nul 2>&1
if errorlevel 1 (
  echo Node.js was not found. Install Node.js and ensure it is on your PATH.
  pause
  exit /b 1
)

echo Checking npm...
where npm >nul 2>&1
if errorlevel 1 (
  echo npm was not found. Install Node.js/npm and ensure it is on your PATH.
  pause
  exit /b 1
)


if not exist "%SCRIPT_DIR%frontend\node_modules" (
  echo Installing frontend dependencies...
  pushd "%SCRIPT_DIR%frontend"
  npm install
  if errorlevel 1 (
    echo npm install failed.
    popd
    pause
    exit /b 1
  )
  popd
)

echo Starting backend and frontend...
start "Backend" cmd /k "cd /d "%SCRIPT_DIR%" && python api.py"
start "Frontend" cmd /k "cd /d "%SCRIPT_DIR%frontend" && npm start"

echo Launched backend and frontend.
pause
