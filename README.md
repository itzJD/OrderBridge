# OrderBridge Python

Backend en Python para recibir pedidos de GoodBarber, guardarlos localmente, sincronizarlos en segundo plano y mandarlos a imprimir en Windows.

## Stack

- `FastAPI` para la API
- `APScheduler` para la sincronizacion automatica
- `SQLAlchemy + SQLite` para almacenamiento local
- `ReportLab` para generar el PDF del pedido
- `pywin32` para servicio local de Windows e impresion
- `Pillow + pypdfium2` para renderizar el PDF antes de imprimir

## Flujo

1. GoodBarber envia un webhook o el scheduler consulta la API.
2. El backend guarda la orden en SQLite.
3. Si la orden sigue en estado local `new`, genera un PDF.
4. El backend manda ese PDF a la impresora configurada en Windows.
5. Si la impresion se acepta, cambia la orden a `printed`.

## Variables

Usa `.env.example` como base.

Variables clave:

- `GOODBARBER_APP_ID`
- `GOODBARBER_API_KEY`
- `API_HOST`
- `API_PORT`
- `PRINTER_NAME`
- `GOODBARBER_SYNC_ENABLED`
- `GOODBARBER_SYNC_INTERVAL_SECONDS`

Si `PRINTER_NAME` queda vacio, se intenta usar la impresora predeterminada de Windows.

## Arranque manual

Para ejecutar la API sin instalar servicio:

```bat
run.bat
```

O manualmente:

```bat
py -3 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
copy .env.example .env
.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Health check:

```powershell
Invoke-WebRequest http://127.0.0.1:8000/api/health -UseBasicParsing
```

## Servicio de Windows

### Requisitos

- Windows
- PowerShell o CMD abiertos como Administrador
- Python instalado con `py -3`
- Acceso local para crear el entorno virtual y el servicio

### Instalacion recomendada

1. Abrir PowerShell como Administrador.
2. Entrar al proyecto:

```powershell
cd D:\orders\python-orderbridge
```

3. Instalar el servicio:

```powershell
.\install_service.bat
```

4. Verificar el estado:

```powershell
sc.exe query OrderBridge
```

5. Verificar la API:

```powershell
Invoke-WebRequest http://127.0.0.1:8000/api/health -UseBasicParsing
```

Si todo esta bien, el servicio queda:

- registrado como `OrderBridge`
- en arranque automatico
- con reinicio automatico si falla

### Que hace `install_service.bat`

El instalador hace esto:

1. Entra al directorio actual del proyecto.
2. Crea `.venv` si no existe.
3. Instala dependencias.
4. Detecta automaticamente la version de Python usada por el `venv`.
5. Copia al root de `.venv` los binarios que `pythonservice.exe` necesita:

- `pythonXY.dll`
- `pythoncomXY.dll`
- `pywintypesXY.dll`

6. Borra una instalacion vieja del servicio si ya existia.
7. Registra el servicio con `pythonservice.exe`.
8. Fuerza los valores correctos de:

- `ImagePath`
- `PythonClass`

9. Configura descripcion, autostart y restart-on-failure.
10. Arranca el servicio.

### Desinstalacion

```powershell
.\uninstall_service.bat
```

O manualmente:

```powershell
sc.exe stop OrderBridge
sc.exe delete OrderBridge
```

## Operacion diaria

Ver estado:

```powershell
sc.exe query OrderBridge
```

Arrancar:

```powershell
sc.exe start OrderBridge
```

Detener:

```powershell
sc.exe stop OrderBridge
```

Ver API:

```powershell
Invoke-WebRequest http://127.0.0.1:8000/api/health -UseBasicParsing
```

## Logs utiles

Los logs del servicio quedan en `logs/`:

- `logs/service-boot.log`
- `logs/service-error.log`
- `logs/uvicorn.out.log`
- `logs/uvicorn.err.log`

Tambien conviene revisar el Visor de eventos de Windows:

- `Application`
- `System`
- proveedor `Python Service`
- proveedor `OrderBridge`

## Problemas reales que aparecieron y como quedaron resueltos

### 1. PowerShell no ejecuta `.bat` del directorio actual

Sintoma:

```powershell
install_service.bat : The term 'install_service.bat' is not recognized...
```

Solucion:

```powershell
.\install_service.bat
```

### 2. `pywin32` no aceptaba `install --startup auto`

Sintoma:

- solo imprimia el `Usage`
- no instalaba el servicio

Solucion aplicada:

- usar `--startup=auto install`

### 3. El servicio quedaba apuntando a una ruta vieja

Sintoma:

- `sc.exe qc OrderBridge` mostraba otro workspace en `BINARY_PATH_NAME`

Causa:

- habia una instalacion vieja en el SCM

Solucion aplicada:

- el instalador ahora elimina el servicio previo
- luego fuerza `ImagePath` al `pythonservice.exe` del proyecto actual

### 4. `PythonClass` quedaba mal registrado

Sintoma:

- `Python Service` reportaba `ModuleNotFoundError: No module named 'windows_service'`
- o aparecia un `PicklingError` al instalar

Causa:

- `pywin32` mezcla distinto comportamiento cuando el servicio se registra desde `__main__`

Solucion aplicada:

- el instalador fuerza `PythonClass` a la ruta correcta del script actual:
  `D:\orders\python-orderbridge\windows_service.OrderBridgeService`

### 5. `pythonservice.exe` no arrancaba por DLL faltantes

Sintoma:

- error de sistema indicando que faltaba `python314.dll`
- Windows solo mostraba `1053`

Causa:

- `pythonservice.exe` necesita los DLL del runtime y de `pywin32` en el root del `venv`

Solucion aplicada:

- `install_service.bat` detecta la version de Python
- copia `pythonXY.dll`, `pythoncomXY.dll` y `pywintypesXY.dll` al root de `.venv`

### 6. El servicio arrancaba y se apagaba enseguida

Sintoma:

- `START_PENDING`
- luego `STOPPED`
- log `OrderBridge uvicorn exited unexpectedly with code 2`

Causa:

- el wrapper estaba lanzando Uvicorn con `sys.executable`
- dentro del servicio eso era `pythonservice.exe`, no `python.exe`

Solucion aplicada:

- `windows_service.py` ahora lanza Uvicorn con:
  `.venv\Scripts\python.exe`

### 7. El arranque podia tardar demasiado

Sintoma:

- `1053 The service did not respond...`

Causa:

- el sync inicial bloqueaba el startup de FastAPI

Solucion aplicada:

- el primer sync se encola en segundo plano con `asyncio.create_task(...)`
- el servicio puede marcar `RUNNING` antes

## Estructura relevante

- `app/main.py`: arranque de FastAPI y scheduler
- `windows_service.py`: wrapper del servicio de Windows
- `install_service.bat`: instalacion y autoreparacion del servicio
- `uninstall_service.bat`: desinstalacion del servicio

## Endpoints

- `GET /api/health`
- `GET /api/orders`
- `GET /api/orders/{order_id}`
- `GET /api/orders/printers`
- `POST /api/orders/{order_id}/print`
- `PATCH /api/orders/{order_id}/status`
- `POST /api/orders/webhook/goodbarber`
- `POST /api/sync/goodbarber`
