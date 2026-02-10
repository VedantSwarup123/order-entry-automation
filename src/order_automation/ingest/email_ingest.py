"""Email ingest via Composio (Gmail / Outlook).

Polls for new emails, parses order data from the body using regex patterns,
and creates orders. Unparseable emails are flagged for manual review.
"""
from __future__ import annotations

import re
from datetime import date
from decimal import Decimal, InvalidOperation

import structlog

from order_automation.ingest.base import IngestSource
from order_automation.integrations.composio_client import execute_action
from order_automation.models.order import (
    Address,
    Order,
    OrderLineItem,
    OrderSource,
    RawOrder,
)

log = structlog.get_logger()

# Key-value patterns:  customer_id: CUST-123
_KV_PATTERN = re.compile(r"^\s*([\w_]+)\s*:\s*(.+)$", re.MULTILINE)

# Tabular line-item pattern:  SKU  QTY  PRICE
_LINE_PATTERN = re.compile(
    r"^\s*(\S+)\s+(\d+)\s+\$?([\d,.]+)\s*$", re.MULTILINE
)


def _extract_kv(body: str) -> dict[str, str]:
    """Extract key:value pairs from the email body."""
    return {m.group(1).lower(): m.group(2).strip() for m in _KV_PATTERN.finditer(body)}


def _extract_line_items(body: str) -> list[OrderLineItem]:
    """Extract tabular line items (SKU QTY PRICE) from the email body."""
    items: list[OrderLineItem] = []
    for m in _LINE_PATTERN.finditer(body):
        try:
            items.append(OrderLineItem(
                sku=m.group(1),
                quantity=int(m.group(2)),
                unit_price=Decimal(m.group(3).replace(",", "")),
            ))
        except (InvalidOperation, ValueError):
            continue
    return items


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
        """Parse an email body into an Order."""
        kv = _extract_kv(raw.body)
        items = _extract_line_items(raw.body)

        if not items:
            # Unparseable → flag for review
            items = [OrderLineItem(sku="REVIEW", quantity=1, unit_price=Decimal(0))]
            log.warning("email_parse_fallback", source_ref=raw.source_ref)

        return [Order(
            source=OrderSource.email,
            source_ref=raw.source_ref,
            customer_id=kv.get("customer_id", ""),
            customer_name=kv.get("customer_name", ""),
            po_number=kv.get("po_number", ""),
            order_date=date.today(),
            ship_to=Address(
                name=kv.get("ship_to_name", ""),
                line1=kv.get("ship_to_address", ""),
                city=kv.get("ship_to_city", ""),
                state=kv.get("ship_to_state", ""),
                postal_code=kv.get("ship_to_zip", ""),
            ),
            line_items=items,
            metadata=raw.metadata,
        )]

    def mark_read(self, source_ref: str) -> None:
        """Mark an email as read after processing."""
        execute_action(self._mark_action, {"message_id": source_ref})
