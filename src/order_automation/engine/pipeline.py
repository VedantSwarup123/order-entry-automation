"""Order processing pipeline.

Orchestrates the full order lifecycle:
normalise → validate → route → submit to destination adapters.
"""
from __future__ import annotations

from typing import Protocol

import structlog

from order_automation.engine.normalizer import OrderNormalizer
from order_automation.engine.router import OrderRouter
from order_automation.engine.validator import OrderValidator
from order_automation.models.order import Order, OrderStatus, SubmissionResult

log = structlog.get_logger()


class OutputAdapter(Protocol):
    """Minimal interface every output adapter must satisfy."""

    def submit(self, order: Order) -> SubmissionResult: ...


class OrderPipeline:
    """End-to-end order processing pipeline."""

    def __init__(
        self,
        normalizer: OrderNormalizer | None = None,
        validator: OrderValidator | None = None,
        router: OrderRouter | None = None,
    ) -> None:
        self.normalizer = normalizer or OrderNormalizer()
        self.validator = validator or OrderValidator()
        self.router = router or OrderRouter()
        self._adapters: dict[str, OutputAdapter] = {}

    def register_adapter(self, name: str, adapter: OutputAdapter) -> None:
        """Register an output adapter under *name*."""
        self._adapters[name] = adapter

    def process(self, order: Order) -> Order:
        """Run the full pipeline and return the updated order."""
        # 1. Normalise
        order = self.normalizer.normalize(order)
        order.status = OrderStatus.pending

        # 2. Validate
        result = self.validator.validate(order)
        if not result.valid:
            order.status = OrderStatus.error
            order.errors.extend(result.errors)
            log.warning("order_validation_failed", order_id=order.id, errors=result.errors)
            return order
        order.status = OrderStatus.validated

        # 3. Route
        destinations = self.router.route(order)
        order.destinations = destinations
        order.status = OrderStatus.routed

        # 4. Submit to each destination (database last so it captures final status)
        any_failure = False
        non_db = [d for d in destinations if d != "database"]
        db_last = [d for d in destinations if d == "database"]

        for dest in non_db + db_last:
            adapter = self._adapters.get(dest)
            if adapter is None:
                log.warning("adapter_not_registered", destination=dest, order_id=order.id)
                continue

            # Set final status before the database write
            if dest == "database":
                order.status = OrderStatus.error if any_failure else OrderStatus.completed

            try:
                sub_result = adapter.submit(order)
                if not sub_result.success:
                    any_failure = True
                    order.errors.append(f"{dest}: {sub_result.error}")
                    log.error("adapter_submit_failed", destination=dest, error=sub_result.error)
            except Exception as exc:
                any_failure = True
                order.errors.append(f"{dest}: {exc}")
                log.error("adapter_submit_exception", destination=dest, error=str(exc))

        order.status = OrderStatus.error if any_failure else OrderStatus.completed
        return order
