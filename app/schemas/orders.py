from datetime import datetime

from pydantic import BaseModel, ConfigDict


class OrderItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    external_id: str
    name: str
    quantity: float
    unit_price: float
    options: list


class OrderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    source: str
    status: str
    reference: str
    created_at: datetime
    updated_at: datetime
    customer_name: str
    customer_phone: str
    customer_email: str
    customer_address: str
    payment_method: str
    payment_status: str
    fulfillment_method: str
    fulfillment_notes: str
    subtotal: float
    delivery: float
    tax: float
    discount: float
    total: float
    currency: str
    items: list[OrderItemRead]


class OrderListResponse(BaseModel):
    orders: list[OrderRead]


class OrderResponse(BaseModel):
    order: OrderRead


class UpdateStatusRequest(BaseModel):
    status: str
