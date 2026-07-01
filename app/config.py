from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "OrderBridge Python"
    api_host: str = "127.0.0.1"
    api_port: int = 8000
    database_url: str = "sqlite:///./storage/orderbridge.db"

    goodbarber_app_id: str = ""
    goodbarber_api_key: str = ""
    goodbarber_base_url: str = "https://commerce.goodbarber.dev"
    goodbarber_orders_path: str = "/publicapi/v2/general/orders/{webzine_id}/"
    goodbarber_per_page: int = 50
    goodbarber_timeout_seconds: int = 15
    goodbarber_sync_enabled: bool = True
    goodbarber_sync_interval_seconds: int = 60

    auto_print_new_orders: bool = True
    print_pdf_dir: Path = Field(default=BASE_DIR / "storage" / "print_pdfs")
    printer_name: str = ""
    windows_print_action: str = "printto"


settings = Settings()
