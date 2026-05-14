@echo off
cd /d "%~dp0"
start "" powershell -NoExit -Command "Set-Location '%~dp0'; & 'C:\Users\A\AppData\Local\Programs\Python\Python313\python.exe' .\web_dashboard.py"
timeout /t 2 /nobreak >nul
start "" "http://127.0.0.1:8000/camera"
