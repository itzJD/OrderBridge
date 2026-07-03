from contextlib import asynccontextmanager
import asyncio
from pathlib import Path

import logging

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.orders import router as orders_router
from app.api.sync import router as sync_router
from app.config import settings
from app.db.session import Base, engine
from app.logging_config import configure_logging
from app.services.scheduler import build_scheduler, scheduled_goodbarber_sync


logger = logging.getLogger("orderbridge")


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    Base.metadata.create_all(bind=engine)
    logger.info("Database schema ready")
    scheduler = None

    if settings.goodbarber_sync_enabled:
        scheduler = build_scheduler()
        scheduler.start()
        asyncio.create_task(scheduled_goodbarber_sync())
        logger.info(
            "GoodBarber sync enabled: polling every %s seconds; initial sync queued",
            settings.goodbarber_sync_interval_seconds,
        )

    yield

    if scheduler:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.include_router(orders_router)
app.include_router(sync_router)

frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
app.mount("/static", StaticFiles(directory=frontend_dir), name="static")


@app.middleware("http")
async def disable_cache_for_frontend(request, call_next):
    response = await call_next(request)
    if request.url.path == "/" or request.url.path.startswith("/static/"):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response


@app.get("/api/health")
async def health():
    return {"ok": True, "service": settings.app_name}


@app.get("/", include_in_schema=False)
async def frontend_index():
    return FileResponse(frontend_dir / "index.html")
