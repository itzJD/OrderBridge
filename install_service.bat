@echo off
setlocal

set "SERVICE_NAME=OrderBridge"
set "PYTHON_EXE=%~dp0.venv\Scripts\python.exe"
set "SERVICE_EXE=%~dp0.venv\pythonservice.exe"
set "PYTHON_CLASS=%~dp0windows_service.OrderBridgeService"

cd /d "%~dp0"

if not exist "%PYTHON_EXE%" (
  py -3 -m venv .venv
)

"%PYTHON_EXE%" -m pip install --upgrade pip
"%PYTHON_EXE%" -m pip install -r requirements.txt

for /f "usebackq delims=" %%i in (`"%PYTHON_EXE%" -c "import sys; print(sys.base_prefix)"`) do set "PYTHON_HOME=%%i"
for /f "usebackq delims=" %%i in (`"%PYTHON_EXE%" -c "import sys; print(f'python{sys.version_info.major}{sys.version_info.minor}.dll')"` ) do set "PYTHON_DLL=%%i"
for /f "usebackq delims=" %%i in (`"%PYTHON_EXE%" -c "import sys; print(f'pythoncom{sys.version_info.major}{sys.version_info.minor}.dll')"` ) do set "PYTHONCOM_DLL=%%i"
for /f "usebackq delims=" %%i in (`"%PYTHON_EXE%" -c "import sys; print(f'pywintypes{sys.version_info.major}{sys.version_info.minor}.dll')"` ) do set "PYWINTYPES_DLL=%%i"

copy /Y "%PYTHON_HOME%\%PYTHON_DLL%" "%~dp0.venv\%PYTHON_DLL%" >nul
copy /Y "%~dp0.venv\Lib\site-packages\pywin32_system32\%PYTHONCOM_DLL%" "%~dp0.venv\%PYTHONCOM_DLL%" >nul
copy /Y "%~dp0.venv\Lib\site-packages\pywin32_system32\%PYWINTYPES_DLL%" "%~dp0.venv\%PYWINTYPES_DLL%" >nul

sc.exe query "%SERVICE_NAME%" >nul 2>&1
if %errorlevel%==0 (
  sc.exe stop "%SERVICE_NAME%" >nul 2>&1
  sc.exe delete "%SERVICE_NAME%" >nul 2>&1
  timeout /t 2 /nobreak >nul
)

"%PYTHON_EXE%" windows_service.py --startup=auto install
reg add "HKLM\SYSTEM\CurrentControlSet\Services\%SERVICE_NAME%\PythonClass" /ve /t REG_SZ /d "%PYTHON_CLASS%" /f
reg add "HKLM\SYSTEM\CurrentControlSet\Services\%SERVICE_NAME%" /v ImagePath /t REG_EXPAND_SZ /d "\"%SERVICE_EXE%\"" /f
sc.exe description "%SERVICE_NAME%" "Servicio local para sincronizar ordenes, generar PDF e imprimir pedidos."
sc.exe failure "%SERVICE_NAME%" reset= 86400 actions= restart/5000/restart/5000/restart/5000
sc.exe failureflag "%SERVICE_NAME%" 1
"%PYTHON_EXE%" windows_service.py start
