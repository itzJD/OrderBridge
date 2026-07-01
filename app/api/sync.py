from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.sync_service import sync_goodbarber_orders


router = APIRouter(prefix="/api/sync", tags=["sync"])


@router.post("/goodbarber")
async def sync_goodbarber(db: Session = Depends(get_db)):
    return await sync_goodbarber_orders(db)
