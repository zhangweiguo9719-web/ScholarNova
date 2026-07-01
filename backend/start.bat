@echo off
cd /d "%~dp0"
D:\Python\python312\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --log-level debug
pause
