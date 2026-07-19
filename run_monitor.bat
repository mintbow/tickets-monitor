@echo off
rem Один прогон монитора авиабилетов с записью лога.
cd /d "%~dp0"
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
"C:\Users\ssaas\AppData\Local\Programs\Python\Python311\python.exe" main.py --once >> monitor.log 2>&1
