"""CSV / Excel file ingest.

Watches a directory for ``*.csv``, ``*.xlsx``, and ``*.xls`` files, reads them
with *pandas*, groups rows by PO number, and moves processed files.
"""
from __future__ import annotations

import shutil
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

import pandas as pd
import structlog

from order_automation.ingest.base import IngestSource
from order_automation.models.order import (
    Address,
    Order,
    OrderLineItem,
    OrderSource,
    RawOrder,
)

log = structlog.get_logger()

_EXTENSIONS = {".csv", ".xlsx", ".xls"}

# Default column mapping (overridable from settings.yaml)
_DEFAULT_MAPPING: dict[str, str] = {
    "po_number": "PO Number",
    "customer_id": "Customer ID",
    "customer_name": "Customer Name",
    "sku": "SKU",
    "description": "Description",
    "quantity": "Quantity",
    "unit_price": "Unit Price",
    "uom": "UOM",
    "ship_to_name": "Ship To Name",
    "ship_to_line1": "Ship To Address",
    "ship_to_city": "Ship To City",
    "ship_to_state": "Ship To State",
    "ship_to_postal_code": "Ship To Zip",
}


def _safe_str(val: Any) -> str:
    """Coerce a cell value to ``str``, handling NaN."""
    if pd.isna(val):
        return ""
    return str(val).strip()


def _safe_decimal(val: Any) -> Decimal:
    """Coerce a cell value to ``Decimal``, defaulting to 0."""
    try:
        if pd.isna(val):
            return Decimal(0)
        return Decimal(str(val).strip().replace(",", ""))
    except (InvalidOperation, ValueError):
        return Decimal(0)


def _safe_int(val: Any) -> int:
    """Coerce a cell value to ``int``, defaulting to 1."""
    try:
        if pd.isna(val):
            return 1
        return max(1, int(float(str(val).strip())))
    except (ValueError, TypeError):
        return 1


class CSVIngest(IngestSource):
    """Reads CSV/Excel files from a watch directory."""

    def __init__(
        self,
        watch_dir: str | Path = "inbox/csv",
        processed_dir: str | Path = "processed/csv",
        column_mapping: dict[str, str] | None = None,
    ) -> None:
        self.watch_dir = Path(watch_dir)
        self.processed_dir = Path(processed_dir)
        self.column_mapping = column_mapping or dict(_DEFAULT_MAPPING)

    # ------------------------------------------------------------------
    # IngestSource interface
    # ------------------------------------------------------------------

    def poll(self) -> list[RawOrder]:
        """Scan *watch_dir* for spreadsheet files and return raw payloads."""
        raws: list[RawOrder] = []
        if not self.watch_dir.exists():
            return raws

        for fpath in sorted(self.watch_dir.iterdir()):
            if fpath.suffix.lower() not in _EXTENSIONS:
                continue
            try:
                df = self._read_file(fpath)
                rows = df.to_dict(orient="records")
                raws.append(RawOrder(
                    source=OrderSource.csv,
                    source_ref=str(fpath),
                    rows=rows,
                    metadata={"filename": fpath.name},
                ))
            except Exception as exc:
                log.error("csv_read_failed", file=str(fpath), error=str(exc))
        return raws

    def parse(self, raw: RawOrder) -> list[Order]:
        """Group rows by PO number and return one Order per PO."""
        mapping = self.column_mapping
        po_col = mapping.get("po_number", "PO Number")

        groups: dict[str, list[dict]] = {}
        for row in raw.rows:
            po = _safe_str(row.get(po_col, ""))
            if not po:
                po = "UNKNOWN"
            groups.setdefault(po, []).append(row)

        orders: list[Order] = []
        for po, rows in groups.items():
            first = rows[0]
            line_items = self._rows_to_line_items(rows, mapping)
            if not line_items:
                continue
            orders.append(Order(
                source=OrderSource.csv,
                source_ref=raw.source_ref,
                customer_id=_safe_str(first.get(mapping.get("customer_id", "Customer ID"), "")),
                customer_name=_safe_str(first.get(mapping.get("customer_name", "Customer Name"), "")),
                po_number=po,
                order_date=date.today(),
                ship_to=Address(
                    name=_safe_str(first.get(mapping.get("ship_to_name", "Ship To Name"), "")),
                    line1=_safe_str(first.get(mapping.get("ship_to_line1", "Ship To Address"), "")),
                    city=_safe_str(first.get(mapping.get("ship_to_city", "Ship To City"), "")),
                    state=_safe_str(first.get(mapping.get("ship_to_state", "Ship To State"), "")),
                    postal_code=_safe_str(first.get(mapping.get("ship_to_postal_code", "Ship To Zip"), "")),
                ),
                line_items=line_items,
                metadata=raw.metadata,
            ))
        return orders

    # ------------------------------------------------------------------
    # File handling
    # ------------------------------------------------------------------

    def move_to_processed(self, filepath: str | Path) -> None:
        """Move a file from the watch dir to the processed dir."""
        src = Path(filepath)
        self.processed_dir.mkdir(parents=True, exist_ok=True)
        dest = self.processed_dir / src.name
        shutil.move(str(src), str(dest))
        log.info("csv_file_moved", src=str(src), dest=str(dest))

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _read_file(self, path: Path) -> pd.DataFrame:
        """Read a CSV or Excel file into a DataFrame, dropping empty rows."""
        if path.suffix.lower() == ".csv":
            df = pd.read_csv(path)
        else:
            df = pd.read_excel(path, engine="openpyxl")
        return df.dropna(how="all")

    def _rows_to_line_items(
        self,
        rows: list[dict],
        mapping: dict[str, str],
    ) -> list[OrderLineItem]:
        """Convert raw row dicts into validated line items."""
        items: list[OrderLineItem] = []
        sku_col = mapping.get("sku", "SKU")
        desc_col = mapping.get("description", "Description")
        qty_col = mapping.get("quantity", "Quantity")
        price_col = mapping.get("unit_price", "Unit Price")
        uom_col = mapping.get("uom", "UOM")

        for row in rows:
            sku = _safe_str(row.get(sku_col, ""))
            if not sku:
                continue
            items.append(OrderLineItem(
                sku=sku,
                description=_safe_str(row.get(desc_col, "")),
                quantity=_safe_int(row.get(qty_col, 1)),
                unit_price=_safe_decimal(row.get(price_col, 0)),
                uom=_safe_str(row.get(uom_col, "")) or "EA",
            ))
        return items
