from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config import settings
from app.db.session import SessionLocal
from app.services.sync_service import sync_goodbarber_orders


def build_scheduler() -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        scheduled_goodbarber_sync,
        "interval",
        seconds=settings.goodbarber_sync_interval_seconds,
        id="goodbarber-sync",
        replace_existing=True,
    )
    return scheduler


async def scheduled_goodbarber_sync() -> None:
    db = SessionLocal()
    try:
        result = await sync_goodbarber_orders(db)
        if result["count"] or result["printed_count"]:
            print(
                f"[GoodBarber Sync] synced={result['count']} printed={result['printed_count']}"
            )
    except Exception as error:
        print(f"[GoodBarber Sync] automatic sync failed: {error}")
    finally:
        db.close()
