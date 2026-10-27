@echo off
cd /d "%~dp0"
if not exist "services\api\.venv\Scripts\python.exe" (
  echo Project dependencies are missing. See DEVELOPMENT.md.
  pause
  exit /b 1
)
"services\api\.venv\Scripts\python.exe" "scripts\dev.py"
pause
