"""Tests for DatabaseAdapter using SQLite in-memory."""
from __future__ import annotations

from decimal import Decimal

from order_automation.models.order import (
    Address,
    Order,
    OrderLineItem,
    OrderSource,
    OrderStatus,
)
from order_automation.output.database import DatabaseAdapter


def _order(**kw) -> Order:
    defaults = dict(
        source=OrderSource.csv,
        customer_id="C1",
        customer_name="Acme",
        po_number="PO-1",
        line_items=[OrderLineItem(sku="X", quantity=2, unit_price=Decimal("10"))],
        ship_to=Address(name="W", line1="1 St", city="C", state="IL", postal_code="60601"),
    )
    defaults.update(kw)
    return Order(**defaults)


class TestDatabaseAdapter:
    def _adapter(self) -> DatabaseAdapter:
        return DatabaseAdapter(url="sqlite:///:memory:")

    def test_submit_success(self):
        db = self._adapter()
        order = _order()
        result = db.submit(order)
        assert result.success
        assert result.destination == "database"

    def test_get_order(self):
        db = self._adapter()
        order = _order()
        db.submit(order)
        record = db.get_order(order.id)
        assert record is not None
        assert record.po_number == "PO-1"
        assert record.customer_id == "C1"

    def test_line_items_persisted(self):
        db = self._adapter()
        order = _order(line_items=[
            OrderLineItem(sku="A", quantity=1, unit_price=Decimal("5")),
            OrderLineItem(sku="B", quantity=3, unit_price=Decimal("7")),
        ])
        db.submit(order)
        items = db.get_line_items(order.id)
        assert len(items) == 2
        skus = {i.sku for i in items}
        assert skus == {"A", "B"}

    def test_get_failures(self):
        db = self._adapter()
        ok = _order(status=OrderStatus.completed)
        err = _order(status=OrderStatus.error)
        db.submit(ok)
        db.submit(err)
        failures = db.get_failures()
        assert len(failures) == 1
        assert failures[0].id == err.id

    def test_get_all_orders(self):
        db = self._adapter()
        db.submit(_order(po_number="PO-1"))
        db.submit(_order(po_number="PO-2"))
        assert len(db.get_all_orders()) == 2

    def test_get_stats(self):
        db = self._adapter()
        db.submit(_order(status=OrderStatus.completed))
        db.submit(_order(status=OrderStatus.completed))
        db.submit(_order(status=OrderStatus.error))
        stats = db.get_stats()
        assert stats.get("completed") == 2
        assert stats.get("error") == 1

    def test_get_nonexistent_order(self):
        db = self._adapter()
        assert db.get_order("does-not-exist") is None

    def test_total_amount_stored(self):
        db = self._adapter()
        order = _order(line_items=[
            OrderLineItem(sku="X", quantity=5, unit_price=Decimal("20")),
        ])
        db.submit(order)
        record = db.get_order(order.id)
        assert record is not None
        assert Decimal(str(record.total_amount)) == Decimal("100")
