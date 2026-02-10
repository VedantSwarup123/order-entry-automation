"""Dashboard API endpoints for the React frontend.

Provides read-only analytics, order listing, customer, and settings endpoints.
Mounted alongside the existing api_ingest.py app.
"""
from __future__ import annotations

import json
import math
import os
import shutil
from datetime import UTC, datetime, timedelta
from typing import Any

import structlog
import yaml
from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker

from order_automation.output.database import (
    AuditLogRecord,
    Base,
    LineItemRecord,
    OrderRecord,
)

log = structlog.get_logger()

router = APIRouter(prefix="/api/v1")

# Database session — initialised at startup
_Session: sessionmaker | None = None


def init_db(url: str = "sqlite:///orders.db") -> None:
    """Initialise the database session factory."""
    global _Session
    engine = create_engine(url, echo=False)
    Base.metadata.create_all(engine)
    _Session = sessionmaker(bind=engine)


def _get_session():
    if _Session is None:
        init_db()
    return _Session()


# ------------------------------------------------------------------
# Stats
# ------------------------------------------------------------------

@router.get("/stats")
def get_stats() -> dict[str, Any]:
    session = _get_session()
    try:
        total = session.query(func.count(OrderRecord.id)).scalar() or 0
        today = datetime.now(UTC).strftime("%Y-%m-%d")
        orders_today = (
            session.query(func.count(OrderRecord.id))
            .filter(func.date(OrderRecord.created_at) == today)
            .scalar() or 0
        )
        error_count = (
            session.query(func.count(OrderRecord.id))
            .filter(OrderRecord.status == "error")
            .scalar() or 0
        )
        success_rate = round((1 - error_count / max(total, 1)) * 100, 1)
        total_revenue = float(
            session.query(func.coalesce(func.sum(OrderRecord.total_amount), 0)).scalar()
        )

        # Trends: compare this week vs last week
        now = datetime.now(UTC)
        week_ago = now - timedelta(days=7)
        two_weeks_ago = now - timedelta(days=14)
        this_week = (
            session.query(func.count(OrderRecord.id))
            .filter(OrderRecord.created_at >= week_ago)
            .scalar() or 0
        )
        last_week = (
            session.query(func.count(OrderRecord.id))
            .filter(OrderRecord.created_at >= two_weeks_ago, OrderRecord.created_at < week_ago)
            .scalar() or 0
        )
        orders_change = round(((this_week - last_week) / max(last_week, 1)) * 100, 1)

        return {
            "total_orders": total,
            "orders_today": orders_today,
            "success_rate": success_rate,
            "total_revenue": total_revenue,
            "trends": {
                "orders_change": orders_change,
                "revenue_change": orders_change,  # approximate
            },
        }
    finally:
        session.close()


# ------------------------------------------------------------------
# Orders
# ------------------------------------------------------------------

