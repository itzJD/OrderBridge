from datetime import datetime
from zoneinfo import ZoneInfo

from app.config import settings


def get_local_timezone() -> ZoneInfo:
    return ZoneInfo(settings.local_timezone)


def now_local_naive() -> datetime:
    return datetime.now(get_local_timezone()).replace(tzinfo=None)


def parse_utc_to_local_naive(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None

    if parsed.tzinfo is None:
        return parsed

    return parsed.astimezone(get_local_timezone()).replace(tzinfo=None)
