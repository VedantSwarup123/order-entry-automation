"""Fax / scanned document ingest via OCR.

Watches a directory for PDF and image files, extracts text using
pytesseract, and parses order data with regex.  Low-quality extractions
are moved to a review directory for manual handling.
"""
from __future__ import annotations

import re
import shutil
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

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

_IMAGE_EXT = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"}
_PDF_EXT = {".pdf"}

# Try to import OCR libs; gracefully degrade if missing.
try:
    import pytesseract  # type: ignore[import-untyped]
    from PIL import Image

    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False
    pytesseract = None  # type: ignore[assignment]
    Image = None  # type: ignore[assignment,misc]

try:
    from pdf2image import convert_from_path  # type: ignore[import-untyped]

    PDF2IMAGE_AVAILABLE = True
except ImportError:
    PDF2IMAGE_AVAILABLE = False
    convert_from_path = None  # type: ignore[assignment]

# Regex for key: value in OCR text
_KV_PATTERN = re.compile(r"([\w\s]+?)\s*:\s*(.+)")
_LINE_PATTERN = re.compile(r"(\S+)\s+(\d+)\s+\$?([\d,.]+)")


def _ocr_image(path: Path) -> str:
    """Run OCR on a single image file."""
    if not TESSERACT_AVAILABLE:
        return ""
    img = Image.open(path)  # type: ignore[union-attr]
    return pytesseract.image_to_string(img)  # type: ignore[union-attr]


def _ocr_pdf(path: Path) -> str:
    """Convert a PDF to images and OCR each page."""
    if not PDF2IMAGE_AVAILABLE or not TESSERACT_AVAILABLE:
        return ""
    pages = convert_from_path(path)  # type: ignore[misc]
    texts: list[str] = []
    for page in pages:
        texts.append(pytesseract.image_to_string(page))  # type: ignore[union-attr]
    return "\n".join(texts)


def _confidence_score(text: str) -> float:
    """Rough heuristic: ratio of alphanumeric chars to total length."""
    if not text:
        return 0.0
    alpha = sum(c.isalnum() or c.isspace() for c in text)
    return alpha / len(text)


class FaxIngest(IngestSource):
    """Watches for fax/scanned files and applies OCR."""

    def __init__(
        self,
        watch_dir: str | Path = "inbox/fax",
        processed_dir: str | Path = "processed/fax",
        review_dir: str | Path = "review/fax",
        min_confidence: float = 0.6,
    ) -> None:
        self.watch_dir = Path(watch_dir)
        self.processed_dir = Path(processed_dir)
        self.review_dir = Path(review_dir)
        self.min_confidence = min_confidence

    def poll(self) -> list[RawOrder]:
        """Scan watch dir for image/PDF files and OCR them."""
        raws: list[RawOrder] = []
        if not self.watch_dir.exists():
            return raws

        for fpath in sorted(self.watch_dir.iterdir()):
            suffix = fpath.suffix.lower()
            if suffix in _IMAGE_EXT:
                text = _ocr_image(fpath)
            elif suffix in _PDF_EXT:
                text = _ocr_pdf(fpath)
            else:
                continue

            conf = _confidence_score(text)
            if conf < self.min_confidence:
                log.warning("fax_low_confidence", file=fpath.name, confidence=conf)
                self.review_dir.mkdir(parents=True, exist_ok=True)
                shutil.move(str(fpath), str(self.review_dir / fpath.name))
                continue

            raws.append(RawOrder(
                source=OrderSource.fax,
                source_ref=str(fpath),
                body=text,
                metadata={"filename": fpath.name, "confidence": conf},
            ))
            self.processed_dir.mkdir(parents=True, exist_ok=True)
            shutil.move(str(fpath), str(self.processed_dir / fpath.name))

        return raws

    def parse(self, raw: RawOrder) -> list[Order]:
        """Parse OCR text into an Order."""
        kv: dict[str, str] = {}
        for m in _KV_PATTERN.finditer(raw.body):
            key = m.group(1).strip().lower().replace(" ", "_")
            kv[key] = m.group(2).strip()

        items: list[OrderLineItem] = []
        for m in _LINE_PATTERN.finditer(raw.body):
            try:
                items.append(OrderLineItem(
                    sku=m.group(1),
                    quantity=int(m.group(2)),
                    unit_price=Decimal(m.group(3).replace(",", "")),
                ))
            except (InvalidOperation, ValueError):
                continue

        if not items:
            items = [OrderLineItem(sku="REVIEW", quantity=1, unit_price=Decimal(0))]

        return [Order(
            source=OrderSource.fax,
            source_ref=raw.source_ref,
            customer_id=kv.get("customer_id", ""),
            customer_name=kv.get("customer_name", kv.get("customer", "")),
            po_number=kv.get("po_number", kv.get("po", "")),
            order_date=date.today(),
            ship_to=Address(
                name=kv.get("ship_to_name", kv.get("ship_to", "")),
                line1=kv.get("ship_to_address", kv.get("address", "")),
                city=kv.get("ship_to_city", kv.get("city", "")),
                state=kv.get("ship_to_state", kv.get("state", "")),
                postal_code=kv.get("ship_to_zip", kv.get("zip", "")),
            ),
            line_items=items,
            metadata=raw.metadata,
        )]
