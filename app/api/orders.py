import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.models import Order
from app.db.session import get_db
from app.schemas.orders import OrderListResponse, OrderRead, OrderResponse, UpdateStatusRequest
from app.services.order_mapper import normalize_goodbarber_order
from app.services.pdf_service import generate_order_pdf
from app.services.print_service import list_printers, print_order, print_test_page
from app.services.settings_service import get_selected_printer, set_selected_printer
from app.services.sync_service import upsert_order
from app.services.time_service import now_local_naive


router = APIRouter(prefix="/api/orders", tags=["orders"])
logger = logging.getLogger("orderbridge.api.orders")


def serialize_order(order: Order) -> OrderRead:
    return OrderRead.model_validate(order)


@router.get("", response_model=OrderListResponse)
def list_orders(status: str | None = None, db: Session = Depends(get_db)):
    logger.info("GET /api/orders status_filter=%s", status or "all")
    query = select(Order).options(selectinload(Order.items)).order_by(Order.created_at.desc())
    if status and status != "all":
        query = query.where(Order.status == status)
    orders = db.execute(query).scalars().unique().all()
    logger.info("Returning %s orders", len(orders))
    for order in orders:
        logger.info(
            "Order id=%s reference=%s status=%s created_at=%s updated_at=%s total=%s items=%s",
            order.id,
            order.reference,
            order.status,
            order.created_at,
            order.updated_at,
            order.total,
            len(order.items),
        )
    return {"orders": [serialize_order(order) for order in orders]}


@router.get("/printers")
def get_printers(db: Session = Depends(get_db)):
    payload = list_printers()
    payload["selected_printer"] = get_selected_printer(db)
    return payload


@router.post("/printers/select")
def select_printer(body: dict, db: Session = Depends(get_db)):
    printer_name = str(body.get("printer_name") or "").strip()
    if not printer_name:
        raise HTTPException(status_code=400, detail="printer_name is required")

    set_selected_printer(db, printer_name)
    db.commit()
    logger.info("Selected printer saved: %s", printer_name)
    return {"selected_printer": printer_name}


@router.post("/printers/test")
def test_printer(body: dict | None = None, db: Session = Depends(get_db)):
    printer_name = ""
    if body:
        printer_name = str(body.get("printer_name") or "").strip()
    if not printer_name:
        printer_name = get_selected_printer(db)

    job = print_test_page(printer_name or None)
    return {"ok": True, "job": job}


@router.get("/{order_id}", response_model=OrderResponse)
def get_order(order_id: str, db: Session = Depends(get_db)):
    logger.info("GET /api/orders/%s", order_id)
    order = db.execute(
        select(Order).options(selectinload(Order.items)).where(Order.id == order_id)
    ).scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return {"order": serialize_order(order)}


@router.get("/{order_id}/pdf")
def download_order_pdf(order_id: str, db: Session = Depends(get_db)):
    logger.info("GET /api/orders/%s/pdf", order_id)
    order = db.execute(
        select(Order).options(selectinload(Order.items)).where(Order.id == order_id)
    ).scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    pdf_path = generate_order_pdf(order)
    return FileResponse(
        path=pdf_path,
        media_type="application/pdf",
        filename=pdf_path.name,
    )


@router.post("/webhook/goodbarber")
def receive_goodbarber_webhook(payload: dict, db: Session = Depends(get_db)):
    logger.info("POST /api/orders/webhook/goodbarber payload_keys=%s", list(payload.keys()))
    normalized = normalize_goodbarber_order(payload)
    logger.info(
        "Webhook normalized order id=%s reference=%s status=%s created_at=%s total=%s items=%s",
        normalized["id"],
        normalized["reference"],
        normalized["status"],
        normalized["created_at"],
        normalized["total"],
        len(normalized["items"]),
    )
    order, _ = upsert_order(db, normalized)
    job = None
    db.commit()
    db.refresh(order)

    if order.status == "new":
        try:
            logger.info("Printing webhook order reference=%s", order.reference)
            job = print_order(order)
            order.status = "printed"
            order.updated_at = now_local_naive()
            db.commit()
            db.refresh(order)
        except Exception as error:
            raise HTTPException(status_code=500, detail=f"Print failed: {error}") from error

    return {"accepted": True, "order": serialize_order(order), "job": job}


@router.post("/{order_id}/print")
def print_existing_order(order_id: str, db: Session = Depends(get_db)):
    logger.info("POST /api/orders/%s/print", order_id)
    order = db.execute(
        select(Order).options(selectinload(Order.items)).where(Order.id == order_id)
    ).scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    try:
        logger.info("Printing existing order reference=%s status=%s", order.reference, order.status)
        job = print_order(order)
        order.status = "printed"
        order.updated_at = now_local_naive()
        db.commit()
        db.refresh(order)
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"Print failed: {error}") from error

    return {"order": serialize_order(order), "job": job}


@router.patch("/{order_id}/status", response_model=OrderResponse)
def update_order_status(order_id: str, body: UpdateStatusRequest, db: Session = Depends(get_db)):
    logger.info("PATCH /api/orders/%s/status -> %s", order_id, body.status)
    if body.status not in {"new", "printed", "done", "cancelled"}:
        raise HTTPException(status_code=400, detail="Invalid order status")

    order = db.execute(select(Order).where(Order.id == order_id)).scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    order.status = body.status
    order.updated_at = now_local_naive()
    db.commit()
    db.refresh(order)
    return {"order": serialize_order(order)}
