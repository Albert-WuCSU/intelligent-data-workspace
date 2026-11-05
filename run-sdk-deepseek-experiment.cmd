@echo off
cd /d "%~dp0"
"services\api\.venv\Scripts\python.exe" "scripts\run_sdk_deepseek_experiment.py" %*
pause
