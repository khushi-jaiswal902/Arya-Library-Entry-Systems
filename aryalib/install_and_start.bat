@echo off
setlocal
cd /d "%~dp0"

echo ==========================================
echo Arya Library Local Setup and Start
echo ==========================================
echo.

where py >nul 2>&1
if errorlevel 1 (
  echo Python launcher ^(py^) was not found.
  echo Install Python 3 first, then run this file again.
  echo.
  pause
  exit /b 1
)

echo Installing/updating Python dependencies...
py -3 -m pip install --upgrade pip
if errorlevel 1 (
  echo Failed to upgrade pip.
  echo.
  pause
  exit /b 1
)

py -3 -m pip install -r requirements.txt
if errorlevel 1 (
  echo Failed to install required Python packages.
  echo.
  pause
  exit /b 1
)

echo.
echo Python packages installed successfully.
echo.
echo Note:
echo If you want to use the standalone desktop scanner,
echo Windows may still need the ZBar runtime for pyzbar.
echo The normal dashboard and browser workflow do not depend on that.
echo.

set "LIBRARY_AUTO_OPEN_BROWSER=1"
echo Starting Arya Library dashboard...
start "" cmd /c "set LIBRARY_AUTO_OPEN_BROWSER=1 && cd /d ""%~dp0"" && py -3 web_dashboard.py"

echo.
echo Setup complete. The browser should open automatically.
echo If it does not, open http://127.0.0.1:8000 manually.
echo.
pause
