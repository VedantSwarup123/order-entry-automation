"""Tests for OrderRouter."""
from __future__ import annotations

import textwrap
import tempfile
from decimal import Decimal
from pathlib import Path

from order_automation.engine.router import OrderRouter
from order_automation.models.order import Address, Order, OrderLineItem, OrderSource


def _line(qty: int = 1, price: str = "10") -> OrderLineItem:
    return OrderLineItem(sku="X", quantity=qty, unit_price=Decimal(price))


def _order(state: str = "IL", qty: int = 1, price: str = "10") -> Order:
    return Order(
        source=OrderSource.csv,
        customer_id="C1",
        po_number="PO-1",
        line_items=[_line(qty=qty, price=price)],
        ship_to=Address(name="W", line1="1 St", city="C", state=state, postal_code="60601"),
    )


def _write_rules(tmp: Path, yaml_text: str) -> Path:
    p = tmp / "rules.yaml"
    p.write_text(textwrap.dedent(yaml_text))
    return p


def test_always_condition():
    with tempfile.TemporaryDirectory() as td:
        p = _write_rules(Path(td), """
        rules:
          - name: test
            condition: "always"
            destination: "db"
        """)
        r = OrderRouter(p)
        assert r.route(_order()) == ["db"]


def test_field_gt():
    with tempfile.TemporaryDirectory() as td:
        p = _write_rules(Path(td), """
        rules:
          - name: big
            condition: {field: "total_amount", operator: ">", value: 5000}
            destination: "erp"
        """)
        r = OrderRouter(p)
        # 1 * 10 = 10, not > 5000
        assert r.route(_order()) == []
        # 100 * 100 = 10000 > 5000
        assert r.route(_order(qty=100, price="100")) == ["erp"]


def test_field_in_list():
    with tempfile.TemporaryDirectory() as td:
        p = _write_rules(Path(td), """
        rules:
          - name: west
            condition: {field: "ship_to.state", operator: "in", value: ["CA","OR","WA"]}
            destination: "portal"
        """)
        r = OrderRouter(p)
        assert r.route(_order(state="CA")) == ["portal"]
        assert r.route(_order(state="IL")) == []


def test_multiple_rules():
    with tempfile.TemporaryDirectory() as td:
        p = _write_rules(Path(td), """
        rules:
          - name: all
            condition: "always"
            destination: "db"
          - name: west
            condition: {field: "ship_to.state", operator: "in", value: ["CA"]}
            destination: "portal"
        """)
        r = OrderRouter(p)
        assert r.route(_order(state="CA")) == ["db", "portal"]
        assert r.route(_order(state="IL")) == ["db"]


def test_default_rules_file():
    """Load the actual config/routing_rules.yaml shipped with the project."""
    r = OrderRouter("config/routing_rules.yaml")
    o = _order(state="CA", qty=100, price="100")
    dests = r.route(o)
    assert "database" in dests
    assert "web_portal" in dests
    assert "erp" in dests
