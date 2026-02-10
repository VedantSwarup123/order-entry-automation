"""Tests for OrderValidator."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from order_automation.engine.validator import OrderValidator
from order_automation.models.order import Address, Order, OrderLineItem, OrderSource


def _line(sku: str = "ABC", qty: int = 1, price: str = "10") -> OrderLineItem:
    return OrderLineItem(sku=sku, quantity=qty, unit_price=Decimal(price))


def _order(**kw) -> Order:
    defaults = dict(
        source=OrderSource.csv,
        customer_id="C1",
        po_number="PO-1",
        line_items=[_line()],
        ship_to=Address(name="W", line1="1 St", city="C", state="IL", postal_code="60601"),
    )
    defaults.update(kw)
    return Order(**defaults)


def test_valid_order():
    v = OrderValidator()
    res = v.validate(_order())
    assert res.valid
    assert res.errors == []


def test_missing_customer_id():
    v = OrderValidator()
    res = v.validate(_order(customer_id=""))
    assert not res.valid
    assert any("customer_id" in e for e in res.errors)


def test_missing_po_number():
    v = OrderValidator()
    res = v.validate(_order(po_number="  "))
    assert not res.valid
    assert any("po_number" in e for e in res.errors)


def test_empty_sku():
    v = OrderValidator()
    res = v.validate(_order(line_items=[_line(sku="  ")]))
    assert not res.valid
    assert any("sku" in e for e in res.errors)


def test_ship_date_before_order_date():
    v = OrderValidator()
    res = v.validate(_order(
        order_date=date(2025, 6, 1),
        requested_ship_date=date(2025, 5, 1),
    ))
    assert not res.valid
    assert any("ship_date" in e for e in res.errors)


def test_ship_date_equal_order_date_ok():
    v = OrderValidator()
    d = date(2025, 6, 1)
    res = v.validate(_order(order_date=d, requested_ship_date=d))
    assert res.valid
