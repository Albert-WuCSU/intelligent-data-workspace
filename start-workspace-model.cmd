@echo off
cd /d "%~dp0"
"services\api\.venv\Scripts\python.exe" "scripts\dev.py" --model-key
pause