@router.get("/orders")
def list_orders(
    limit: int = Query(15, ge=1, le=100),
    offset: int = Query(0, ge=0),
    status: str | None = None,
    source: str | None = None,
    search: str | None = None,
    sort: str = "created_at",
    order: str = "desc",
) -> dict[str, Any]:
    session = _get_session()
    try:
        q = session.query(OrderRecord)

        if status:
            q = q.filter(OrderRecord.status == status)
        if source:
            q = q.filter(OrderRecord.source == source)
        if search:
            pattern = f"%{search}%"
            q = q.filter(
                (OrderRecord.customer_name.ilike(pattern))
                | (OrderRecord.customer_id.ilike(pattern))
                | (OrderRecord.po_number.ilike(pattern))
                | (OrderRecord.id.ilike(pattern))
            )

        total = q.count()

        # Sorting
        allowed_sorts = {
            "id", "customer_name", "po_number", "source",
            "total_amount", "total_quantity", "status", "created_at",
        }
        sort_field = sort if sort in allowed_sorts else "created_at"
        col = getattr(OrderRecord, sort_field, OrderRecord.created_at)
        q = q.order_by(col.desc() if order == "desc" else col.asc())

        records = q.offset(offset).limit(limit).all()
        pages = max(1, math.ceil(total / limit))
        page = (offset // limit) + 1

        orders = []
        for r in records:
            item_count = (
                session.query(func.count(LineItemRecord.id))
                .filter(LineItemRecord.order_id == r.id)
                .scalar() or 0
            )
            orders.append({
                "id": r.id,
                "customer_id": r.customer_id,
                "customer_name": r.customer_name,
                "po_number": r.po_number,
                "source": r.source,
                "total_amount": float(r.total_amount or 0),
                "total_quantity": int(r.total_quantity or 0),
                "status": r.status,
                "created_at": str(r.created_at) if r.created_at else "",
                "errors": r.errors or "",
                "item_count": item_count,
            })

        return {"orders": orders, "total": total, "page": page, "pages": pages}
    finally:
        session.close()


@router.get("/orders/{order_id}")
def get_order(order_id: str) -> dict[str, Any]:
    session = _get_session()
    try:
        r = session.query(OrderRecord).filter_by(id=order_id).first()
        if not r:
            raise HTTPException(status_code=404, detail="Order not found")

        items = session.query(LineItemRecord).filter_by(order_id=order_id).all()
        line_items = [
            {
                "id": li.id,
                "sku": li.sku,
                "description": li.description,
                "quantity": int(li.quantity or 0),
                "unit_price": float(li.unit_price or 0),
                "uom": li.uom,
                "line_total": float(li.line_total or 0),
            }
            for li in items
        ]

        return {
            "id": r.id,
            "customer_id": r.customer_id,
            "customer_name": r.customer_name,
            "po_number": r.po_number,
            "source": r.source,
            "source_ref": r.source_ref or "",
            "order_date": r.order_date or "",
            "ship_to_name": r.ship_to_name or "",
            "ship_to_line1": r.ship_to_line1 or "",
            "ship_to_city": r.ship_to_city or "",
            "ship_to_state": r.ship_to_state or "",
            "ship_to_postal_code": r.ship_to_postal_code or "",
            "ship_to_country": r.ship_to_country or "",
            "total_amount": float(r.total_amount or 0),
            "total_quantity": int(r.total_quantity or 0),
            "status": r.status,
            "errors": r.errors or "",
            "notes": r.notes or "",
            "created_at": str(r.created_at) if r.created_at else "",
            "destinations": [],
            "line_items": line_items,
            "item_count": len(line_items),
        }
    finally:
        session.close()


# ------------------------------------------------------------------
# Customers
# ------------------------------------------------------------------

@router.get("/customers")
def list_customers() -> dict[str, list[dict[str, Any]]]:
    session = _get_session()
    try:
        rows = (
            session.query(
                OrderRecord.customer_id,
                OrderRecord.customer_name,
                func.count(OrderRecord.id).label("order_count"),
                func.sum(OrderRecord.total_amount).label("total_revenue"),
                func.max(OrderRecord.created_at).label("last_order"),
            )
            .group_by(OrderRecord.customer_id, OrderRecord.customer_name)
            .order_by(func.count(OrderRecord.id).desc())
            .all()
        )
        customers = [
            {
                "customer_id": r.customer_id,
                "customer_name": r.customer_name or r.customer_id,
                "order_count": r.order_count,
                "total_revenue": float(r.total_revenue or 0),
                "last_order": str(r.last_order) if r.last_order else "",
            }
            for r in rows
        ]
        return {"customers": customers}
    finally:
        session.close()


@router.get("/customers/{customer_id}")
def get_customer(customer_id: str) -> dict[str, Any]:
    session = _get_session()
    try:
        orders = (
            session.query(OrderRecord)
            .filter_by(customer_id=customer_id)
            .order_by(OrderRecord.created_at.desc())
            .all()
        )
        if not orders:
            raise HTTPException(status_code=404, detail="Customer not found")

        total_revenue = sum(float(o.total_amount or 0) for o in orders)
        order_list = [
            {
                "id": o.id,
                "customer_id": o.customer_id,
                "customer_name": o.customer_name,
                "po_number": o.po_number,
                "source": o.source,
                "total_amount": float(o.total_amount or 0),
                "total_quantity": int(o.total_quantity or 0),
                "status": o.status,
                "created_at": str(o.created_at) if o.created_at else "",
                "errors": o.errors or "",
                "item_count": 0,
            }
            for o in orders
        ]

        return {
            "customer_id": customer_id,
            "customer_name": orders[0].customer_name or customer_id,
            "order_count": len(orders),
            "total_revenue": total_revenue,
            "last_order": str(orders[0].created_at) if orders[0].created_at else "",
            "avg_order_value": round(total_revenue / max(len(orders), 1), 2),
            "orders": order_list,
        }
    finally:
        session.close()


# ------------------------------------------------------------------
# Analytics
# ------------------------------------------------------------------

@router.get("/analytics/orders-by-day")
def orders_by_day(days: int = Query(30, ge=1, le=365)) -> list[dict[str, Any]]:
    session = _get_session()
    try:
        cutoff = datetime.now(UTC) - timedelta(days=days)
        rows = (
            session.query(
                func.date(OrderRecord.created_at).label("day"),
                func.count(OrderRecord.id).label("count"),
                func.coalesce(func.sum(OrderRecord.total_amount), 0).label("revenue"),
            )
            .filter(OrderRecord.created_at >= cutoff)
            .group_by(func.date(OrderRecord.created_at))
            .order_by(func.date(OrderRecord.created_at))
            .all()
        )
        return [
            {"date": str(r.day), "count": r.count, "revenue": float(r.revenue)}
            for r in rows
        ]
    finally:
        session.close()


@router.get("/analytics/orders-by-source")
def orders_by_source() -> list[dict[str, Any]]:
    session = _get_session()
    try:
        rows = (
            session.query(
                OrderRecord.source,
                func.count(OrderRecord.id).label("count"),
            )
            .group_by(OrderRecord.source)
            .all()
        )
        return [{"source": r.source, "count": r.count} for r in rows]
    finally:
        session.close()


@router.get("/analytics/orders-by-status")
def orders_by_status() -> list[dict[str, Any]]:
    session = _get_session()
    try:
        rows = (
            session.query(
                OrderRecord.status,
                func.count(OrderRecord.id).label("count"),
            )
            .group_by(OrderRecord.status)
            .all()
        )
        return [{"status": r.status, "count": r.count} for r in rows]
    finally:
        session.close()


@router.get("/analytics/top-customers")
def top_customers(limit: int = Query(10, ge=1, le=50)) -> list[dict[str, Any]]:
    session = _get_session()
    try:
        rows = (
            session.query(
                OrderRecord.customer_id,
                OrderRecord.customer_name,
                func.count(OrderRecord.id).label("order_count"),
                func.sum(OrderRecord.total_amount).label("total_revenue"),
            )
            .group_by(OrderRecord.customer_id, OrderRecord.customer_name)
            .order_by(func.count(OrderRecord.id).desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "customer_id": r.customer_id,
                "customer_name": r.customer_name or r.customer_id,
                "order_count": r.order_count,
                "total_revenue": float(r.total_revenue or 0),
            }
            for r in rows
        ]
    finally:
        session.close()


# ------------------------------------------------------------------
# Inbox
# ------------------------------------------------------------------

@router.get("/inbox/recent")
def inbox_recent() -> list[dict[str, Any]]:
    session = _get_session()
    try:
        entries = (
            session.query(AuditLogRecord)
            .order_by(AuditLogRecord.timestamp.desc())
            .limit(20)
            .all()
        )
        return [
            {
                "id": e.id,
                "order_id": e.order_id,
                "action": e.action,
                "detail": e.detail or "",
                "timestamp": str(e.timestamp) if e.timestamp else "",
            }
            for e in entries
        ]
    finally:
        session.close()


@router.post("/inbox/upload-csv")
async def upload_csv(file: UploadFile = File(...)) -> dict[str, Any]:
    inbox_dir = "inbox/csv"
    os.makedirs(inbox_dir, exist_ok=True)
    dest = os.path.join(inbox_dir, file.filename or "upload.csv")
    with open(dest, "wb") as f:
        content = await file.read()
        f.write(content)

    # Try to trigger CSV ingest
    try:
        from order_automation.ingest.csv_ingest import CSVIngest
        ingest = CSVIngest(
            watch_dir=inbox_dir,
            processed_dir="processed/csv",
            column_mapping={},
        )
        raw_orders = ingest.poll()
        return {
            "status": "processed",
            "filename": file.filename,
            "orders_found": len(raw_orders),
        }
    except Exception as exc:
        # File saved but ingest failed — that's okay for demo
        return {
            "status": "saved",
            "filename": file.filename,
            "message": f"File saved. Ingest error: {exc}",
        }


# ------------------------------------------------------------------
# Settings
# ------------------------------------------------------------------

@router.get("/settings/integrations")
def settings_integrations() -> dict[str, str]:
    return {
        "gmail": "disconnected",
        "outlook": "disconnected",
        "sheets": "disconnected",
        "slack": "disconnected",
    }


@router.get("/settings/routing-rules")
def settings_routing_rules() -> dict[str, list[dict[str, str]]]:
    rules_path = "config/routing_rules.yaml"
    try:
        with open(rules_path) as f:
            data = yaml.safe_load(f)
        rules = data.get("rules", [])
        return {
            "rules": [
                {
                    "name": r.get("name", ""),
                    "condition": json.dumps(r.get("condition", "")) if isinstance(r.get("condition"), dict) else str(r.get("condition", "")),
                    "destination": r.get("destination", ""),
                }
                for r in rules
            ]
        }
    except FileNotFoundError:
        return {"rules": []}
