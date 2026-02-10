"""Tests for the canonical Order model."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from order_automation.models.order import (
    Address,
    Order,
    OrderLineItem,
    OrderSource,
    OrderStatus,
    RawOrder,
    SubmissionResult,
    ValidationResult,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _line(sku: str = "ABC-123", qty: int = 10, price: str = "9.99") -> OrderLineItem:
    return OrderLineItem(sku=sku, quantity=qty, unit_price=Decimal(price))


def _order(**overrides) -> Order:
    defaults = dict(
        source=OrderSource.csv,
        customer_id="CUST-001",
        customer_name="Acme Corp",
        po_number="PO-100",
        line_items=[_line()],
        ship_to=Address(name="Warehouse", line1="1 Main St", city="Springfield", state="IL", postal_code="62701"),
    )
    defaults.update(overrides)
    return Order(**defaults)


# ---------------------------------------------------------------------------
# Address
# ---------------------------------------------------------------------------

class TestAddress:
    def test_defaults(self):
        addr = Address()
        assert addr.country == "US"
        assert addr.line2 is None

    def test_full(self):
        addr = Address(name="A", line1="1 St", line2="Apt 2", city="C", state="S", postal_code="12345", country="CA")
        assert addr.country == "CA"


# ---------------------------------------------------------------------------
# OrderLineItem
# ---------------------------------------------------------------------------

class TestOrderLineItem:
    def test_line_total(self):
        item = _line(qty=5, price="10.00")
        assert item.line_total == Decimal("50.00")

    def test_zero_price(self):
        item = _line(price="0")
        assert item.line_total == Decimal(0)

    def test_negative_quantity_rejected(self):
        with pytest.raises(ValidationError):
            OrderLineItem(sku="X", quantity=-1, unit_price=Decimal("1"))

    def test_zero_quantity_rejected(self):
        with pytest.raises(ValidationError):
            OrderLineItem(sku="X", quantity=0, unit_price=Decimal("1"))

    def test_negative_price_rejected(self):
        with pytest.raises(ValidationError):
            OrderLineItem(sku="X", quantity=1, unit_price=Decimal("-1"))

    def test_default_uom(self):
        assert _line().uom == "EA"


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class TestEnums:
    def test_order_source_values(self):
        assert set(OrderSource) == {
            OrderSource.email, OrderSource.csv, OrderSource.sheets,
            OrderSource.api, OrderSource.manual, OrderSource.fax,
        }

    def test_order_status_values(self):
        assert OrderStatus.pending.value == "pending"


# ---------------------------------------------------------------------------
# RawOrder
# ---------------------------------------------------------------------------

class TestRawOrder:
    def test_minimal(self):
        raw = RawOrder(source=OrderSource.csv)
        assert raw.rows == []
        assert raw.body == ""

    def test_with_data(self):
        raw = RawOrder(source=OrderSource.email, body="hello", metadata={"from": "x@y.com"})
        assert raw.metadata["from"] == "x@y.com"


# ---------------------------------------------------------------------------
# Order
# ---------------------------------------------------------------------------

class TestOrder:
    def test_valid_order(self):
        o = _order()
        assert o.status == OrderStatus.pending
        assert o.total_amount == Decimal("99.90")
        assert o.total_quantity == 10
        assert len(o.id) == 36  # UUID

    def test_multiple_line_items(self):
        o = _order(line_items=[_line(qty=2, price="10"), _line(qty=3, price="5")])
        assert o.total_amount == Decimal("35")
        assert o.total_quantity == 5

    def test_must_have_line_items(self):
        with pytest.raises(ValidationError, match="at least one line item"):
            _order(line_items=[])

    def test_computed_fields_not_settable(self):
        o = _order()
        assert isinstance(o.total_amount, Decimal)

    def test_order_date_default_today(self):
        o = _order()
        assert o.order_date == date.today()

    def test_serialization_roundtrip(self):
        o = _order()
        data = o.model_dump()
        o2 = Order.model_validate(data)
        assert o2.id == o.id
        assert o2.total_amount == o.total_amount
        assert o2.line_items[0].sku == o.line_items[0].sku

    def test_json_roundtrip(self):
        o = _order()
        json_str = o.model_dump_json()
        o2 = Order.model_validate_json(json_str)
        assert o2.po_number == o.po_number

    def test_errors_list(self):
        o = _order()
        o.errors.append("bad SKU")
        assert len(o.errors) == 1

    def test_metadata(self):
        o = _order(metadata={"origin_file": "test.csv"})
        assert o.metadata["origin_file"] == "test.csv"

    def test_requested_ship_date_optional(self):
        o = _order()
        assert o.requested_ship_date is None
        o2 = _order(requested_ship_date=date(2025, 12, 31))
        assert o2.requested_ship_date == date(2025, 12, 31)


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------

class TestValidationResult:
    def test_valid(self):
        r = ValidationResult(valid=True)
        assert r.errors == []

    def test_invalid(self):
        r = ValidationResult(valid=False, errors=["missing PO"])
        assert not r.valid


class TestSubmissionResult:
    def test_success(self):
        r = SubmissionResult(success=True, destination="database", external_ref="abc")
        assert r.error == ""

    def test_failure(self):
        r = SubmissionResult(success=False, destination="erp", error="timeout")
        assert not r.success
