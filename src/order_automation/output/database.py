"""SQLite / SQLAlchemy output adapter.

Every order is persisted here regardless of other destinations.
"""
from __future__ import annotations

from datetime import UTC, datetime

import structlog
from sqlalchemy import (
    Column,
    DateTime,
    Integer,
    Numeric,
    String,
    Text,
    create_engine,
)
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from order_automation.models.order import Order, SubmissionResult
from order_automation.output.base import OutputAdapter

log = structlog.get_logger()


# ------------------------------------------------------------------
# ORM models
# ------------------------------------------------------------------

class Base(DeclarativeBase):
    """SQLAlchemy declarative base."""


class OrderRecord(Base):
    """Persisted order header."""

    __tablename__ = "orders"

    id = Column(String, primary_key=True)
    source = Column(String, nullable=False)
    source_ref = Column(String, default="")
    customer_id = Column(String, default="")
    customer_name = Column(String, default="")
    po_number = Column(String, default="")
    order_date = Column(String, default="")
    ship_to_name = Column(String, default="")
    ship_to_line1 = Column(String, default="")
    ship_to_city = Column(String, default="")
    ship_to_state = Column(String, default="")
    ship_to_postal_code = Column(String, default="")
    ship_to_country = Column(String, default="US")
    total_amount = Column(Numeric, default=0)
    total_quantity = Column(Integer, default=0)
    status = Column(String, default="pending")
    errors = Column(Text, default="")
    notes = Column(Text, default="")
    confidence = Column(Numeric, default=None, nullable=True)
    extraction_method = Column(String, default="", nullable=True)
    sap_order_type = Column(String, default="", nullable=True)
    sap_data = Column(Text, default="", nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))


class LineItemRecord(Base):
    """Persisted line item."""

    __tablename__ = "line_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(String, nullable=False)
    sku = Column(String, nullable=False)
    description = Column(String, default="")
    quantity = Column(Integer, default=0)
    unit_price = Column(Numeric, default=0)
    uom = Column(String, default="EA")
    line_total = Column(Numeric, default=0)


class AuditLogRecord(Base):
    """Audit trail entry."""

    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(String, nullable=False)
    action = Column(String, nullable=False)
    detail = Column(Text, default="")
    timestamp = Column(DateTime, default=lambda: datetime.now(UTC))


class DeadLetterRecord(Base):
    """Failed orders stored for later retry."""

    __tablename__ = "dead_letter"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(String, nullable=False)
    payload = Column(Text, nullable=False)
    error = Column(Text, default="")
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))


class ReviewQueueRecord(Base):
    """Orders flagged for human review."""

    __tablename__ = "review_queue"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(String, nullable=False)
    source = Column(String, default="")
    customer_name = Column(String, default="")
    po_number = Column(String, default="")
    confidence = Column(Numeric, default=0.0)
    extraction_method = Column(String, default="")
    anomalies = Column(Text, default="")
    original_text = Column(Text, default="")
    extracted_data = Column(Text, default="")
    status = Column(String, default="pending")  # pending, approved, rejected, modified
    reviewer_notes = Column(Text, default="")
    reviewed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))


# ------------------------------------------------------------------
# Adapter
# ------------------------------------------------------------------

class DatabaseAdapter(OutputAdapter):
    """Writes orders to a SQLAlchemy-backed database."""

    def __init__(self, url: str = "sqlite:///orders.db") -> None:
        self.engine = create_engine(url, echo=False)
        Base.metadata.create_all(self.engine)
        self._Session = sessionmaker(bind=self.engine)

    def submit(self, order: Order) -> SubmissionResult:
        """INSERT the order and its line items."""
        session: Session = self._Session()
        try:
            record = OrderRecord(
                id=order.id,
                source=order.source.value,
                source_ref=order.source_ref,
                customer_id=order.customer_id,
                customer_name=order.customer_name,
                po_number=order.po_number,
                order_date=str(order.order_date),
                ship_to_name=order.ship_to.name,
                ship_to_line1=order.ship_to.line1,
                ship_to_city=order.ship_to.city,
                ship_to_state=order.ship_to.state,
                ship_to_postal_code=order.ship_to.postal_code,
                ship_to_country=order.ship_to.country,
                total_amount=order.total_amount,
                total_quantity=order.total_quantity,
                status=order.status.value,
                errors="; ".join(order.errors),
                notes=order.notes,
            )
            session.add(record)

            for item in order.line_items:
                session.add(LineItemRecord(
                    order_id=order.id,
                    sku=item.sku,
                    description=item.description,
                    quantity=item.quantity,
                    unit_price=item.unit_price,
                    uom=item.uom,
                    line_total=item.line_total,
                ))

            session.add(AuditLogRecord(
                order_id=order.id,
                action="submitted",
                detail=f"Source: {order.source.value}, PO: {order.po_number}",
            ))

            session.commit()
            log.info("db_order_saved", order_id=order.id)
            return SubmissionResult(success=True, destination="database", external_ref=order.id)
        except Exception as exc:
            session.rollback()
            log.error("db_order_failed", order_id=order.id, error=str(exc))
            return SubmissionResult(success=False, destination="database", error=str(exc))
        finally:
            session.close()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def get_order(self, order_id: str) -> OrderRecord | None:
        """Fetch a single order by ID."""
        session = self._Session()
        try:
            return session.query(OrderRecord).filter_by(id=order_id).first()
        finally:
            session.close()

    def get_failures(self) -> list[OrderRecord]:
        """Return all orders with status='error'."""
        session = self._Session()
        try:
            return list(session.query(OrderRecord).filter_by(status="error").all())
        finally:
            session.close()

    def get_all_orders(self) -> list[OrderRecord]:
        """Return all orders."""
        session = self._Session()
        try:
            return list(session.query(OrderRecord).all())
        finally:
            session.close()

    def get_line_items(self, order_id: str) -> list[LineItemRecord]:
        """Return line items for an order."""
        session = self._Session()
        try:
            return list(session.query(LineItemRecord).filter_by(order_id=order_id).all())
        finally:
            session.close()

    def get_stats(self) -> dict[str, int]:
        """Return order counts grouped by status."""
        session = self._Session()
        try:
            from sqlalchemy import func
            rows = (
                session.query(OrderRecord.status, func.count())
                .group_by(OrderRecord.status)
                .all()
            )
            return {status: count for status, count in rows}
        finally:
            session.close()
