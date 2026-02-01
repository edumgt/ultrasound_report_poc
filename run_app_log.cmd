@echo off
python app.py > run_console.log 2>&1
echo ExitCode=%ERRORLEVEL%
type run_console.log
pause
