"""Tests for OrderPipeline."""
from __future__ import annotations

from decimal import Decimal

from order_automation.engine.pipeline import OrderPipeline
from order_automation.engine.router import OrderRouter
from order_automation.models.order import (
    Address,
    Order,
    OrderLineItem,
    OrderSource,
    OrderStatus,
    SubmissionResult,
)


# ---------------------------------------------------------------------------
# Mock adapter
# ---------------------------------------------------------------------------

class MockAdapter:
    """Records submitted orders and returns configurable results."""

    def __init__(self, *, success: bool = True, error: str = "") -> None:
        self.submitted: list[Order] = []
        self._success = success
        self._error = error

    def submit(self, order: Order) -> SubmissionResult:
        """Record the order and return the configured result."""
        self.submitted.append(order)
        return SubmissionResult(success=self._success, destination="mock", error=self._error)


class FailingAdapter:
    """Always raises an exception."""

    def submit(self, order: Order) -> SubmissionResult:
        """Raise to simulate an adapter crash."""
        raise RuntimeError("boom")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _order(**kw) -> Order:
    defaults = dict(
        source=OrderSource.csv,
        customer_id="C1",
        po_number="PO-1",
        line_items=[OrderLineItem(sku="X", quantity=1, unit_price=Decimal("10"))],
        ship_to=Address(name="W", line1="1 St", city="C", state="IL", postal_code="60601"),
    )
    defaults.update(kw)
    return Order(**defaults)


def _pipeline_with_mock(adapter: MockAdapter | None = None) -> tuple[OrderPipeline, MockAdapter]:
    adapter = adapter or MockAdapter()
    router = OrderRouter()
    router.rules = [{"name": "all", "condition": "always", "destination": "mock"}]
    p = OrderPipeline(router=router)
    p.register_adapter("mock", adapter)
    return p, adapter


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_happy_path():
    pipe, adapter = _pipeline_with_mock()
    o = pipe.process(_order())
    assert o.status == OrderStatus.completed
    assert len(adapter.submitted) == 1


def test_validation_failure_short_circuits():
    pipe, adapter = _pipeline_with_mock()
    o = pipe.process(_order(customer_id=""))
    assert o.status == OrderStatus.error
    assert "customer_id" in o.errors[0]
    assert len(adapter.submitted) == 0


def test_adapter_returning_failure():
    bad = MockAdapter(success=False, error="downstream error")
    pipe, _ = _pipeline_with_mock(bad)
    o = pipe.process(_order())
    assert o.status == OrderStatus.error
    assert any("downstream error" in e for e in o.errors)


def test_adapter_exception_captured():
    router = OrderRouter()
    router.rules = [{"name": "all", "condition": "always", "destination": "fail"}]
    pipe = OrderPipeline(router=router)
    pipe.register_adapter("fail", FailingAdapter())
    o = pipe.process(_order())
    assert o.status == OrderStatus.error
    assert any("boom" in e for e in o.errors)


def test_missing_adapter_skipped():
    router = OrderRouter()
    router.rules = [
        {"name": "db", "condition": "always", "destination": "database"},
        {"name": "ghost", "condition": "always", "destination": "nonexistent"},
    ]
    adapter = MockAdapter()
    pipe = OrderPipeline(router=router)
    pipe.register_adapter("database", adapter)
    o = pipe.process(_order())
    # "nonexistent" skipped with warning, "database" succeeds
    assert o.status == OrderStatus.completed
    assert len(adapter.submitted) == 1


def test_normalisation_applied():
    pipe, adapter = _pipeline_with_mock()
    o = pipe.process(_order(customer_name="  acme  "))
    assert adapter.submitted[0].customer_name == "Acme"
