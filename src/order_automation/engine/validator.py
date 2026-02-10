"""Order validation logic."""
from __future__ import annotations

from datetime import timedelta

import structlog

from order_automation.models.order import Order, ValidationResult

log = structlog.get_logger()


class DuplicateDetector:
    """Detects duplicate orders by PO number + customer within a time window."""

    def __init__(self, time_window_hours: int = 48) -> None:
        self.time_window = timedelta(hours=time_window_hours)
        self._recent_orders: list[dict] = []

    def load_recent_orders(self, orders: list[dict]) -> None:
        """Load recent orders for duplicate checking.

        Each dict should have: customer_id, po_number, created_at (datetime).
        """
        self._recent_orders = orders

    def check(self, order: Order) -> list[str]:
        """Check if the order is a potential duplicate.

        Returns list of warning strings (empty if no duplicates found).
        """
        warnings: list[str] = []

        if not order.po_number or not order.customer_id:
            return warnings

        for existing in self._recent_orders:
            if (
                existing.get("po_number", "").upper() == order.po_number.upper()
                and existing.get("customer_id", "").upper() == order.customer_id.upper()
            ):
                warnings.append(
                    f"Potential duplicate: PO {order.po_number} for customer "
                    f"{order.customer_id} already exists (order {existing.get('id', 'unknown')})"
                )

        return warnings


class OrderValidator:
    """Validates an :class:`Order` against business rules."""

    def __init__(self, duplicate_detector: DuplicateDetector | None = None) -> None:
        self.duplicate_detector = duplicate_detector

    def validate(self, order: Order) -> ValidationResult:
        """Run all validation checks and return the result."""
        errors: list[str] = []

        if not order.customer_id.strip():
            errors.append("customer_id is required")

        if not order.po_number.strip():
            errors.append("po_number is required")

        for idx, item in enumerate(order.line_items):
            if not item.sku.strip():
                errors.append(f"line_items[{idx}].sku is required")

        if (
            order.requested_ship_date is not None
            and order.requested_ship_date < order.order_date
        ):
            errors.append("requested_ship_date must be >= order_date")

        if order.total_amount <= 0:
            errors.append("total_amount must be > 0")

        # Duplicate detection
        if self.duplicate_detector:
            dup_warnings = self.duplicate_detector.check(order)
            if dup_warnings:
                for w in dup_warnings:
                    log.warning("duplicate_detected", order_id=order.id, warning=w)
                errors.extend(dup_warnings)

        return ValidationResult(valid=len(errors) == 0, errors=errors)
