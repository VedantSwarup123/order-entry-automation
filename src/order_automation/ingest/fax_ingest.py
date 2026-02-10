"""Fax / scanned document ingest via OCR.

Watches a directory for PDF and image files, extracts text using
pytesseract, then uses LLM-powered extraction (with regex fallback)
to parse order data. Low-quality extractions are flagged for review.
"""
from __future__ import annotations

import shutil
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

import structlog

from order_automation.ingest.base import IngestSource
from order_automation.integrations.llm_client import extract_order_from_text
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

# Orders below this confidence go to review queue
CONFIDENCE_THRESHOLD = 0.65

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


def _ocr_confidence_score(text: str) -> float:
    """Rough heuristic: ratio of alphanumeric chars to total length."""
    if not text:
        return 0.0
    alpha = sum(c.isalnum() or c.isspace() for c in text)
    return alpha / len(text)


class FaxIngest(IngestSource):
    """Watches for fax/scanned files and applies OCR + LLM extraction."""

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

            conf = _ocr_confidence_score(text)
            if conf < self.min_confidence:
                log.warning("fax_low_confidence", file=fpath.name, confidence=conf)
                self.review_dir.mkdir(parents=True, exist_ok=True)
                shutil.move(str(fpath), str(self.review_dir / fpath.name))
                continue

            raws.append(RawOrder(
                source=OrderSource.fax,
                source_ref=str(fpath),
                body=text,
                metadata={"filename": fpath.name, "ocr_confidence": conf},
            ))
            self.processed_dir.mkdir(parents=True, exist_ok=True)
            shutil.move(str(fpath), str(self.processed_dir / fpath.name))

        return raws

    def parse(self, raw: RawOrder) -> list[Order]:
        """Parse OCR text into an Order using LLM extraction."""
        extracted = extract_order_from_text(raw.body, source="fax")

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
            source=OrderSource.fax,
            source_ref=raw.source_ref,
            customer_id=extracted.get("customer_id", ""),
            customer_name=extracted.get("customer_name", kv_get_compat(extracted, "customer", "")),
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
            "fax_parsed",
            source_ref=raw.source_ref,
            method=extraction_method,
            confidence=confidence,
            anomalies=len(anomalies),
            needs_review=needs_review,
        )

        return [order]


def kv_get_compat(data: dict, key: str, default: str = "") -> str:
    """Compatibility helper for nested key access."""
    return data.get(key, default)
