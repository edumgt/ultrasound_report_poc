@echo off
set SAFE_MODE=1
python app.py
echo ExitCode=%ERRORLEVEL%
pause
