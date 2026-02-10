"""ERP output adapter.

If ``base_url`` is configured, sends orders via HTTP. Otherwise uses a
mock that generates fake confirmation numbers.
"""
from __future__ import annotations

import uuid

import structlog

from order_automation.models.order import Order, SubmissionResult
from order_automation.output.base import OutputAdapter

log = structlog.get_logger()


class MockERPAdapter(OutputAdapter):
    """In-memory mock that generates fake ERP confirmation numbers."""

    def __init__(self) -> None:
        self.submitted: list[Order] = []

    def submit(self, order: Order) -> SubmissionResult:
        """Generate a mock confirmation and record the order."""
        ref = f"ERP-{uuid.uuid4().hex[:8].upper()}"
        self.submitted.append(order)
        log.info("mock_erp_submit", order_id=order.id, ref=ref)
        return SubmissionResult(success=True, destination="erp", external_ref=ref)


class ERPAdapter(OutputAdapter):
    """HTTP-based ERP adapter (delegates to mock when not configured)."""

    def __init__(self, base_url: str = "") -> None:
        self.base_url = base_url.rstrip("/") if base_url else ""
        self._mock = MockERPAdapter()

    def submit(self, order: Order) -> SubmissionResult:
        """Submit to ERP or fall back to mock."""
        if not self.base_url:
            return self._mock.submit(order)

        import httpx

        try:
            resp = httpx.post(
                f"{self.base_url}/api/orders",
                json=order.model_dump(mode="json"),
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            return SubmissionResult(
                success=True,
                destination="erp",
                external_ref=data.get("confirmation", order.id),
            )
        except Exception as exc:
            log.error("erp_submit_failed", order_id=order.id, error=str(exc))
            return SubmissionResult(success=False, destination="erp", error=str(exc))
