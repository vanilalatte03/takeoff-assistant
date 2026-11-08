@echo off
setlocal
if not exist "%~dp0apps\api\.venv311\Scripts\pythonw.exe" goto missing
"%~dp0apps\api\.venv311\Scripts\python.exe" -c "import ctypes" >nul 2>&1
if errorlevel 1 goto missing
start "" "%~dp0apps\api\.venv311\Scripts\pythonw.exe" "%~dp0scripts\desktop_launcher.py"
exit /b
:missing
powershell.exe -NoProfile -EncodedCommand QQBkAGQALQBUAHkAcABlACAALQBBAHMAcwBlAG0AYgBsAHkATgBhAG0AZQAgAFAAcgBlAHMAZQBuAHQAYQB0AGkAbwBuAEYAcgBhAG0AZQB3AG8AcgBrADsAIABbAFMAeQBzAHQAZQBtAC4AVwBpAG4AZABvAHcAcwAuAE0AZQBzAHMAYQBnAGUAQgBvAHgAXQA6ADoAUwBoAG8AdwAoACcAUAB5AHQAaABvAG4AIAAzAC4AMQAxACAAAKzBwFjWvax0xyAAxsW1wsiy5LIuACAAUgBFAEEARABNAEUAWMcgAFzNCM0gAADJRL4gAAjIKMx8uSAARMbMuFzVIACktCAA5LLcwiAA5MKJ1VjVOMGUxi4AJwAsACcAVABhAGsAZQBvAGYAZgAgAEEAcwBzAGkAcwB0AGEAbgB0ACAA5MKJ1SAAAMlEvicAKQA=
exit /b 1
