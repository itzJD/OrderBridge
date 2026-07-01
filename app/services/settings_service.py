from sqlalchemy.orm import Session

from app.db.models import AppSetting


PRINTER_SETTING_KEY = "selected_printer"


def get_setting(db: Session, key: str, default: str = "") -> str:
    setting = db.get(AppSetting, key)
    return setting.value if setting else default


def set_setting(db: Session, key: str, value: str) -> None:
    setting = db.get(AppSetting, key)
    if setting is None:
        setting = AppSetting(key=key, value=value)
        db.add(setting)
    else:
        setting.value = value


def get_selected_printer(db: Session) -> str:
    return get_setting(db, PRINTER_SETTING_KEY)


def set_selected_printer(db: Session, printer_name: str) -> None:
    set_setting(db, PRINTER_SETTING_KEY, printer_name.strip())
