import asyncio
from datetime import datetime
import logging

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.config import settings
from app.db.models import Order, OrderItem
from app.services.goodbarber import fetch_goodbarber_orders
from app.services.order_mapper import normalize_goodbarber_order
from app.services.print_service import print_order


_sync_lock = asyncio.Lock()
logger = logging.getLogger("orderbridge.sync")


async def sync_goodbarber_orders(db: Session, auto_print: bool | None = None) -> dict:
    auto_print_enabled = settings.auto_print_new_orders if auto_print is None else auto_print

    async with _sync_lock:
        logger.info("Starting GoodBarber sync (auto_print=%s)", auto_print_enabled)
        remote_orders = await fetch_goodbarber_orders()
        logger.info("Fetched %s remote orders", len(remote_orders))
        normalized = [normalize_goodbarber_order(payload) for payload in remote_orders]
        response_orders = []
        printed_count = 0

        for payload in normalized:
            logger.info(
                "Processing order id=%s reference=%s status=%s created_at=%s total=%s items=%s",
                payload["id"],
                payload["reference"],
                payload["status"],
                payload["created_at"],
                payload["total"],
                len(payload["items"]),
            )
            order, was_created = upsert_order(db, payload)
            logger.info(
                "Upserted order id=%s created=%s persisted_status=%s updated_at=%s",
                order.id,
                was_created,
                order.status,
                order.updated_at,
            )
            if auto_print_enabled and should_auto_print(order, was_created):
                try:
                    logger.info("Auto-printing order reference=%s", order.reference)
                    print_order(order)
                    order.status = "printed"
                    order.updated_at = datetime.utcnow()
                    printed_count += 1
                    logger.info("Auto-print OK reference=%s new_status=%s", order.reference, order.status)
                except Exception as error:
                    logger.exception("Sync print failed for %s: %s", order.reference, error)
            response_orders.append(order)

        db.commit()
        logger.info(
            "Sync finished count=%s printed_count=%s",
            len(response_orders),
            printed_count,
        )
        return {
            "count": len(response_orders),
            "printed_count": printed_count,
            "orders": response_orders,
        }


def upsert_order(db: Session, payload: dict) -> tuple[Order, bool]:
    order = db.execute(
        select(Order)
        .options(selectinload(Order.items))
        .where(Order.id == payload["id"])
    ).scalar_one_or_none()

    was_created = order is None
    if order is None:
        order = Order(id=payload["id"])
        db.add(order)

    preserve_status = order.status if order.status in {"printed", "done", "cancelled"} else payload["status"]
    order.source = payload["source"]
    order.status = preserve_status
    order.reference = payload["reference"]
    order.created_at = payload["created_at"]
    order.updated_at = datetime.utcnow()
    order.customer_name = payload["customer_name"]
    order.customer_phone = payload["customer_phone"]
    order.customer_email = payload["customer_email"]
    order.customer_address = payload["customer_address"]
    order.payment_method = payload["payment_method"]
    order.payment_status = payload["payment_status"]
    order.fulfillment_method = payload["fulfillment_method"]
    order.fulfillment_notes = payload["fulfillment_notes"]
    order.subtotal = payload["subtotal"]
    order.delivery = payload["delivery"]
    order.tax = payload["tax"]
    order.discount = payload["discount"]
    order.total = payload["total"]
    order.currency = payload["currency"]
    order.raw_payload = payload["raw_payload"]

    order.items.clear()
    for item_payload in payload["items"]:
        order.items.append(
            OrderItem(
                position=item_payload["position"],
                external_id=item_payload["external_id"],
                name=item_payload["name"],
                quantity=item_payload["quantity"],
                unit_price=item_payload["unit_price"],
                options=item_payload["options"],
            )
        )

    db.flush()
    db.refresh(order)
    return order, was_created


def should_auto_print(order: Order, was_created: bool) -> bool:
    if order.status != "new":
        return False
    return was_created or order.status == "new"
