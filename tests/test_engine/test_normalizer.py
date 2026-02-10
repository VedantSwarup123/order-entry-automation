"""Tests for OrderNormalizer."""
from __future__ import annotations

from decimal import Decimal

from order_automation.engine.normalizer import OrderNormalizer
from order_automation.models.order import Address, Order, OrderLineItem, OrderSource


def _line(sku: str = "abc-123", uom: str = "each", qty: int = 1, price: str = "10") -> OrderLineItem:
    return OrderLineItem(sku=sku, quantity=qty, unit_price=Decimal(price), uom=uom)


def _order(**kw) -> Order:
    defaults = dict(
        source=OrderSource.csv,
        customer_id="C1",
        customer_name="  acme corp  ",
        po_number="PO-1",
        line_items=[_line()],
        ship_to=Address(
            name="W", line1="1 St", city="C",
            state="california", postal_code="9 0210", country="usa",
        ),
    )
    defaults.update(kw)
    return Order(**defaults)


def test_customer_name_title_case():
    n = OrderNormalizer()
    o = n.normalize(_order())
    assert o.customer_name == "Acme Corp"


def test_state_abbreviation():
    n = OrderNormalizer()
    o = n.normalize(_order())
    assert o.ship_to.state == "CA"


def test_country_normalisation():
    n = OrderNormalizer()
    o = n.normalize(_order())
    assert o.ship_to.country == "US"


def test_postal_code_cleanup():
    n = OrderNormalizer()
    o = n.normalize(_order())
    assert o.ship_to.postal_code == "90210"


def test_sku_uppercase_trim():
    n = OrderNormalizer()
    o = n.normalize(_order(line_items=[_line(sku="  abc-123 ")]))
    assert o.line_items[0].sku == "ABC-123"


def test_uom_standardisation():
    n = OrderNormalizer()
    o = n.normalize(_order(line_items=[_line(uom="each")]))
    assert o.line_items[0].uom == "EA"

    o2 = n.normalize(_order(line_items=[_line(uom="Case")]))
    assert o2.line_items[0].uom == "CS"


def test_bill_to_also_normalised():
    n = OrderNormalizer()
    o = _order(bill_to=Address(
        name="HQ", line1="2 St", city="B",
        state="new york", postal_code="10001", country="united states",
    ))
    result = n.normalize(o)
    assert result.bill_to is not None
    assert result.bill_to.state == "NY"
    assert result.bill_to.country == "US"


def test_already_abbreviated_state_unchanged():
    n = OrderNormalizer()
    o = _order(ship_to=Address(
        name="W", line1="1 St", city="C",
        state="TX", postal_code="75001", country="US",
    ))
    result = n.normalize(o)
    assert result.ship_to.state == "TX"
