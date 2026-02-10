"""Google Sheets ingest via Composio.

Reads new rows from a configured spreadsheet and converts them to orders.
Tracks the last processed row count to detect additions.
"""
from __future__ import annotations

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

# Default column-index mapping
_DEFAULT_COL_MAP: dict[str, int] = {
    "po_number": 0,
    "customer_id": 1,
    "customer_name": 2,
    "sku": 3,
    "description": 4,
    "quantity": 5,
    "unit_price": 6,
}


def _cell(row: list, idx: int) -> str:
    """Safely get a cell value as string."""
    if idx < len(row):
        val = row[idx]
        return str(val).strip() if val is not None else ""
    return ""


class SheetsIngest(IngestSource):
    """Polls a Google Sheet for new rows via Composio."""

    def __init__(
        self,
        spreadsheet_id: str = "",
        sheet_name: str = "Orders",
        column_mapping: dict[str, int] | None = None,
    ) -> None:
        self.spreadsheet_id = spreadsheet_id
        self.sheet_name = sheet_name
        self.column_mapping = column_mapping or dict(_DEFAULT_COL_MAP)
        self._last_row_count: int = 0

    def poll(self) -> list[RawOrder]:
        """Fetch sheet data and return only new rows as a RawOrder."""
        if not self.spreadsheet_id:
            return []

        result = execute_action("GOOGLESHEETS_GET_SPREADSHEET_DATA", {
            "spreadsheet_id": self.spreadsheet_id,
            "sheet_name": self.sheet_name,
        })

        all_rows = result.get("values") or result.get("rows") or result.get("data") or []
        new_rows = all_rows[self._last_row_count:]
        self._last_row_count = len(all_rows)

        if not new_rows:
            return []

        return [RawOrder(
            source=OrderSource.sheets,
            source_ref=f"sheets:{self.spreadsheet_id}",
            rows=[{"cells": r} for r in new_rows],
            metadata={"spreadsheet_id": self.spreadsheet_id},
        )]

    def parse(self, raw: RawOrder) -> list[Order]:
        """Convert sheet rows into orders, grouping by PO number."""
        cm = self.column_mapping
        groups: dict[str, list[list]] = {}
        for row_dict in raw.rows:
            cells = row_dict.get("cells", [])
            po = _cell(cells, cm.get("po_number", 0)) or "UNKNOWN"
            groups.setdefault(po, []).append(cells)

        orders: list[Order] = []
        for po, rows in groups.items():
            first = rows[0]
            items: list[OrderLineItem] = []
            for cells in rows:
                sku = _cell(cells, cm.get("sku", 3))
                if not sku:
                    continue
                try:
                    qty = max(1, int(float(_cell(cells, cm.get("quantity", 5)) or "1")))
                except ValueError:
                    qty = 1
                try:
                    price = Decimal(_cell(cells, cm.get("unit_price", 6)) or "0")
                except InvalidOperation:
                    price = Decimal(0)
                items.append(OrderLineItem(sku=sku, quantity=qty, unit_price=price))

            if not items:
                continue

            orders.append(Order(
                source=OrderSource.sheets,
                source_ref=raw.source_ref,
                customer_id=_cell(first, cm.get("customer_id", 1)),
                customer_name=_cell(first, cm.get("customer_name", 2)),
                po_number=po,
                order_date=date.today(),
                ship_to=Address(),
                line_items=items,
                metadata=raw.metadata,
            ))
        return orders
