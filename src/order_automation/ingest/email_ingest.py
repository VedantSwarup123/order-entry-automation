"""Email ingest via Composio (Gmail / Outlook).

Polls for new emails, extracts order data using LLM-powered extraction
(with regex fallback), and creates orders. Low-confidence extractions
are flagged for human review.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation

import structlog

from order_automation.ingest.base import IngestSource
from order_automation.integrations.composio_client import execute_action
from order_automation.integrations.llm_client import extract_order_from_text
from order_automation.models.order import (
    Address,
    Order,
    OrderLineItem,
    OrderSource,
    RawOrder,
)

log = structlog.get_logger()

# Orders below this confidence go to review queue
CONFIDENCE_THRESHOLD = 0.7


class EmailIngest(IngestSource):
    """Polls Gmail or Outlook for new order emails via Composio."""

    def __init__(self, provider: str = "gmail") -> None:
        self.provider = provider
        self._action = (
            "GMAIL_FETCH_EMAILS" if provider == "gmail" else "OUTLOOK_FETCH_EMAILS"
        )
        self._mark_action = (
            "GMAIL_MARK_AS_READ" if provider == "gmail" else "OUTLOOK_MARK_AS_READ"
        )

    def poll(self) -> list[RawOrder]:
        """Fetch unread order emails."""
        result = execute_action(self._action, {"query": "subject:order is:unread"})
        emails = result.get("emails") or result.get("messages") or []
        raws: list[RawOrder] = []
        for email in emails:
            body = email.get("body", "") if isinstance(email, dict) else str(email)
            raws.append(RawOrder(
                source=OrderSource.email,
                source_ref=email.get("id", "") if isinstance(email, dict) else "",
                body=body,
                metadata={"provider": self.provider},
            ))
        return raws

    def parse(self, raw: RawOrder) -> list[Order]:
        """Parse an email body into an Order using LLM extraction."""
        extracted = extract_order_from_text(raw.body, source="email")

        confidence = extracted.get("confidence", 0.0)
        extraction_method = extracted.get("extraction_method", "unknown")
        anomalies = extracted.get("anomalies", [])

        # Build line items from extracted data
        items: list[OrderLineItem] = []
        for li in extracted.get("line_items", []):
            try:
                items.append(OrderLineItem(
                    sku=li.get("sku", "UNKNOWN"),
                    description=li.get("description", ""),
                    quantity=int(li.get("quantity", 1)),
                    unit_price=Decimal(str(li.get("unit_price", 0))),
                    uom=li.get("uom", "EA"),
                ))
            except (InvalidOperation, ValueError):
                continue

        if not items:
            items = [OrderLineItem(sku="REVIEW", quantity=1, unit_price=Decimal(0))]
            log.warning("email_parse_fallback", source_ref=raw.source_ref)

        # Build ship_to from extracted data
        ship_to_data = extracted.get("ship_to", {})

        # Determine if order needs review
        needs_review = confidence < CONFIDENCE_THRESHOLD or len(anomalies) > 0

        metadata = {
            **raw.metadata,
            "extraction_method": extraction_method,
            "confidence": confidence,
            "anomalies": anomalies,
            "needs_review": needs_review,
        }

        order = Order(
            source=OrderSource.email,
            source_ref=raw.source_ref,
            customer_id=extracted.get("customer_id", ""),
            customer_name=extracted.get("customer_name", ""),
            po_number=extracted.get("po_number", ""),
            order_date=date.today(),
            ship_to=Address(
                name=ship_to_data.get("name", ""),
                line1=ship_to_data.get("line1", ""),
                city=ship_to_data.get("city", ""),
                state=ship_to_data.get("state", ""),
                postal_code=ship_to_data.get("postal_code", ""),
            ),
            line_items=items,
            notes=extracted.get("notes", ""),
            metadata=metadata,
        )

        log.info(
            "email_parsed",
            source_ref=raw.source_ref,
            method=extraction_method,
            confidence=confidence,
            anomalies=len(anomalies),
            needs_review=needs_review,
        )

        return [order]

    def mark_read(self, source_ref: str) -> None:
        """Mark an email as read after processing."""
        execute_action(self._mark_action, {"message_id": source_ref})
