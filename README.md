# OrderBridge Python

Backend puro en Python para recibir pedidos de GoodBarber, guardarlos localmente, sincronizarlos cada minuto y mandarlos a imprimir en Windows como PDF.

## Stack

- `FastAPI` para la API
- `APScheduler` para la sincronizacion automatica
- `SQLAlchemy + SQLite` para almacenamiento local
- `ReportLab` para generar el PDF del pedido
- `pywin32` para detectar impresoras de Windows y disparar la impresion
- impresion nativa en Windows renderizando el PDF a imagen desde Python

## Flujo

1. GoodBarber envia un webhook o el scheduler consulta la API cada 60 segundos.
2. El backend guarda la orden en SQLite.
3. Si la orden sigue en estado local `new`, genera un PDF.
4. El backend manda ese PDF a la impresora configurada en Windows.
5. Si el envio se acepta, cambia la orden a `printed`.

## Arranque rapido

```bat
run.bat
```

Tambien puedes hacerlo manual:

```bat
py -3 -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

## Endpoints

- `GET /api/health`
- `GET /api/orders`
- `GET /api/orders/{order_id}`
- `GET /api/orders/printers`
- `POST /api/orders/{order_id}/print`
- `PATCH /api/orders/{order_id}/status`
- `POST /api/orders/webhook/goodbarber`
- `POST /api/sync/goodbarber`

## Variables

Usa `.env.example` como base. Si `PRINTER_NAME` queda vacio, se intenta usar la impresora predeterminada de Windows.

## Nota de impresion

La impresion genera el PDF, lo renderiza en Python con `PyMuPDF`, lo ajusta con `Pillow` y lo envia a la impresora seleccionada con `pywin32`.

Si `PRINTER_NAME` queda vacio, se intenta usar la impresora predeterminada de Windows.
