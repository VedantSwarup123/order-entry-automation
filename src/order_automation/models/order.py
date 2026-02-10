"""Canonical order model.

Every order — regardless of ingest source — is normalised into these
Pydantic v2 models before entering the processing pipeline.
"""
from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, computed_field, model_validator

# ---------------------------------------------------------------------------
# Value objects
# ---------------------------------------------------------------------------

class Address(BaseModel):
    """Postal address."""

    name: str = ""
    line1: str = ""
    line2: str | None = None
    city: str = ""
    state: str = ""
    postal_code: str = ""
    country: str = "US"


class OrderLineItem(BaseModel):
    """Single line on a purchase order."""

    sku: str
    description: str = ""
    quantity: int = Field(gt=0)
    unit_price: Decimal = Field(ge=0)
    uom: str = "EA"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def line_total(self) -> Decimal:
        """Quantity multiplied by unit price."""
        return Decimal(self.quantity) * self.unit_price


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class OrderSource(str, Enum):
    """Where the order originated."""

    email = "email"
    csv = "csv"
    sheets = "sheets"
    api = "api"
    manual = "manual"
    fax = "fax"


class OrderStatus(str, Enum):
    """Processing status of an order."""

    pending = "pending"
    validated = "validated"
    routed = "routed"
    completed = "completed"
    error = "error"


# ---------------------------------------------------------------------------
# Raw ingest payload
# ---------------------------------------------------------------------------

class RawOrder(BaseModel):
    """Loosely-typed payload coming straight from an ingest source."""

    source: OrderSource
    source_ref: str = ""
    body: str = ""
    attachments: list[str] = Field(default_factory=list)
    rows: list[dict[str, Any]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Canonical order
# ---------------------------------------------------------------------------

class Order(BaseModel):
    """Fully-typed order ready for the processing pipeline."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source: OrderSource
    source_ref: str = ""
    customer_id: str = ""
    customer_name: str = ""
    po_number: str = ""
    order_date: date = Field(default_factory=date.today)
    requested_ship_date: date | None = None
    ship_to: Address = Field(default_factory=Address)
    bill_to: Address | None = None
    line_items: list[OrderLineItem] = Field(default_factory=list)
    notes: str = ""
    status: OrderStatus = OrderStatus.pending
    errors: list[str] = Field(default_factory=list)
    destinations: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total_amount(self) -> Decimal:
        """Sum of all line-item totals."""
        return sum((item.line_total for item in self.line_items), Decimal(0))

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total_quantity(self) -> int:
        """Sum of all line-item quantities."""
        return sum(item.quantity for item in self.line_items)

    @model_validator(mode="after")
    def _must_have_line_items(self) -> Order:
        if not self.line_items:
            raise ValueError("Order must have at least one line item")
        return self


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------

class ValidationResult(BaseModel):
    """Outcome of order validation."""

    valid: bool
    errors: list[str] = Field(default_factory=list)


class SubmissionResult(BaseModel):
    """Outcome of submitting an order to a destination adapter."""

    success: bool
    destination: str = ""
    external_ref: str = ""
    error: str = ""
