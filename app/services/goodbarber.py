from urllib.parse import urljoin

import logging

import httpx

from app.config import settings


logger = logging.getLogger("orderbridge.goodbarber")


def build_orders_url() -> str:
    if not settings.goodbarber_app_id or not settings.goodbarber_api_key:
        raise ValueError("GOODBARBER_APP_ID y GOODBARBER_API_KEY son requeridos")

    resolved_path = (
        settings.goodbarber_orders_path
        .replace("{webzine_id}", settings.goodbarber_app_id)
        .replace("{app_id}", settings.goodbarber_app_id)
    )
    base = settings.goodbarber_base_url if settings.goodbarber_base_url.endswith("/") else f"{settings.goodbarber_base_url}/"
    url = urljoin(base, resolved_path.lstrip("/"))
    return f"{url}?per_page={settings.goodbarber_per_page}"


async def fetch_goodbarber_orders() -> list[dict]:
    url = build_orders_url()
    logger.info("Fetching orders from GoodBarber: %s", url)
    async with httpx.AsyncClient(timeout=settings.goodbarber_timeout_seconds) as client:
        response = await client.get(
            url,
            headers={
                "Accept": "application/json",
                "token": settings.goodbarber_api_key,
            },
        )

    logger.info("GoodBarber response status: %s", response.status_code)
    response.raise_for_status()
    payload = response.json()
    if isinstance(payload, dict):
        logger.info("GoodBarber payload keys: %s", list(payload.keys()))
    if isinstance(payload, list):
        logger.info("GoodBarber returned %s raw orders", len(payload))
        return payload
    orders = payload.get("orders") or payload.get("data") or []
    logger.info("GoodBarber returned %s orders", len(orders))
    return orders
