"""Google Sheets output adapter via Composio.

Appends an order summary row to a configured spreadsheet.
"""
from __future__ import annotations

from datetime import UTC, datetime

import structlog

from order_automation.integrations.composio_client import execute_action
from order_automation.models.order import Order, SubmissionResult
from order_automation.output.base import OutputAdapter

log = structlog.get_logger()


class SheetsOutputAdapter(OutputAdapter):
    """Appends a row per order to a Google Sheet via Composio."""

    def __init__(self, spreadsheet_id: str = "", sheet_name: str = "OrderLog") -> None:
        self.spreadsheet_id = spreadsheet_id
        self.sheet_name = sheet_name

    def submit(self, order: Order) -> SubmissionResult:
        """Append an order summary row."""
        if not self.spreadsheet_id:
            log.info("sheets_output_skipped", reason="no spreadsheet_id configured")
            return SubmissionResult(success=True, destination="sheets", external_ref="skipped")

        row = [
            order.id,
            order.source.value,
            order.customer_name,
            order.po_number,
            str(order.total_amount),
            order.status.value,
            datetime.now(UTC).isoformat(),
        ]

        result = execute_action("GOOGLESHEETS_APPEND_ROW", {
            "spreadsheet_id": self.spreadsheet_id,
            "sheet_name": self.sheet_name,
            "values": row,
        })

        success = result.get("success", True)
        return SubmissionResult(
            success=success,
            destination="sheets",
            external_ref=self.spreadsheet_id,
            error="" if success else str(result),
        )
