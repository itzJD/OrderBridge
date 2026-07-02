from datetime import datetime
from uuid import uuid4


def normalize_goodbarber_order(payload: dict) -> dict:
    source = payload.get("order") or payload.get("data") or payload
    customer = source.get("customer") or source.get("billing_address") or source.get("shipping_address") or {}
    totals = source.get("totals")
    if not isinstance(totals, dict):
        totals = {}

    order_id = str(source.get("id") or source.get("order_id") or source.get("reference") or uuid4())

    return {
        "id": order_id,
        "source": "goodbarber",
        "status": map_goodbarber_status(source.get("status")),
        "reference": source.get("reference") or source.get("order_num") or source.get("number") or order_id,
        "created_at": parse_dt(source.get("created_at")) or datetime.utcnow(),
        "customer_name": (
            source.get("customer_name")
            or customer.get("name")
            or " ".join(filter(None, [source.get("first_name"), source.get("last_name")]))
            or " ".join(filter(None, [customer.get("first_name"), customer.get("last_name")]))
            or "Cliente"
        ),
        "customer_phone": source.get("phone") or customer.get("phone") or customer.get("phone_number") or "",
        "customer_email": source.get("email") or customer.get("email") or "",
        "customer_address": format_address(customer),
        "payment_method": source.get("payment_method") or source.get("payment", {}).get("method") or "No especificado",
        "payment_status": source.get("payment_status") or source.get("payment", {}).get("status") or "pendiente",
        "fulfillment_method": (
            source.get("shipping_method")
            or source.get("fulfillment", {}).get("method")
            or source.get("delivery_method")
            or "No especificado"
        ),
        "fulfillment_notes": source.get("customer_note") or source.get("notes") or source.get("comment") or "",
        "subtotal": as_float(totals.get("subtotal") or source.get("subtotal")),
        "delivery": as_float(totals.get("delivery") or totals.get("shipping") or source.get("shipping_total")),
        "tax": as_float(totals.get("tax") or source.get("tax_total")),
        "discount": as_float(totals.get("discount") or source.get("discount_total")),
        "total": as_float(totals.get("total") or source.get("total_price") or source.get("total")),
        "currency": totals.get("currency") or source.get("currency") or "USD",
        "raw_payload": source,
        "items": normalize_items(source.get("items") or source.get("products") or source.get("lines") or []),
    }


def normalize_items(items: list[dict]) -> list[dict]:
    result = []
    for index, item in enumerate(items):
        result.append(
            {
                "position": index,
                "external_id": str(item.get("id") or item.get("product_id") or item.get("sku") or uuid4()),
                "name": (
                    item.get("name")
                    or item.get("title")
                    or item.get("product_name")
                    or item.get("product", {}).get("name")
                    or item.get("product", {}).get("title")
                    or item.get("sku")
                    or "Producto"
                ),
                "quantity": float(item.get("quantity") or item.get("qty") or 1),
                "unit_price": float(item.get("unit_price") or item.get("price") or 0),
                "options": item.get("options") or item.get("variants") or item.get("option_values") or [],
            }
        )
    return result


def map_goodbarber_status(status: str | None) -> str:
    normalized = str(status or "").upper()
    if normalized == "CANCELLED":
        return "cancelled"
    if normalized in {"DELIVERED", "FULFILLED"}:
        return "done"
    return "new"


def format_address(customer: dict) -> str:
    if customer.get("localized_address"):
        return customer["localized_address"]

    return ", ".join(
        filter(
            None,
            [
                customer.get("street"),
                customer.get("address"),
                customer.get("address_1"),
                customer.get("address_2"),
                customer.get("city"),
                customer.get("state"),
                customer.get("zip") or customer.get("postcode"),
                customer.get("country"),
            ],
        )
    )


def parse_dt(value: str | None):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def as_float(value) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0
