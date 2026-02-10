"""Streamlit UI for manual order entry.

Run with:  streamlit run src/order_automation/ui/app.py
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

import streamlit as st
import yaml

from order_automation.engine.normalizer import OrderNormalizer
from order_automation.engine.pipeline import OrderPipeline
from order_automation.engine.router import OrderRouter
from order_automation.engine.validator import OrderValidator
from order_automation.models.order import (
    Address,
    Order,
    OrderLineItem,
    OrderSource,
    OrderStatus,
    ValidationResult,
)
from order_automation.output.database import DatabaseAdapter
from order_automation.output.erp import ERPAdapter
from order_automation.output.notifications import EmailConfirmation, SlackNotifier
from order_automation.output.sheets_output import SheetsOutputAdapter
from order_automation.output.web_portal import WebPortalAdapter

# ------------------------------------------------------------------
# Setup
# ------------------------------------------------------------------

def _load_config() -> dict:
    p = Path("config/settings.yaml")
    if not p.exists():
        return {}
    with open(p) as f:
        return yaml.safe_load(f) or {}


@st.cache_resource
def _get_pipeline() -> OrderPipeline:
    cfg = _load_config()
    db_url = cfg.get("database", {}).get("url", "sqlite:///orders.db")
    router_path = cfg.get("routing", {}).get("rules_file", "config/routing_rules.yaml")

    router = OrderRouter()
    if Path(router_path).exists():
        router.load(router_path)

    pipeline = OrderPipeline(
        normalizer=OrderNormalizer(),
        validator=OrderValidator(),
        router=router,
    )

    out_cfg = cfg.get("output", {})
    pipeline.register_adapter("database", DatabaseAdapter(url=db_url))

    if out_cfg.get("sheets", {}).get("enabled", False):
        pipeline.register_adapter("sheets", SheetsOutputAdapter(
            spreadsheet_id=out_cfg["sheets"].get("spreadsheet_id", ""),
        ))
    if out_cfg.get("slack", {}).get("enabled", False):
        pipeline.register_adapter("slack_notify", SlackNotifier())
    if out_cfg.get("email_confirmation", {}).get("enabled", False):
        pipeline.register_adapter("email_confirmation", EmailConfirmation())
    if out_cfg.get("erp", {}).get("enabled", False):
        pipeline.register_adapter("erp", ERPAdapter())
    if out_cfg.get("web_portal", {}).get("enabled", False):
        pipeline.register_adapter("web_portal", WebPortalAdapter())

    return pipeline


@st.cache_resource
def _get_db() -> DatabaseAdapter:
    cfg = _load_config()
    db_url = cfg.get("database", {}).get("url", "sqlite:///orders.db")
    return DatabaseAdapter(url=db_url)


# ------------------------------------------------------------------
# Page
# ------------------------------------------------------------------

st.set_page_config(page_title="Order Entry", layout="wide")
st.title("Manual Order Entry")

# Sidebar — recent orders
with st.sidebar:
    st.header("Recent Orders")
    db = _get_db()
    recent = db.get_all_orders()[-10:]
    if recent:
        for r in reversed(recent):
            st.text(f"{r.po_number} [{r.status}]")
    else:
        st.info("No orders yet.")

# ------------------------------------------------------------------
# Form
# ------------------------------------------------------------------

col1, col2 = st.columns(2)

with col1:
    customer_id = st.text_input("Customer ID")
    customer_name = st.text_input("Customer Name")
    po_number = st.text_input("PO Number")
    order_date = st.date_input("Order Date", value=date.today())

with col2:
    st.subheader("Ship-To Address")
    ship_name = st.text_input("Name", key="ship_name")
    ship_line1 = st.text_input("Address Line 1", key="ship_line1")
    ship_city = st.text_input("City", key="ship_city")
    ship_state = st.text_input("State", key="ship_state")
    ship_zip = st.text_input("ZIP Code", key="ship_zip")

# Line items
st.subheader("Line Items")

if "line_items" not in st.session_state:
    st.session_state.line_items = [{"sku": "", "description": "", "quantity": 1, "unit_price": "0.00"}]


def _add_line():
    st.session_state.line_items.append({"sku": "", "description": "", "quantity": 1, "unit_price": "0.00"})


def _remove_line(idx: int):
    if len(st.session_state.line_items) > 1:
        st.session_state.line_items.pop(idx)


for i, item in enumerate(st.session_state.line_items):
    c1, c2, c3, c4, c5 = st.columns([2, 3, 1, 1.5, 0.5])
    with c1:
        item["sku"] = st.text_input("SKU", value=item["sku"], key=f"sku_{i}")
    with c2:
        item["description"] = st.text_input("Description", value=item["description"], key=f"desc_{i}")
    with c3:
        item["quantity"] = st.number_input("Qty", value=item["quantity"], min_value=1, key=f"qty_{i}")
    with c4:
        item["unit_price"] = st.text_input("Unit Price", value=item["unit_price"], key=f"price_{i}")
    with c5:
        st.write("")  # spacer
        if st.button("X", key=f"rm_{i}"):
            _remove_line(i)
            st.rerun()

st.button("+ Add Line Item", on_click=_add_line)

# ------------------------------------------------------------------
# Actions
# ------------------------------------------------------------------

bcol1, bcol2 = st.columns(2)

with bcol1:
    validate_btn = st.button("Validate")
with bcol2:
    submit_btn = st.button("Submit", type="primary")


def _build_order() -> Order:
    """Build an Order from the form state."""
    items: list[OrderLineItem] = []
    for item in st.session_state.line_items:
        sku = item.get("sku", "").strip()
        if not sku:
            continue
        try:
            price = Decimal(str(item.get("unit_price", "0")).replace(",", ""))
        except InvalidOperation:
            price = Decimal(0)
        items.append(OrderLineItem(
            sku=sku,
            description=item.get("description", ""),
            quantity=max(1, int(item.get("quantity", 1))),
            unit_price=price,
        ))

    if not items:
        items = [OrderLineItem(sku="PLACEHOLDER", quantity=1, unit_price=Decimal(0))]

    return Order(
        source=OrderSource.manual,
        customer_id=customer_id,
        customer_name=customer_name,
        po_number=po_number,
        order_date=order_date,
        ship_to=Address(
            name=ship_name,
            line1=ship_line1,
            city=ship_city,
            state=ship_state,
            postal_code=ship_zip,
        ),
        line_items=items,
    )


if validate_btn:
    order = _build_order()
    v = OrderValidator()
    result: ValidationResult = v.validate(order)
    if result.valid:
        st.success("Order is valid.")
    else:
        for err in result.errors:
            st.error(err)

if submit_btn:
    order = _build_order()
    pipeline = _get_pipeline()
    processed = pipeline.process(order)
    if processed.status == OrderStatus.completed:
        st.success(f"Order submitted successfully! ID: {processed.id}")
    else:
        st.error(f"Order failed: {'; '.join(processed.errors)}")
