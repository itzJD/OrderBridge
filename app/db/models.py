from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.services.time_service import now_local_naive


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    source: Mapped[str] = mapped_column(String(32), default="goodbarber")
    status: Mapped[str] = mapped_column(String(32), default="new", index=True)
    reference: Mapped[str] = mapped_column(String(128), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now_local_naive, index=True)

    customer_name: Mapped[str] = mapped_column(String(255), default="")
    customer_phone: Mapped[str] = mapped_column(String(128), default="")
    customer_email: Mapped[str] = mapped_column(String(255), default="")
    customer_address: Mapped[str] = mapped_column(Text, default="")

    payment_method: Mapped[str] = mapped_column(String(255), default="")
    payment_status: Mapped[str] = mapped_column(String(255), default="")
    fulfillment_method: Mapped[str] = mapped_column(String(255), default="")
    fulfillment_notes: Mapped[str] = mapped_column(Text, default="")

    subtotal: Mapped[float] = mapped_column(Float, default=0)
    delivery: Mapped[float] = mapped_column(Float, default=0)
    tax: Mapped[float] = mapped_column(Float, default=0)
    discount: Mapped[float] = mapped_column(Float, default=0)
    total: Mapped[float] = mapped_column(Float, default=0)
    currency: Mapped[str] = mapped_column(String(16), default="USD")

    raw_payload: Mapped[dict] = mapped_column(JSON, default=dict)

    items: Mapped[list["OrderItem"]] = relationship(
        back_populates="order",
        cascade="all, delete-orphan",
        order_by="OrderItem.position",
    )


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[str] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    position: Mapped[int] = mapped_column(Integer, default=0)
    external_id: Mapped[str] = mapped_column(String(128), default="")
    name: Mapped[str] = mapped_column(String(255))
    quantity: Mapped[float] = mapped_column(Float, default=1)
    unit_price: Mapped[float] = mapped_column(Float, default=0)
    options: Mapped[list] = mapped_column(JSON, default=list)

    order: Mapped[Order] = relationship(back_populates="items")


class AppSetting(Base):
    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(Text, default="")
