"""Order validation logic."""
from __future__ import annotations

from order_automation.models.order import Order, ValidationResult


class OrderValidator:
    """Validates an :class:`Order` against business rules."""

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

        return ValidationResult(valid=len(errors) == 0, errors=errors)
