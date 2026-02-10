"""Web portal output adapter.

Posts the order payload to a configured URL, falling back to a mock if
no URL is configured.
"""
from __future__ import annotations

import uuid

import structlog

from order_automation.models.order import Order, SubmissionResult
from order_automation.output.base import OutputAdapter

log = structlog.get_logger()


class MockPortalOutput(OutputAdapter):
    """In-memory mock for the web portal destination."""

    def __init__(self) -> None:
        self.submitted: list[Order] = []

    def submit(self, order: Order) -> SubmissionResult:
        """Record the order and return a mock ref."""
        ref = f"PORTAL-{uuid.uuid4().hex[:8].upper()}"
        self.submitted.append(order)
        log.info("mock_portal_submit", order_id=order.id, ref=ref)
        return SubmissionResult(success=True, destination="web_portal", external_ref=ref)


class WebPortalAdapter(OutputAdapter):
    """HTTP adapter that posts orders to a web portal."""

    def __init__(self, base_url: str = "") -> None:
        self.base_url = base_url.rstrip("/") if base_url else ""
        self._mock = MockPortalOutput()

    def submit(self, order: Order) -> SubmissionResult:
        """Submit to the portal or fall back to mock."""
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
                destination="web_portal",
                external_ref=data.get("id", order.id),
            )
        except Exception as exc:
            log.error("portal_submit_failed", order_id=order.id, error=str(exc))
            return SubmissionResult(success=False, destination="web_portal", error=str(exc))
