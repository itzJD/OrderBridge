@echo off
setlocal

set "PYTHON_EXE=%~dp0.venv\Scripts\python.exe"

cd /d "%~dp0"

if not exist "%PYTHON_EXE%" (
  py -3 -m venv .venv
)

"%PYTHON_EXE%" windows_service.py stop
"%PYTHON_EXE%" windows_service.py remove
