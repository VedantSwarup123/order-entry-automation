"""REST API ingest via FastAPI.

Exposes ``POST /api/v1/orders`` and ``POST /api/v1/orders/batch`` for
external systems to push orders directly into the pipeline.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

import structlog
from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

from order_automation.models.order import (
    Address,
    Order,
    OrderLineItem,
    OrderSource,
    OrderStatus,
)

log = structlog.get_logger()

app = FastAPI(title="Order Entry Automation API", version="0.1.0")

# The pipeline will be injected by main.py at startup.
_pipeline: Any = None


def set_pipeline(pipeline: Any) -> None:
    """Set the global pipeline instance (called once at startup)."""
    global _pipeline
    _pipeline = pipeline


# ------------------------------------------------------------------
# Auth
# ------------------------------------------------------------------

_API_KEY: str = "dev-api-key-change-me"


def set_api_key(key: str) -> None:
    """Override the default API key (from settings)."""
    global _API_KEY
    _API_KEY = key


def _verify_key(x_api_key: str = Header(...)) -> str:
    if x_api_key != _API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return x_api_key


# ------------------------------------------------------------------
# Request / response schemas
# ------------------------------------------------------------------

class LineItemIn(BaseModel):
    """Line item submitted via API."""

    sku: str
    description: str = ""
    quantity: int = Field(gt=0)
    unit_price: Decimal = Field(ge=0)
    uom: str = "EA"


class AddressIn(BaseModel):
    """Address submitted via API."""

    name: str = ""
    line1: str = ""
    line2: str | None = None
    city: str = ""
    state: str = ""
    postal_code: str = ""
    country: str = "US"


class OrderIn(BaseModel):
    """Inbound order payload."""

    customer_id: str
    customer_name: str = ""
    po_number: str
    order_date: date | None = None
    requested_ship_date: date | None = None
    ship_to: AddressIn = Field(default_factory=AddressIn)
    line_items: list[LineItemIn]
    notes: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class OrderOut(BaseModel):
    """Response after processing an order."""

    order_id: str
    status: str
    errors: list[str]


# ------------------------------------------------------------------
# Endpoints
# ------------------------------------------------------------------

@app.get("/api/v1/health")
def health() -> dict[str, str]:
    """Health check."""
    return {"status": "ok"}


def _to_order(payload: OrderIn) -> Order:
    """Convert an API payload to a canonical Order."""
    return Order(
        source=OrderSource.api,
        customer_id=payload.customer_id,
        customer_name=payload.customer_name,
        po_number=payload.po_number,
        order_date=payload.order_date or date.today(),
        requested_ship_date=payload.requested_ship_date,
        ship_to=Address(**payload.ship_to.model_dump()),
        line_items=[OrderLineItem(**li.model_dump()) for li in payload.line_items],
        notes=payload.notes,
        metadata=payload.metadata,
    )


@app.post("/api/v1/orders", response_model=OrderOut, dependencies=[Depends(_verify_key)])
def create_order(payload: OrderIn) -> OrderOut:
    """Submit a single order."""
    order = _to_order(payload)
    if _pipeline is not None:
        order = _pipeline.process(order)
    else:
        order.status = OrderStatus.error
        order.errors.append("Pipeline not initialised")
    return OrderOut(order_id=order.id, status=order.status.value, errors=order.errors)


class BatchIn(BaseModel):
    """Batch order payload."""

    orders: list[OrderIn]


class BatchOut(BaseModel):
    """Batch order response."""

    results: list[OrderOut]


@app.post("/api/v1/orders/batch", response_model=BatchOut, dependencies=[Depends(_verify_key)])
def create_orders_batch(payload: BatchIn) -> BatchOut:
    """Submit multiple orders at once."""
    results: list[OrderOut] = []
    for item in payload.orders:
        order = _to_order(item)
        if _pipeline is not None:
            order = _pipeline.process(order)
        else:
            order.status = OrderStatus.error
            order.errors.append("Pipeline not initialised")
        results.append(OrderOut(order_id=order.id, status=order.status.value, errors=order.errors))
    return BatchOut(results=results)
